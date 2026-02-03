"""
Usage Tracking Service.

This module provides services for tracking rule execution usage by consumers.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from common.logger import get_logger
from common.db_connection import get_db_session
from common.db_models import ConsumerRuleUsage

logger = get_logger(__name__)


class UsageTrackingService:
    """Service for tracking consumer rule usage."""

    def track_usage(
        self,
        consumer_id: str,
        rule_ids: List[str],
        ruleset_id: Optional[int] = None
    ) -> None:
        """
        Track usage of rules by a consumer.
        
        increments the execution count and updates the last executed timestamp
        for the given consumer and rules.
        
        Args:
            consumer_id: Consumer identifier
            rule_ids: List of rule identifiers that were executed/matched
            ruleset_id: Optional ruleset identifier
        """
        if not consumer_id or not rule_ids:
            return

        try:
            with get_db_session() as session:
                for rule_id in rule_ids:
                    # Upsert logic: insert or update if exists
                    stmt = insert(ConsumerRuleUsage).values(
                        consumer_id=consumer_id,
                        rule_id=rule_id,
                        ruleset_id=ruleset_id,
                        execution_count=1,
                        last_executed_at=datetime.utcnow()
                    )
                    
                    # On conflict (consumer_id + rule_id exists), increment count and update timestamp
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['consumer_id', 'rule_id'],
                        set_={
                            "execution_count": ConsumerRuleUsage.execution_count + 1,
                            "last_executed_at": datetime.utcnow(),
                            # Update ruleset_id if provided (it might change if rule moves to new ruleset)
                            "ruleset_id": ruleset_id if ruleset_id is not None else ConsumerRuleUsage.ruleset_id
                        }
                    )
                    
                    session.execute(stmt)
                
                logger.debug(
                    "Tracked usage for consumer",
                    consumer_id=consumer_id,
                    rule_count=len(rule_ids)
                )

        except Exception as e:
            # Aggregate exception to avoid breaking rule execution flow
            logger.error(
                "Failed to track usage",
                consumer_id=consumer_id,
                error=str(e),
                exc_info=True
            )

# Global service instance
_usage_tracking_service: Optional[UsageTrackingService] = None


def get_usage_tracking_service() -> UsageTrackingService:
    """Get global service instance."""
    global _usage_tracking_service
    if _usage_tracking_service is None:
        _usage_tracking_service = UsageTrackingService()
    return _usage_tracking_service
