"""
API routes for DMN file upload and parsing.

This module provides REST API endpoints for uploading DMN (Decision Model Notation)
files and converting them to the rule engine's internal rule format.
"""

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse

from api.models import (
    DMNUploadResponse,
    RuleResponse,
    ErrorResponse
)
from common.dmn_parser import DMNParser
from common.logger import get_logger
from common.exceptions import (
    ConfigurationError,
    DataValidationError
)
from common.security import sanitize_filename, validate_file_path
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/dmn",
    tags=["dmn"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


def _convert_dmn_rule_to_app_format(dmn_rule: dict) -> dict:
    """
    Convert DMN parser output to app's rule format.
    
    DMN parser returns rules with: id, rule_name, attribute, condition, constant,
    message, weight, rule_point, priority, action_result
    
    App format expects: id, rule_name, type, conditions (dict), description,
    result, weight, rule_point, priority, action_result
    
    Note: DMN rules have inline conditions (attribute, equation, constant),
    which are returned in the conditions dict. These differ from the app's
    standard format which uses condition references (e.g., {"item": "C0001"}).
    
    Args:
        dmn_rule: Rule dictionary from DMN parser
        
    Returns:
        Rule dictionary in app format with inline condition details
    """
    # Extract condition details
    attribute = dmn_rule.get('attribute', '')
    condition = dmn_rule.get('condition', 'equal')
    constant = dmn_rule.get('constant', '')
    
    # Create condition dict with inline condition details
    # This format includes the condition details directly since DMN rules
    # don't reference external condition objects
    conditions_dict = {
        'attribute': attribute,
        'equation': condition,
        'constant': constant
    }
    
    # Convert to app format
    app_rule = {
        'id': dmn_rule.get('id', ''),
        'rule_name': dmn_rule.get('rule_name', ''),
        'type': 'simple',  # DMN rules are typically simple (single condition)
        'conditions': conditions_dict,
        'description': dmn_rule.get('message', ''),
        'result': dmn_rule.get('action_result', ''),
        'weight': dmn_rule.get('weight', 1.0),
        'rule_point': dmn_rule.get('rule_point', 10.0),
        'priority': dmn_rule.get('priority', 1),
        'action_result': dmn_rule.get('action_result', '')
    }
    
    return app_rule


@router.post(
    "/upload",
    response_model=DMNUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse DMN file",
    description="Upload a DMN (Decision Model Notation) XML file and convert it to the rule engine's internal rule format."
)
async def upload_dmn_file(
    http_request: Request,
    file: UploadFile = File(..., description="DMN XML file to upload"),
    api_key: Optional[str] = Depends(get_api_key)
) -> DMNUploadResponse:
    """
    Upload and parse a DMN file.
    
    Args:
        file: Uploaded DMN XML file
        http_request: FastAPI request object
        api_key: Optional API key for authentication
        
    Returns:
        DMNUploadResponse containing parsed rules in app format
        
    Raises:
        HTTPException: If file upload or parsing fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None) if http_request else None
    
    logger.info("API DMN upload request", 
                correlation_id=correlation_id, 
                filename=file.filename)
    
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
    
    # Check file extension
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
    
    try:
        # Read file content
        content = await file.read()
        xml_content = content.decode('utf-8')
        
        logger.debug("DMN file content read", 
                    correlation_id=correlation_id, 
                    content_length=len(xml_content))
        
        # Save file to disk
        try:
            # Sanitize filename to prevent path injection
            safe_filename = sanitize_filename(file.filename)
            if safe_filename != file.filename:
                logger.warning("Filename sanitized", 
                             correlation_id=correlation_id,
                             original=file.filename, 
                             sanitized=safe_filename)
            
            # Build file path
            output_dir = "data/input"
            file_path = str(Path(output_dir) / safe_filename)
            
            # Validate path to prevent directory traversal
            validated_path = validate_file_path(file_path, allowed_base=output_dir, must_exist=False)
            file_path = str(validated_path)
            
            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Write file content (use binary mode to preserve file integrity)
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info("DMN file saved successfully", 
                       correlation_id=correlation_id,
                       file_path=file_path)
        except Exception as save_error:
            logger.error("Failed to save DMN file", 
                        correlation_id=correlation_id,
                        error=str(save_error), 
                        exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_type": "ConfigurationError",
                    "message": f"Failed to save uploaded file: {str(save_error)}",
                    "error_code": "FILE_SAVE_ERROR",
                    "correlation_id": correlation_id
                }
            )
        
        # Parse DMN content
        parser = DMNParser()
        parse_result = parser.parse_content(xml_content)
        
        rules_set = parse_result.get('rules_set', [])
        patterns = parse_result.get('patterns', {})
        
        logger.info("DMN file parsed successfully", 
                   correlation_id=correlation_id, 
                   rules_count=len(rules_set))
        
        # Convert DMN rules to app format
        converted_rules = []
        for dmn_rule in rules_set:
            app_rule = _convert_dmn_rule_to_app_format(dmn_rule)
            converted_rules.append(app_rule)
        
        # Convert to response models
        rules = [RuleResponse(**rule) for rule in converted_rules]
        
        logger.info("DMN upload completed", 
                   correlation_id=correlation_id, 
                   rules_count=len(rules))
        
        return DMNUploadResponse(
            filename=file.filename,
            file_path=file_path,
            rules=rules,
            patterns=patterns,
            rules_count=len(rules),
            correlation_id=correlation_id
        )
        
    except UnicodeDecodeError as e:
        logger.error("Failed to decode DMN file", 
                    correlation_id=correlation_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "DataValidationError",
                "message": f"File must be valid UTF-8 encoded XML: {str(e)}",
                "error_code": "INVALID_ENCODING",
                "correlation_id": correlation_id
            }
        )
    except ConfigurationError as e:
        logger.error("DMN parsing error", 
                    correlation_id=correlation_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                **e.to_dict(),
                "correlation_id": correlation_id
            }
        )
    except DataValidationError as e:
        logger.error("Data validation error parsing DMN", 
                    correlation_id=correlation_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                **e.to_dict(),
                "correlation_id": correlation_id
            }
        )
    except Exception as e:
        logger.error("Unexpected error parsing DMN file", 
                    correlation_id=correlation_id, 
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "DMN_PARSE_ERROR",
                "correlation_id": correlation_id
            }
        )
