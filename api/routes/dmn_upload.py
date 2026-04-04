"""
API routes for DMN file upload and parsing.

This module provides REST API endpoints for uploading DMN (Decision Model Notation)
files and converting them to the rule engine's internal rule format.

Domain exceptions propagate to ``api.middleware.errors``.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, status

from api.deps import get_correlation_id
from api.middleware.auth import get_api_key
from api.models import DMNUploadResponse, ErrorResponse, RuleResponse
from common.dmn_parser import DMNParser
from common.exceptions import ConfigurationError, DataValidationError
from common.logger import get_logger
from common.security import sanitize_filename, validate_file_path

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/dmn",
    tags=["dmn"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


def _convert_dmn_rule_to_app_format(dmn_rule: dict) -> dict:
    """
    Convert DMN parser output to app's rule format.

    Args:
        dmn_rule: Rule dictionary from DMN parser

    Returns:
        Rule dictionary in app format with inline condition details
    """
    attribute = dmn_rule.get("attribute", "")
    condition = dmn_rule.get("condition", "equal")
    constant = dmn_rule.get("constant", "")

    conditions_dict = {
        "attribute": attribute,
        "equation": condition,
        "constant": constant,
    }

    return {
        "id": dmn_rule.get("id", ""),
        "rule_name": dmn_rule.get("rule_name", ""),
        "type": "simple",
        "conditions": conditions_dict,
        "description": dmn_rule.get("message", ""),
        "result": dmn_rule.get("action_result", ""),
        "weight": dmn_rule.get("weight", 1.0),
        "rule_point": dmn_rule.get("rule_point", 10.0),
        "priority": dmn_rule.get("priority", 1),
        "action_result": dmn_rule.get("action_result", ""),
    }


@router.post(
    "/upload",
    response_model=DMNUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse DMN file",
    description=(
        "Upload a DMN (Decision Model Notation) XML file and convert it to the "
        "rule engine's internal rule format."
    ),
)
async def upload_dmn_file(
    file: UploadFile = File(..., description="DMN XML file to upload"),
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> DMNUploadResponse:
    """Upload and parse a DMN file."""
    logger.info("API DMN upload request", correlation_id=correlation_id, filename=file.filename)

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
    try:
        xml_content = content.decode("utf-8")
    except UnicodeDecodeError as e:
        logger.error(
            "Failed to decode DMN file",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True,
        )
        raise DataValidationError(
            f"File must be valid UTF-8 encoded XML: {str(e)}",
            error_code="INVALID_ENCODING",
            context={},
        ) from e

    logger.debug(
        "DMN file content read",
        correlation_id=correlation_id,
        content_length=len(xml_content),
    )

    safe_filename = sanitize_filename(file.filename)
    if safe_filename != file.filename:
        logger.warning(
            "Filename sanitized",
            correlation_id=correlation_id,
            original=file.filename,
            sanitized=safe_filename,
        )

    output_dir = "data/input"
    file_path = str(Path(output_dir) / safe_filename)
    validated_path = validate_file_path(file_path, allowed_base=output_dir, must_exist=False)
    file_path = str(validated_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(
            "DMN file saved successfully", correlation_id=correlation_id, file_path=file_path
        )
    except OSError as save_error:
        logger.error(
            "Failed to save DMN file",
            correlation_id=correlation_id,
            error=str(save_error),
            exc_info=True,
        )
        raise ConfigurationError(
            f"Failed to save uploaded file: {str(save_error)}",
            error_code="FILE_SAVE_ERROR",
            context={"file_path": file_path},
        ) from save_error

    parser = DMNParser()
    parse_result = parser.parse_content(xml_content)

    rules_set = parse_result.get("rules_set", [])
    patterns = parse_result.get("patterns", {})

    logger.info(
        "DMN file parsed successfully",
        correlation_id=correlation_id,
        rules_count=len(rules_set),
    )

    converted_rules = [_convert_dmn_rule_to_app_format(dmn_rule) for dmn_rule in rules_set]
    rules = [RuleResponse(**rule) for rule in converted_rules]

    logger.info("DMN upload completed", correlation_id=correlation_id, rules_count=len(rules))

    return DMNUploadResponse(
        filename=file.filename,
        file_path=file_path,
        rules=rules,
        patterns=patterns,
        rules_count=len(rules),
        correlation_id=correlation_id,
    )
