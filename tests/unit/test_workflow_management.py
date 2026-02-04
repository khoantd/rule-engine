"""
Unit tests for services.workflow_management module.
"""

from typing import Any, Dict, List, Optional

import pytest

from services.workflow_management import WorkflowManagementService
from common.exceptions import DataValidationError


class FakeWorkflow:
    """Simple in-memory workflow representation for tests."""

    def __init__(self, name: str, description: Optional[str], is_active: bool, stages: List[Dict[str, Any]]):
        self._name = name
        self._description = description
        self._is_active = is_active
        self._stages = stages

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def stages(self) -> List[Any]:
        # Expose minimal interface expected by to_dict() in service
        class _Stage:
            def __init__(self, name: str, position: int) -> None:
                self.name = name
                self.position = position

            def to_dict(self) -> Dict[str, Any]:
                return {"name": self.name, "position": self.position}

        return [
            _Stage(stage["name"], stage["position"]) for stage in self._stages
        ]

    @property
    def created_at(self) -> None:
        return None

    @property
    def updated_at(self) -> None:
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "is_active": self._is_active,
            "stages": self._stages,
            "created_at": None,
            "updated_at": None,
        }


class FakeWorkflowRepository:
    """Fake repository for testing WorkflowManagementService without a database."""

    def __init__(self) -> None:
        self._store: Dict[str, FakeWorkflow] = {}

    def get_workflow_by_name(self, name: str, include_inactive: bool = False) -> Optional[FakeWorkflow]:
        workflow = self._store.get(name)
        if workflow and (include_inactive or workflow.is_active):
            return workflow
        return None

    def create_workflow(
        self,
        name: str,
        description: Optional[str],
        stages: List[str],
        is_active: bool = True,
        session: Any = None,
    ) -> FakeWorkflow:
        fake_stages = [
            {"name": stage_name, "position": index}
            for index, stage_name in enumerate(stages, start=1)
        ]
        workflow = FakeWorkflow(name=name, description=description, is_active=is_active, stages=fake_stages)
        self._store[name] = workflow
        return workflow

    def list_workflows(
        self,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[FakeWorkflow]:
        values = list(self._store.values())
        if is_active is not None:
            values = [wf for wf in values if wf.is_active == is_active]
        return values[offset : offset + limit]

    def update_workflow(
        self,
        name: str,
        description: Optional[Optional[str]] = None,
        stages: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        session: Any = None,
    ) -> Optional[FakeWorkflow]:
        workflow = self._store.get(name)
        if not workflow:
            return None

        if description is not None:
            workflow._description = description
        if is_active is not None:
            workflow._is_active = is_active
        if stages is not None:
            fake_stages = [
                {"name": stage_name, "position": index}
                for index, stage_name in enumerate(stages, start=1)
            ]
            workflow._stages = fake_stages
        return workflow

    def delete_workflow(
        self,
        name: str,
        hard: bool = False,
    ) -> bool:
        workflow = self._store.get(name)
        if not workflow:
            return False
        if hard:
            del self._store[name]
        else:
            workflow._is_active = False
        return True


class TestWorkflowManagementService:
    """Unit tests for WorkflowManagementService using a fake repository."""

    def setup_method(self) -> None:
        self.repo = FakeWorkflowRepository()
        self.service = WorkflowManagementService(workflow_repository=self.repo)

    def test_create_workflow_success(self) -> None:
        """Create workflow with valid data succeeds."""
        data = {
            "name": "ticket_processing",
            "description": "Standard ticket workflow",
            "stages": ["INITIATED", "NEW", "FINISHED"],
        }

        result = self.service.create_workflow(data)

        assert result["name"] == "ticket_processing"
        assert result["is_active"] is True
        assert [s["name"] for s in result["stages"]] == ["INITIATED", "NEW", "FINISHED"]

    def test_create_workflow_duplicate_name_raises(self) -> None:
        """Creating a workflow with an existing name raises DataValidationError."""
        data = {
            "name": "ticket_processing",
            "description": "Standard ticket workflow",
            "stages": ["INITIATED"],
        }
        self.service.create_workflow(data)

        with pytest.raises(DataValidationError) as exc_info:
            self.service.create_workflow(data)

        assert exc_info.value.error_code == "WORKFLOW_NAME_EXISTS"

    def test_create_workflow_invalid_name_raises(self) -> None:
        """Empty workflow name raises DataValidationError."""
        data = {"name": "  ", "stages": ["INITIATED"]}

        with pytest.raises(DataValidationError) as exc_info:
            self.service.create_workflow(data)

        assert exc_info.value.error_code == "WORKFLOW_NAME_EMPTY"

    def test_create_workflow_invalid_stages_raises(self) -> None:
        """Empty stages list raises DataValidationError."""
        data = {"name": "ticket_processing", "stages": []}

        with pytest.raises(DataValidationError) as exc_info:
            self.service.create_workflow(data)

        assert exc_info.value.error_code == "WORKFLOW_STAGES_EMPTY"

    def test_list_workflows_returns_created_workflow(self) -> None:
        """list_workflows returns created workflows."""
        self.service.create_workflow(
            {"name": "wf1", "stages": ["A", "B"], "description": None}
        )

        result = self.service.list_workflows(is_active=None, offset=0, limit=10)

        assert result["count"] == 1
        assert result["workflows"][0]["name"] == "wf1"

    def test_get_workflow_returns_existing_workflow(self) -> None:
        """get_workflow returns existing workflow."""
        self.service.create_workflow(
            {"name": "wf1", "stages": ["A"], "description": None}
        )

        workflow = self.service.get_workflow("wf1")

        assert workflow is not None
        assert workflow["name"] == "wf1"

    def test_update_workflow_updates_fields(self) -> None:
        """update_workflow updates description and stages."""
        self.service.create_workflow(
            {"name": "wf1", "stages": ["A"], "description": "original"}
        )

        updated = self.service.update_workflow(
            "wf1",
            {
                "description": "updated",
                "stages": ["B", "C"],
                "is_active": False,
            },
        )

        assert updated["description"] == "updated"
        assert [s["name"] for s in updated["stages"]] == ["B", "C"]
        assert updated["is_active"] is False

    def test_update_workflow_not_found_raises(self) -> None:
        """Updating a non-existing workflow raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            self.service.update_workflow("missing", {"description": "x"})

        assert exc_info.value.error_code == "WORKFLOW_NOT_FOUND"

    def test_delete_workflow_soft(self) -> None:
        """Soft delete marks workflow as inactive."""
        self.service.create_workflow(
            {"name": "wf1", "stages": ["A"], "description": None}
        )

        self.service.delete_workflow("wf1", hard=False)
        workflow = self.service.get_workflow("wf1", include_inactive=True)

        assert workflow is not None
        assert workflow["is_active"] is False

    def test_delete_workflow_not_found_raises(self) -> None:
        """Deleting non-existing workflow raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            self.service.delete_workflow("missing", hard=False)

        assert exc_info.value.error_code == "WORKFLOW_NOT_FOUND"

