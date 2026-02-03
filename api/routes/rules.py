"""
API routes for rule execution.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File, Form

from api.models import (
    RuleExecutionRequest,
    RuleExecutionResponse,
    BatchRuleExecutionRequest,
    BatchRuleExecutionResponse,
    BatchItemResult,
    ErrorResponse,
    DMNRuleExecutionRequest
)
from services.ruleengine_exec import rules_exec, rules_exec_batch, dmn_rules_exec
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
    RuleEvaluationError
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/rules",
    tags=["rules"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.post(
    "/execute",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules against input data",
    description="Execute business rules against input data and return scoring results with action recommendations."
)
async def execute_rules(
    request: RuleExecutionRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleExecutionResponse:
    """
    Execute rules against input data.
    
    This endpoint evaluates all configured rules against the provided input data
    and returns:
    - Total weighted points
    - Pattern result (concatenated action results)
    - Action recommendation based on pattern matching
    
    Args:
        request: Rule execution request with input data
        http_request: FastAPI request object for correlation ID
        
    Returns:
        Rule execution response with results
        
    Raises:
        HTTPException: If execution fails or validation fails
    """
    start_time = time.time()
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    # Use correlation ID from request if provided
    if request.correlation_id:
        correlation_id = request.correlation_id
    
    logger.info(
        "API rule execution request",
        correlation_id=correlation_id,
        dry_run=request.dry_run,
        data_keys=list(request.data.keys())
    )
    
    try:
        # Execute rules
        result = rules_exec(
            data=request.data,
            dry_run=request.dry_run,
            correlation_id=correlation_id,
            consumer_id=request.consumer_id
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Convert rule evaluations if present
        rule_evaluations = None
        would_match = None
        would_not_match = None
        
        if request.dry_run and 'rule_evaluations' in result:
            from api.models import RuleEvaluationResult
            
            rule_evaluations = [
                RuleEvaluationResult(**evaluation)
                for evaluation in result.get('rule_evaluations', [])
            ]
            
            if 'would_match' in result:
                would_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_match', [])
                ]
            
            if 'would_not_match' in result:
                would_not_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_not_match', [])
                ]
        
        response = RuleExecutionResponse(
            total_points=result.get('total_points', 0.0),
            pattern_result=result.get('pattern_result', ''),
            action_recommendation=result.get('action_recommendation'),
            rule_evaluations=rule_evaluations,
            would_match=would_match,
            would_not_match=would_not_match,
            dry_run=result.get('dry_run', request.dry_run),
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id
        )
        
        logger.info(
            "API rule execution completed",
            correlation_id=correlation_id,
            total_points=response.total_points,
            pattern_result=response.pattern_result,
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except RuleEvaluationError as e:
        logger.error("Rule evaluation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error in rule execution", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.post(
    "/batch",
    response_model=BatchRuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules against multiple data items",
    description="Execute rules against multiple input data items in parallel for efficient batch processing."
)
async def execute_rules_batch(
    request: BatchRuleExecutionRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> BatchRuleExecutionResponse:
    """
    Execute rules against multiple data items in batch.
    
    This endpoint processes multiple input data items efficiently, optionally
    in parallel, and returns results for each item along with batch statistics.
    
    Args:
        request: Batch rule execution request with list of input data
        http_request: FastAPI request object for correlation ID
        
    Returns:
        Batch rule execution response with results and summary
        
    Raises:
        HTTPException: If execution fails or validation fails
    """
    start_time = time.time()
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    # Use correlation ID from request if provided
    if request.correlation_id:
        correlation_id = request.correlation_id
    
    logger.info(
        "API batch rule execution request",
        correlation_id=correlation_id,
        batch_size=len(request.data_list),
        dry_run=request.dry_run,
        max_workers=request.max_workers
    )
    
    try:
        # Execute batch rules
        result = rules_exec_batch(
            data_list=request.data_list,
            dry_run=request.dry_run,
            max_workers=request.max_workers,
            correlation_id=correlation_id,
            consumer_id=request.consumer_id
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Convert results to response model
        batch_results = []
        for item_result in result.get('results', []):
            batch_result = BatchItemResult(
                item_index=item_result.get('item_index', 0),
                correlation_id=item_result.get('correlation_id', ''),
                status=item_result.get('status', 'failed'),
                total_points=item_result.get('total_points'),
                pattern_result=item_result.get('pattern_result'),
                action_recommendation=item_result.get('action_recommendation'),
                error=item_result.get('error'),
                error_type=item_result.get('error_type')
            )
            batch_results.append(batch_result)
        
        response = BatchRuleExecutionResponse(
            batch_id=result.get('batch_id', correlation_id or 'unknown'),
            results=batch_results,
            summary=result.get('summary', {}),
            dry_run=result.get('dry_run', request.dry_run)
        )
        
        logger.info(
            "API batch rule execution completed",
            correlation_id=correlation_id,
            batch_id=response.batch_id,
            total_executions=response.summary.get('total_executions', 0),
            successful=response.summary.get('successful_executions', 0),
            failed=response.summary.get('failed_executions', 0),
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except RuleEvaluationError as e:
        logger.error("Rule evaluation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error in batch rule execution", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.post(
    "/execute-dmn",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules from DMN file",
    description="Execute business rules from a DMN (Decision Model Notation) file against input data."
)
async def execute_dmn_rules(
    request: DMNRuleExecutionRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleExecutionResponse:
    """
    Execute rules from a DMN file against input data.
    
    This endpoint accepts a DMN file (via file path or XML content) and input data,
    parses the DMN file to extract decision tables and rules, converts them to
    executable format, and executes them against the provided input data.
    
    Args:
        request: DMN rule execution request with DMN source and input data
        http_request: FastAPI request object for correlation ID
        
    Returns:
        Rule execution response with results
        
    Raises:
        HTTPException: If execution fails or validation fails
    """
    start_time = time.time()
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    # Use correlation ID from request if provided
    if request.correlation_id:
        correlation_id = request.correlation_id
    
    logger.info(
        "API DMN rule execution request",
        correlation_id=correlation_id,
        dry_run=request.dry_run,
        has_dmn_file=request.dmn_file is not None,
        has_dmn_content=request.dmn_content is not None,
        data_keys=list(request.data.keys())
    )
    
    try:
        # Validate DMN source
        try:
            request.validate_dmn_source_provided()
        except ValueError as validation_error:
            logger.error("DMN source validation error", error=str(validation_error), correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "DataValidationError",
                    "message": str(validation_error),
                    "error_code": "MISSING_DMN_SOURCE" if "must be provided" in str(validation_error) else "MULTIPLE_DMN_SOURCES",
                    "correlation_id": correlation_id
                }
            )
        
        # Execute DMN rules
        result = dmn_rules_exec(
            dmn_file=request.dmn_file,
            dmn_content=request.dmn_content,
            data=request.data,
            dry_run=request.dry_run,
            correlation_id=correlation_id,
            consumer_id=request.consumer_id
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Convert rule evaluations if present
        rule_evaluations = None
        would_match = None
        would_not_match = None
        
        if request.dry_run and 'rule_evaluations' in result:
            from api.models import RuleEvaluationResult
            
            rule_evaluations = [
                RuleEvaluationResult(**evaluation)
                for evaluation in result.get('rule_evaluations', [])
            ]
            
            if 'would_match' in result:
                would_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_match', [])
                ]
            
            if 'would_not_match' in result:
                would_not_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_not_match', [])
                ]
        
        response = RuleExecutionResponse(
            total_points=result.get('total_points', 0.0),
            pattern_result=result.get('pattern_result', ''),
            action_recommendation=result.get('action_recommendation'),
            decision_outputs=result.get('decision_outputs'),
            rule_evaluations=rule_evaluations,
            would_match=would_match,
            would_not_match=would_not_match,
            dry_run=result.get('dry_run', request.dry_run),
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id
        )
        
        logger.info(
            "API DMN rule execution completed",
            correlation_id=correlation_id,
            total_points=response.total_points,
            pattern_result=response.pattern_result,
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except RuleEvaluationError as e:
        logger.error("Rule evaluation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except Exception as e:
        logger.error("Unexpected error in DMN rule execution", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
                "correlation_id": correlation_id
            }
        )


@router.post(
    "/execute-dmn-upload",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules from uploaded DMN file",
    description="Execute business rules from an uploaded DMN file against input data."
)
async def execute_dmn_rules_upload(
    file: UploadFile = File(..., description="DMN XML file to upload"),
    data: str = Form(..., description="JSON string containing input data"),
    dry_run: bool = Form(default=False, description="Execute rules without side effects"),
    consumer_id: Optional[str] = Form(default=None, description="Consumer ID for usage tracking"),
    http_request: Request = None,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleExecutionResponse:
    """
    Execute rules from an uploaded DMN file against input data.
    
    This endpoint accepts a DMN file as multipart form data upload along with
    input data, providing a simpler interface for file-based execution.
    
    Args:
        file: Uploaded DMN XML file
        data: JSON string containing input data dictionary
        dry_run: Execute rules without side effects
        http_request: FastAPI request object for correlation ID
        
    Returns:
        Rule execution response with results
        
    Raises:
        HTTPException: If execution fails or validation fails
    """
    import json
    
    start_time = time.time()
    correlation_id = getattr(http_request.state, 'correlation_id', None) if http_request else None
    
    logger.info(
        "API DMN rule execution upload request",
        correlation_id=correlation_id,
        filename=file.filename,
        dry_run=dry_run
    )
    
    try:
        # Validate file type
        if not file.filename:
            logger.error("No filename provided", correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "DataValidationError",
                    "message": "File must have a filename",
                    "error_code": "MISSING_FILENAME",
                    "correlation_id": correlation_id
                }
            )
        
        if not file.filename.lower().endswith('.dmn'):
            logger.warning("Invalid file extension", 
                         correlation_id=correlation_id, 
                         filename=file.filename)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "DataValidationError",
                    "message": "File must have .dmn extension",
                    "error_code": "INVALID_FILE_TYPE",
                    "context": {"filename": file.filename},
                    "correlation_id": correlation_id
                }
            )
        
        # Read file content
        content = await file.read()
        dmn_content = content.decode('utf-8')
        
        # Parse input data JSON
        try:
            input_data = json.loads(data)
        except json.JSONDecodeError as json_error:
            logger.error("Invalid JSON in data field", error=str(json_error), correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "DataValidationError",
                    "message": f"Invalid JSON in data field: {str(json_error)}",
                    "error_code": "INVALID_JSON",
                    "correlation_id": correlation_id
                }
            )
        
        if not isinstance(input_data, dict):
            logger.error("Data must be a dictionary", correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "DataValidationError",
                    "message": "data must be a dictionary",
                    "error_code": "DATA_INVALID_TYPE",
                    "correlation_id": correlation_id
                }
            )
        
        logger.debug("DMN file content read", 
                    correlation_id=correlation_id, 
                    content_length=len(dmn_content),
                    data_keys=list(input_data.keys()))
        
        # Execute DMN rules
        result = dmn_rules_exec(
            dmn_content=dmn_content,
            data=input_data,
            dry_run=dry_run,
            correlation_id=correlation_id,
            consumer_id=consumer_id
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Convert rule evaluations if present
        rule_evaluations = None
        would_match = None
        would_not_match = None
        
        if dry_run and 'rule_evaluations' in result:
            from api.models import RuleEvaluationResult
            
            rule_evaluations = [
                RuleEvaluationResult(**evaluation)
                for evaluation in result.get('rule_evaluations', [])
            ]
            
            if 'would_match' in result:
                would_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_match', [])
                ]
            
            if 'would_not_match' in result:
                would_not_match = [
                    RuleEvaluationResult(**evaluation)
                    for evaluation in result.get('would_not_match', [])
                ]
        
        response = RuleExecutionResponse(
            total_points=result.get('total_points', 0.0),
            pattern_result=result.get('pattern_result', ''),
            action_recommendation=result.get('action_recommendation'),
            decision_outputs=result.get('decision_outputs'),
            rule_evaluations=rule_evaluations,
            would_match=would_match,
            would_not_match=would_not_match,
            dry_run=result.get('dry_run', dry_run),
            execution_time_ms=execution_time_ms,
            correlation_id=correlation_id
        )
        
        logger.info(
            "API DMN rule execution upload completed",
            correlation_id=correlation_id,
            filename=file.filename,
            total_points=response.total_points,
            pattern_result=response.pattern_result,
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except RuleEvaluationError as e:
        logger.error("Rule evaluation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={**e.to_dict(), "correlation_id": correlation_id}
        )
    except Exception as e:
        logger.error("Unexpected error in DMN rule execution upload", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
                "correlation_id": correlation_id
            }
        )

