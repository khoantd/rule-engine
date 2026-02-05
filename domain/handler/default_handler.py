from dataclasses import dataclass
from typing import Any, Optional

from common.pattern.cor.handler import AbstractHandler
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DefaultHandler(AbstractHandler):
    """
    Catch-all handler for workflow stages that do not match NEW, INPROGESS, or FINISHED.
    Returns a pass-through result so custom stage names (e.g. from credit_approval_workflow)
    do not cause None and WorkflowError. Data is returned unchanged.
    """

    def handle(
        self,
        process_name: str = "default",
        request: Any = Optional,
        data: Any = Optional,
    ) -> Any:
        if request == self._stage:
            return {
                "step": request,
                "data": data if isinstance(data, dict) else {},
                "histories": [],
            }
        # Pass-through for any other stage (custom names like "Eligibility Check")
        # so the chain never returns None and wf_exec does not raise STEP_RESULT_INVALID.
        logger.debug(
            "DefaultHandler pass-through for unmatched stage",
            process_name=process_name,
            step=request,
        )
        return {
            "process_name": process_name,
            "step": request,
            "data": data if isinstance(data, dict) else {},
        }
