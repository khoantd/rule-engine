"""
Workflow Management Service with Database Integration.

This module provides services for managing workflow definitions, including
CRUD operations backed by the database. Workflows are global, named
definitions composed of ordered stages and can be executed by name via
services.workflow_exec.wf_exec.
"""

from typing import Any, Dict, List, Optional, Tuple

from common.logger import get_logger
from common.exceptions import DataValidationError, ConfigurationError, WorkflowError
from common.repository.db_repository import WorkflowRepository
from common.db_models import Workflow
from common.db_connection import get_db_session

logger = get_logger(__name__)


class WorkflowManagementService:
    """
    Service for managing workflow definitions using database storage.
    """

    def __init__(self, workflow_repository: Optional[WorkflowRepository] = None) -> None:
        """
        Initialize workflow management service.

        Args:
            workflow_repository: Optional workflow repository. If None, creates new instance.
        """
        self.workflow_repository = workflow_repository or WorkflowRepository()
        logger.debug("WorkflowManagementService initialized")

    @staticmethod
    def _validate_workflow_name(name: str) -> str:
        """
        Validate and normalize workflow name.

        Args:
            name: Raw workflow name

        Returns:
            Normalized workflow name

        Raises:
            DataValidationError: If name is empty or invalid
        """
        if name is None:
            raise DataValidationError(
                "Workflow name cannot be None",
                error_code="WORKFLOW_NAME_EMPTY",
                context={"name": name},
            )
        value = name.strip()
        if not value:
            raise DataValidationError(
                "Workflow name cannot be empty",
                error_code="WORKFLOW_NAME_EMPTY",
                context={"name": name},
            )
        return value

    @staticmethod
    def _validate_stages(stages: List[str]) -> List[str]:
        """
        Validate and normalize workflow stages.

        Args:
            stages: List of stage names

        Returns:
            Normalized list of stage names

        Raises:
            DataValidationError: If stages list is invalid
        """
        if not isinstance(stages, list) or len(stages) == 0:
            raise DataValidationError(
                "stages must be a non-empty list",
                error_code="WORKFLOW_STAGES_EMPTY",
                context={"stages": stages},
            )

        cleaned: List[str] = []
        for index, stage in enumerate(stages):
            if not isinstance(stage, str):
                raise DataValidationError(
                    f"Stage at index {index} must be a string",
                    error_code="WORKFLOW_STAGE_INVALID_TYPE",
                    context={"index": index, "stage": stage},
                )
            value = stage.strip()
            if not value:
                raise DataValidationError(
                    f"Stage at index {index} cannot be empty",
                    error_code="WORKFLOW_STAGE_EMPTY",
                    context={"index": index},
                )
            cleaned.append(value)

        return cleaned

    def create_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow definition.

        Args:
            data: Workflow data containing:
                - name: Workflow name (required)
                - description: Optional description
                - stages: Non-empty list of stage names (required)

        Returns:
            Created workflow dictionary

        Raises:
            DataValidationError: If input is invalid or name already exists
            ConfigurationError: If creation fails
        """
        raw_name = data.get("name")
        name = self._validate_workflow_name(raw_name)
        stages_raw = data.get("stages")
        stages = self._validate_stages(stages_raw or [])

        logger.debug("Creating workflow", workflow_name=name, stages=stages)

        try:
            # Check if workflow already exists (active or inactive)
            existing = self.workflow_repository.get_workflow_by_name(
                name, include_inactive=True
            )
            if existing:
                raise DataValidationError(
                    f"Workflow with name '{name}' already exists",
                    error_code="WORKFLOW_NAME_EXISTS",
                    context={"name": name},
                )

            with get_db_session() as session:
                workflow = self.workflow_repository.create_workflow(
                    name=name,
                    description=data.get("description"),
                    stages=stages,
                    is_active=True,
                    session=session,
                )

                logger.info("Workflow created successfully", workflow_name=name)
                return self._workflow_to_dict(workflow)

        except DataValidationError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to create workflow",
                workflow_name=name,
                error=str(exc),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to create workflow: {str(exc)}",
                error_code="WORKFLOW_CREATE_ERROR",
                context={"name": name, "error": str(exc)},
            ) from exc

    def list_workflows(
        self,
        is_active: Optional[bool],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """
        List workflows with optional active filter and pagination.

        Args:
            is_active: Optional filter for active flag
            offset: Pagination offset
            limit: Page size

        Returns:
            Dictionary with:
                - workflows: List of workflow dicts
                - count: Number of workflows in the list
        """
        logger.debug(
            "Listing workflows",
            is_active=is_active,
            offset=offset,
            limit=limit,
        )
        try:
            workflows = self.workflow_repository.list_workflows(
                is_active=is_active,
                offset=offset,
                limit=limit,
            )
            result = [self._workflow_to_dict(wf) for wf in workflows]
            logger.info(
                "Workflows listed successfully",
                count=len(result),
                is_active=is_active,
            )
            return {"workflows": result, "count": len(result)}
        except Exception as exc:
            logger.error(
                "Failed to list workflows",
                error=str(exc),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to list workflows: {str(exc)}",
                error_code="WORKFLOW_LIST_ERROR",
                context={"error": str(exc)},
            ) from exc

    def get_workflow(self, name: str, include_inactive: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a workflow definition by name.

        Args:
            name: Workflow name
            include_inactive: Whether to include inactive workflows

        Returns:
            Workflow dictionary if found, None otherwise

        Raises:
            DataValidationError: If name is invalid
            ConfigurationError: If retrieval fails
        """
        normalized_name = self._validate_workflow_name(name)
        logger.debug(
            "Getting workflow",
            workflow_name=normalized_name,
            include_inactive=include_inactive,
        )

        try:
            workflow = self.workflow_repository.get_workflow_by_name(
                normalized_name,
                include_inactive=include_inactive,
            )
            if not workflow:
                logger.warning("Workflow not found", workflow_name=normalized_name)
                return None

            logger.info("Workflow found", workflow_name=normalized_name)
            return self._workflow_to_dict(workflow)
        except DataValidationError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to get workflow",
                workflow_name=normalized_name,
                error=str(exc),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get workflow {normalized_name}: {str(exc)}",
                error_code="WORKFLOW_GET_ERROR",
                context={"name": normalized_name, "error": str(exc)},
            ) from exc

    def update_workflow(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing workflow definition.

        Args:
            name: Existing workflow name
            data: Fields to update:
                - description: Optional new description
                - stages: Optional new ordered list of stages
                - is_active: Optional active flag

        Returns:
            Updated workflow dictionary

        Raises:
            DataValidationError: If input is invalid or workflow not found
            ConfigurationError: If update fails
        """
        normalized_name = self._validate_workflow_name(name)
        if not data:
            raise DataValidationError(
                "Update payload cannot be empty",
                error_code="WORKFLOW_UPDATE_EMPTY",
                context={"name": normalized_name},
            )

        logger.debug("Updating workflow", workflow_name=normalized_name, data=data)

        description: Optional[Optional[str]] = data.get("description") if "description" in data else None
        stages_raw: Optional[List[str]] = data.get("stages") if "stages" in data else None
        is_active: Optional[bool] = data.get("is_active") if "is_active" in data else None

        stages: Optional[List[str]] = None
        if stages_raw is not None:
            stages = self._validate_stages(stages_raw)

        try:
            workflow = self.workflow_repository.update_workflow(
                name=normalized_name,
                description=description,
                stages=stages,
                is_active=is_active,
            )
            if not workflow:
                raise DataValidationError(
                    f"Workflow with name '{normalized_name}' not found",
                    error_code="WORKFLOW_NOT_FOUND",
                    context={"name": normalized_name},
                )

            logger.info("Workflow updated successfully", workflow_name=normalized_name)
            return self._workflow_to_dict(workflow)
        except DataValidationError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to update workflow",
                workflow_name=normalized_name,
                error=str(exc),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to update workflow: {str(exc)}",
                error_code="WORKFLOW_UPDATE_ERROR",
                context={"name": normalized_name, "error": str(exc)},
            ) from exc

    def delete_workflow(self, name: str, hard: bool = False) -> None:
        """
        Delete (deactivate) a workflow definition.

        Args:
            name: Workflow name
            hard: If True, hard-delete the workflow and stages. Otherwise soft delete.

        Raises:
            DataValidationError: If name is invalid or workflow not found
            ConfigurationError: If deletion fails
        """
        normalized_name = self._validate_workflow_name(name)
        logger.debug("Deleting workflow", workflow_name=normalized_name, hard=hard)

        try:
            deleted = self.workflow_repository.delete_workflow(
                name=normalized_name,
                hard=hard,
            )
            if not deleted:
                raise DataValidationError(
                    f"Workflow with name '{normalized_name}' not found",
                    error_code="WORKFLOW_NOT_FOUND",
                    context={"name": normalized_name},
                )

            logger.info(
                "Workflow deleted successfully",
                workflow_name=normalized_name,
                hard=hard,
            )
        except DataValidationError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to delete workflow",
                workflow_name=normalized_name,
                hard=hard,
                error=str(exc),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to delete workflow: {str(exc)}",
                error_code="WORKFLOW_DELETE_ERROR",
                context={"name": normalized_name, "hard": hard, "error": str(exc)},
            ) from exc

    @staticmethod
    def _workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
        """
        Convert Workflow model to dictionary expected by API.

        Args:
            workflow: Workflow model instance

        Returns:
            Dictionary representation compatible with WorkflowResponse
        """
        # Use model's own conversion for consistency
        data = workflow.to_dict()
        return data


_workflow_management_service: Optional[WorkflowManagementService] = None


def get_workflow_management_service() -> WorkflowManagementService:
    """
    Get global workflow management service instance.

    Returns:
        WorkflowManagementService instance
    """
    global _workflow_management_service
    if _workflow_management_service is None:
        _workflow_management_service = WorkflowManagementService()
    return _workflow_management_service

