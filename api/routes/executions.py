"""
Query persisted rule execution logs.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import get_execution_query_service_dep
from api.models import ExecutionLogsListResponse, ExecutionLogSummaryResponse
from common.exceptions import DataValidationError
from common.logger import get_logger
from services.execution_query import ExecutionQueryService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


def _parse_optional_datetime(value: Optional[str], field: str) -> Optional[datetime]:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError as e:
        raise DataValidationError(
            "Invalid datetime (use ISO 8601)",
            error_code="INVALID_DATETIME",
            context={field: value, "error": str(e)},
        ) from e


@router.get("", response_model=ExecutionLogsListResponse)
async def list_executions(
    consumer_id: Optional[str] = Query(None, description="Filter by consumer business id"),
    ruleset_id: Optional[int] = Query(None, description="Filter by ruleset primary key"),
    from_ts: Optional[str] = Query(
        None,
        alias="from",
        description="Inclusive start (ISO 8601)",
    ),
    to_ts: Optional[str] = Query(
        None,
        alias="to",
        description="Exclusive end (ISO 8601)",
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_payload: bool = Query(
        False,
        description="Include input_data and output_data (may contain sensitive data)",
    ),
    service: ExecutionQueryService = Depends(get_execution_query_service_dep),
) -> ExecutionLogsListResponse:
    """List execution log rows with optional filters and pagination."""
    parsed_from = _parse_optional_datetime(from_ts, "from")
    parsed_to = _parse_optional_datetime(to_ts, "to")
    rows, total = service.list_executions(
        consumer_id=consumer_id,
        ruleset_id=ruleset_id,
        from_ts=parsed_from,
        to_ts=parsed_to,
        limit=limit,
        offset=offset,
        include_payload=include_payload,
    )
    executions = [ExecutionLogSummaryResponse(**r) for r in rows]
    return ExecutionLogsListResponse(
        executions=executions,
        total=total,
        limit=limit,
        offset=offset,
    )
