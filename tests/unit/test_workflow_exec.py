"""
Unit tests for services.workflow_exec module.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any

from services.workflow_exec import (
    workflow_setup,
    validate_workflow_inputs,
    wf_exec
)
from common.exceptions import DataValidationError, WorkflowError
from common.pattern.cor.handler import Handler


class TestValidateWorkflowInputs:
    """Tests for validate_workflow_inputs function."""
    
    def test_validate_workflow_inputs_valid(self, sample_input_data):
        """Test validation with valid inputs."""
        result = validate_workflow_inputs("process1", ["INITIATED", "NEW"], sample_input_data)
        assert result[0] == "process1"
        assert result[1] == ["INITIATED", "NEW"]
        assert result[2] == sample_input_data
    
    def test_validate_workflow_inputs_empty_process_name(self):
        """Test validation with empty process name raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs("", ["STAGE1"], {})
        
        assert exc_info.value.error_code == "PROCESS_NAME_EMPTY"
    
    def test_validate_workflow_inputs_none_process_name(self):
        """Test validation with None process name raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs(None, ["STAGE1"], {})
        
        assert exc_info.value.error_code == "PROCESS_NAME_EMPTY"
    
    def test_validate_workflow_inputs_invalid_process_name_type(self):
        """Test validation with invalid process name type raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs(123, ["STAGE1"], {})
        
        assert exc_info.value.error_code == "PROCESS_NAME_INVALID_TYPE"
    
    def test_validate_workflow_inputs_invalid_stages_type(self):
        """Test validation with invalid stages type raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs("process1", "not a list", {})
        
        assert exc_info.value.error_code == "STAGES_INVALID_TYPE"
    
    def test_validate_workflow_inputs_invalid_stage_item_type(self):
        """Test validation with invalid stage item type raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs("process1", [123, "STAGE2"], {})
        
        assert exc_info.value.error_code == "STAGE_INVALID_TYPE"
    
    def test_validate_workflow_inputs_invalid_data_type(self):
        """Test validation with invalid data type raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_workflow_inputs("process1", ["STAGE1"], "not a dict")
        
        assert exc_info.value.error_code == "DATA_INVALID_TYPE"
    
    def test_validate_workflow_inputs_none_data(self):
        """Test validation with None data converts to empty dict."""
        result = validate_workflow_inputs("process1", ["STAGE1"], None)
        assert result[2] == {}


class TestWorkflowSetup:
    """Tests for workflow_setup function."""
    
    @patch('services.workflow_exec.get_container')
    @patch('services.workflow_exec.get_handler_factory')
    def test_workflow_setup_success(
        self,
        mock_get_factory,
        mock_get_container,
        sample_ext_rule
    ):
        """Test successful workflow setup."""
        mock_factory = MagicMock()
        mock_handler = MagicMock(spec=Handler)
        mock_factory.create_handler_chain.return_value = mock_handler
        mock_get_factory.return_value = mock_factory
        
        mock_container = MagicMock()
        mock_container.has.return_value = False
        mock_get_container.return_value = mock_container
        
        result = workflow_setup()
        
        assert result == mock_handler
        mock_factory.create_handler_chain.assert_called_once()
    
    @patch('services.workflow_exec.get_container')
    @patch('services.workflow_exec.get_handler_factory')
    def test_workflow_setup_with_factory(
        self,
        mock_get_factory,
        mock_get_container
    ):
        """Test workflow setup with provided factory."""
        mock_factory = MagicMock()
        mock_handler = MagicMock(spec=Handler)
        mock_factory.create_handler_chain.return_value = mock_handler
        
        result = workflow_setup(mock_factory)
        
        assert result == mock_handler
        mock_factory.create_handler_chain.assert_called_once()
        mock_get_factory.assert_not_called()
    
    @patch('services.workflow_exec.get_container')
    @patch('services.workflow_exec.get_handler_factory')
    def test_workflow_setup_error(
        self,
        mock_get_factory,
        mock_get_container
    ):
        """Test workflow setup with error raises WorkflowError."""
        mock_factory = MagicMock()
        mock_factory.create_handler_chain.side_effect = Exception("Setup error")
        mock_get_factory.return_value = mock_factory
        
        mock_container = MagicMock()
        mock_container.has.return_value = False
        mock_get_container.return_value = mock_container
        
        with pytest.raises(WorkflowError) as exc_info:
            workflow_setup()
        
        assert exc_info.value.error_code == "WORKFLOW_SETUP_ERROR"


class TestWfExec:
    """Tests for wf_exec function."""
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_success(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test successful workflow execution."""
        mock_handler = MagicMock(spec=Handler)
        mock_handler.handle.return_value = {
            "data": {"result": "success"},
            "status": "completed"
        }
        mock_workflow_setup.return_value = mock_handler
        
        result = wf_exec("process1", ["INITIATED", "NEW"], sample_input_data)
        
        assert result["status"] == "completed"
        assert mock_handler.handle.call_count == 2  # Two stages
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_default_stages(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test workflow execution with default stages."""
        mock_handler = MagicMock(spec=Handler)
        mock_handler.handle.return_value = {"data": {}}
        mock_workflow_setup.return_value = mock_handler
        
        result = wf_exec("process1", [], sample_input_data)
        
        # Should use default stages
        assert mock_handler.handle.call_count == 4  # Default 4 stages
    
    def test_wf_exec_invalid_input(self):
        """Test workflow execution with invalid input raises DataValidationError."""
        with pytest.raises(DataValidationError):
            wf_exec("", ["STAGE1"], {})
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_setup_error(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test workflow execution with setup error raises WorkflowError."""
        mock_workflow_setup.side_effect = WorkflowError("Setup error", error_code="SETUP_ERROR")
        
        with pytest.raises(WorkflowError) as exc_info:
            wf_exec("process1", ["STAGE1"], sample_input_data)
        
        assert exc_info.value.error_code == "SETUP_ERROR"
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_handler_none(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test workflow execution with None handler raises WorkflowError."""
        mock_workflow_setup.return_value = None
        
        with pytest.raises(WorkflowError) as exc_info:
            wf_exec("process1", ["STAGE1"], sample_input_data)
        
        assert exc_info.value.error_code == "HANDLER_NONE"
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_invalid_result(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test workflow execution with invalid result raises WorkflowError."""
        mock_handler = MagicMock(spec=Handler)
        mock_handler.handle.return_value = "not a dict"  # Invalid result
        mock_workflow_setup.return_value = mock_handler
        
        with pytest.raises(WorkflowError) as exc_info:
            wf_exec("process1", ["STAGE1"], sample_input_data)
        
        assert exc_info.value.error_code == "STEP_RESULT_INVALID"
    
    @patch('services.workflow_exec.workflow_setup')
    def test_wf_exec_handler_error(
        self,
        mock_workflow_setup,
        sample_input_data
    ):
        """Test workflow execution with handler error raises WorkflowError."""
        mock_handler = MagicMock(spec=Handler)
        mock_handler.handle.side_effect = Exception("Handler error")
        mock_workflow_setup.return_value = mock_handler
        
        with pytest.raises(WorkflowError) as exc_info:
            wf_exec("process1", ["STAGE1"], sample_input_data)
        
        assert exc_info.value.error_code == "STEP_EXECUTION_ERROR"

