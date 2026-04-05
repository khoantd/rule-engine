"""
Read-only queries for persisted rule execution logs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from common.logger import get_logger
from common.repository.db_repository import ExecutionLogRepository

logger = get_logger(__name__)


class ExecutionQueryService:
    """List execution log rows with optional filters."""

    def __init__(self, repository: Optional[ExecutionLogRepository] = None) -> None:
        self._repository = repository or ExecutionLogRepository()

    def list_executions(
        self,
        consumer_id: Optional[str] = None,
        ruleset_id: Optional[int] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        include_payload: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Return execution summaries and total count matching filters.

        Args:
            consumer_id: Filter by consumer business id
            ruleset_id: Filter by ruleset primary key
            from_ts: Inclusive lower bound on ``ExecutionLog.timestamp``
            to_ts: Exclusive upper bound on ``ExecutionLog.timestamp``
            limit: Maximum rows to return
            offset: Row offset for pagination
            include_payload: Include ``input_data`` and ``output_data`` in each dict

        Returns:
            Tuple of (list of dicts, total matching count before limit/offset)
        """
        rows, total = self._repository.list_logs(
            consumer_id=consumer_id,
            ruleset_id=ruleset_id,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
            offset=offset,
            include_payload=include_payload,
        )
        out: List[Dict[str, Any]] = []
        for row in rows:
            item: Dict[str, Any] = {
                "id": row.id,
                "execution_id": row.execution_id,
                "correlation_id": None,
                "ruleset_id": row.ruleset_id,
                "consumer_id": row.consumer_id,
                "total_points": row.total_points,
                "pattern_result": row.pattern_result,
                "execution_time_ms": row.execution_time_ms,
                "success": row.success,
                "error_message": row.error_message,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            if include_payload:
                item["input_data"] = row.input_data
                item["output_data"] = row.output_data
            out.append(item)
        return out, total


_service: Optional[ExecutionQueryService] = None


def get_execution_query_service() -> ExecutionQueryService:
    global _service
    if _service is None:
        _service = ExecutionQueryService()
    return _service


def set_execution_query_service(service: Optional[ExecutionQueryService]) -> None:
    global _service
    _service = service
