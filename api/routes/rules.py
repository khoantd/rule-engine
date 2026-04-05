"""
API routes for rule execution.

Domain exceptions from ``services.ruleengine_exec`` propagate to the global
handler in ``api.middleware.errors``.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from api.deps import get_consumer_ruleset_registration_service_dep, get_correlation_id
from api.middleware.auth import get_api_key
from api.models import (
    BatchItemResult,
    BatchRuleExecutionRequest,
    BatchRuleExecutionResponse,
    DMNRuleExecutionRequest,
    ErrorResponse,
    RuleEvaluationResult,
    RuleExecutionRequest,
    RuleExecutionResponse,
)
from common.exceptions import DataValidationError
from common.logger import get_logger
from services.consumer_ruleset_registration import ConsumerRulesetRegistrationService
from services.ruleengine_exec import (
    dmn_rules_exec,
    rules_exec,
    rules_exec_batch,
    rules_exec_by_ruleset,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/rules",
    tags=["rules"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


def _effective_correlation_id(
    header_or_state_id: Optional[str], body_correlation_id: Optional[str]
) -> Optional[str]:
    if body_correlation_id:
        return body_correlation_id
    return header_or_state_id


def _dry_run_evaluations_from_result(
    result: Dict[str, Any], dry_run: bool
) -> Tuple[
    Optional[List[RuleEvaluationResult]],
    Optional[List[RuleEvaluationResult]],
    Optional[List[RuleEvaluationResult]],
]:
    """Build optional evaluation lists for dry-run responses."""
    if not dry_run or "rule_evaluations" not in result:
        return None, None, None
    rule_evaluations = [
        RuleEvaluationResult(**evaluation) for evaluation in result.get("rule_evaluations", [])
    ]
    would_match = None
    if "would_match" in result:
        would_match = [
            RuleEvaluationResult(**evaluation) for evaluation in result.get("would_match", [])
        ]
    would_not_match = None
    if "would_not_match" in result:
        would_not_match = [
            RuleEvaluationResult(**evaluation) for evaluation in result.get("would_not_match", [])
        ]
    return rule_evaluations, would_match, would_not_match


def _rule_execution_response_from_result(
    result: Dict[str, Any],
    dry_run: bool,
    execution_time_ms: float,
    correlation_id: Optional[str],
) -> RuleExecutionResponse:
    rule_evaluations, would_match, would_not_match = _dry_run_evaluations_from_result(
        result, dry_run
    )
    return RuleExecutionResponse(
        total_points=result.get("total_points", 0.0),
        pattern_result=result.get("pattern_result", ""),
        action_recommendation=result.get("action_recommendation"),
        decision_outputs=result.get("decision_outputs"),
        rule_evaluations=rule_evaluations,
        would_match=would_match,
        would_not_match=would_not_match,
        dry_run=result.get("dry_run", dry_run),
        execution_time_ms=execution_time_ms,
        correlation_id=correlation_id,
    )


@router.post(
    "/execute",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules against input data",
    description=(
        "Execute business rules against input data and return scoring results "
        "with action recommendations."
    ),
)
async def execute_rules(
    request: RuleExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> RuleExecutionResponse:
    """Execute rules against input data."""
    start_time = time.time()
    correlation_id = _effective_correlation_id(correlation_id, request.correlation_id)
    logger.info(
        "API rule execution request",
        correlation_id=correlation_id,
        dry_run=request.dry_run,
        data_keys=list(request.data.keys()),
        request_rules_count=(len(request.rules) if request.rules is not None else None),
    )
    result = rules_exec(
        data=request.data,
        dry_run=request.dry_run,
        correlation_id=correlation_id,
        consumer_id=request.consumer_id,
        rules=request.rules,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = _rule_execution_response_from_result(
        result, request.dry_run, execution_time_ms, correlation_id
    )
    logger.info(
        "API rule execution completed",
        correlation_id=correlation_id,
        total_points=response.total_points,
        pattern_result=response.pattern_result,
        execution_time_ms=execution_time_ms,
    )
    return response


@router.post(
    "/{ruleset_name}/execute",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a specific ruleset against input data",
    description=(
        "Execute business rules from a specific ruleset against input data "
        "and return scoring results with action recommendations."
    ),
)
async def execute_ruleset(
    ruleset_name: str,
    request: RuleExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    registration_service: ConsumerRulesetRegistrationService = Depends(
        get_consumer_ruleset_registration_service_dep
    ),
) -> RuleExecutionResponse:
    """Execute a specific ruleset against input data."""
    start_time = time.time()
    correlation_id = _effective_correlation_id(correlation_id, request.correlation_id)
    logger.info(
        "API ruleset execution request",
        correlation_id=correlation_id,
        ruleset_name=ruleset_name,
        dry_run=request.dry_run,
        data_keys=list(request.data.keys()),
    )
    registration_service.ensure_can_execute_ruleset(request.consumer_id, ruleset_name)
    result = rules_exec_by_ruleset(
        ruleset_name=ruleset_name,
        data=request.data,
        dry_run=request.dry_run,
        correlation_id=correlation_id,
        consumer_id=request.consumer_id,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = _rule_execution_response_from_result(
        result, request.dry_run, execution_time_ms, correlation_id
    )
    logger.info(
        "API ruleset execution completed",
        correlation_id=correlation_id,
        ruleset_name=ruleset_name,
        total_points=response.total_points,
        pattern_result=response.pattern_result,
        execution_time_ms=execution_time_ms,
    )
    return response


@router.post(
    "/batch",
    response_model=BatchRuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules against multiple data items",
    description=(
        "Execute rules against multiple input data items in parallel for efficient batch processing. "
        "When the request omits ``rules``, definitions are loaded like ``POST /execute`` "
        "(database when ``USE_DATABASE`` and a DB URL are configured, otherwise file/S3). "
        "If ``USE_DATABASE`` is true, inline rules must not be required for DB loading: "
        "a database URL and database-backed config repository are enforced."
    ),
)
async def execute_rules_batch(
    request: BatchRuleExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> BatchRuleExecutionResponse:
    """Execute rules against multiple data items in batch."""
    start_time = time.time()
    correlation_id = _effective_correlation_id(correlation_id, request.correlation_id)
    logger.info(
        "API batch rule execution request",
        correlation_id=correlation_id,
        batch_size=len(request.data_list),
        dry_run=request.dry_run,
        max_workers=request.max_workers,
    )
    result = rules_exec_batch(
        data_list=request.data_list,
        dry_run=request.dry_run,
        max_workers=request.max_workers,
        correlation_id=correlation_id,
        consumer_id=request.consumer_id,
        rules=request.rules,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    batch_results: List[BatchItemResult] = []
    for item_result in result.get("results", []):
        batch_results.append(
            BatchItemResult(
                item_index=item_result.get("item_index", 0),
                correlation_id=item_result.get("correlation_id", ""),
                status=item_result.get("status", "failed"),
                total_points=item_result.get("total_points"),
                pattern_result=item_result.get("pattern_result"),
                action_recommendation=item_result.get("action_recommendation"),
                error=item_result.get("error"),
                error_type=item_result.get("error_type"),
            )
        )
    response = BatchRuleExecutionResponse(
        batch_id=result.get("batch_id", correlation_id or "unknown"),
        results=batch_results,
        summary=result.get("summary", {}),
        dry_run=result.get("dry_run", request.dry_run),
    )
    logger.info(
        "API batch rule execution completed",
        correlation_id=correlation_id,
        batch_id=response.batch_id,
        total_executions=response.summary.get("total_executions", 0),
        successful=response.summary.get("successful_executions", 0),
        failed=response.summary.get("failed_executions", 0),
        execution_time_ms=execution_time_ms,
    )
    return response


def _validate_dmn_request_source(request: DMNRuleExecutionRequest) -> None:
    try:
        request.validate_dmn_source_provided()
    except ValueError as validation_error:
        msg = str(validation_error)
        code = "MISSING_DMN_SOURCE" if "must be provided" in msg else "MULTIPLE_DMN_SOURCES"
        raise DataValidationError(msg, error_code=code, context={}) from validation_error


@router.post(
    "/execute-dmn",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules from DMN file",
    description=(
        "Execute business rules from a DMN (Decision Model and Notation) file against input data."
    ),
)
async def execute_dmn_rules(
    request: DMNRuleExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> RuleExecutionResponse:
    """Execute rules from a DMN file against input data."""
    start_time = time.time()
    correlation_id = _effective_correlation_id(correlation_id, request.correlation_id)
    logger.info(
        "API DMN rule execution request",
        correlation_id=correlation_id,
        dry_run=request.dry_run,
        has_dmn_file=request.dmn_file is not None,
        has_dmn_content=request.dmn_content is not None,
        data_keys=list(request.data.keys()),
    )
    _validate_dmn_request_source(request)
    result = dmn_rules_exec(
        dmn_file=request.dmn_file,
        dmn_content=request.dmn_content,
        data=request.data,
        dry_run=request.dry_run,
        correlation_id=correlation_id,
        consumer_id=request.consumer_id,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = _rule_execution_response_from_result(
        result, request.dry_run, execution_time_ms, correlation_id
    )
    logger.info(
        "API DMN rule execution completed",
        correlation_id=correlation_id,
        total_points=response.total_points,
        pattern_result=response.pattern_result,
        execution_time_ms=execution_time_ms,
    )
    return response


@router.post(
    "/execute-dmn-upload",
    response_model=RuleExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute rules from uploaded DMN file",
    description="Execute business rules from an uploaded DMN file against input data.",
)
async def execute_dmn_rules_upload(
    file: UploadFile = File(..., description="DMN XML file to upload"),
    data: str = Form(..., description="JSON string containing input data"),
    dry_run: bool = Form(default=False, description="Execute rules without side effects"),
    consumer_id: Optional[str] = Form(default=None, description="Consumer ID for usage tracking"),
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> RuleExecutionResponse:
    """Execute rules from an uploaded DMN file against input data."""
    start_time = time.time()
    logger.info(
        "API DMN rule execution upload request",
        correlation_id=correlation_id,
        filename=file.filename,
        dry_run=dry_run,
    )
    if not file.filename:
        logger.error("No filename provided", correlation_id=correlation_id)
        raise DataValidationError(
            "File must have a filename",
            error_code="MISSING_FILENAME",
            context={},
        )
    if not file.filename.lower().endswith(".dmn"):
        logger.warning(
            "Invalid file extension",
            correlation_id=correlation_id,
            filename=file.filename,
        )
        raise DataValidationError(
            "File must have .dmn extension",
            error_code="INVALID_FILE_TYPE",
            context={"filename": file.filename},
        )
    content = await file.read()
    dmn_content = content.decode("utf-8")
    try:
        input_data = json.loads(data)
    except json.JSONDecodeError as json_error:
        logger.error(
            "Invalid JSON in data field", error=str(json_error), correlation_id=correlation_id
        )
        raise DataValidationError(
            f"Invalid JSON in data field: {str(json_error)}",
            error_code="INVALID_JSON",
            context={},
        ) from json_error
    if not isinstance(input_data, dict):
        logger.error("Data must be a dictionary", correlation_id=correlation_id)
        raise DataValidationError(
            "data must be a dictionary",
            error_code="DATA_INVALID_TYPE",
            context={},
        )
    logger.debug(
        "DMN file content read",
        correlation_id=correlation_id,
        content_length=len(dmn_content),
        data_keys=list(input_data.keys()),
    )
    result = dmn_rules_exec(
        dmn_content=dmn_content,
        data=input_data,
        dry_run=dry_run,
        correlation_id=correlation_id,
        consumer_id=consumer_id,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = _rule_execution_response_from_result(
        result, dry_run, execution_time_ms, correlation_id
    )
    logger.info(
        "API DMN rule execution upload completed",
        correlation_id=correlation_id,
        filename=file.filename,
        total_points=response.total_points,
        pattern_result=response.pattern_result,
        execution_time_ms=execution_time_ms,
    )
    return response
