
# from typing import Any
from common.pattern.cor.handler import Handler
from typing import Any, Dict, List, Optional, Tuple
from domain.handler.newcase_handler import NewCaseHandler
from domain.handler.inprocesscase_handler import InprogressCaseHandler
from domain.handler.finishedcase_handler import FinishedCaseHandler
from domain.handler.default_handler import DefaultHandler
from common.logger import get_logger
from common.exceptions import DataValidationError, WorkflowError
from common.di.factory import get_handler_factory, HandlerFactory
from common.di.container import get_container

logger = get_logger(__name__)


def workflow_setup(handler_factory: Optional[HandlerFactory] = None) -> Handler:
    """
    Set up workflow handler chain using dependency injection.
    
    Args:
        handler_factory: Optional handler factory. If None, uses default factory.
    
    Returns:
        Handler chain starting with FinishedCaseHandler
        
    Raises:
        WorkflowError: If handler setup fails
    """
    try:
        # Use DI container to get handler factory if not provided
        if handler_factory is None:
            # Try to get from DI container first
            container = get_container()
            if container.has('handler_factory'):
                handler_factory = container.get('handler_factory')
            else:
                # Use default factory
                handler_factory = get_handler_factory()
        
        handler = handler_factory.create_handler_chain()
        logger.debug("Workflow handler chain setup successfully")
        return handler
    except Exception as e:
        logger.error("Failed to setup workflow handlers", error=str(e), exc_info=True)
        raise WorkflowError(
            f"Failed to setup workflow handlers: {str(e)}",
            error_code="WORKFLOW_SETUP_ERROR",
            context={'error': str(e)}
        ) from e


def validate_workflow_inputs(
    process_name: str, 
    ls_stages: List[str], 
    data: Dict[str, Any]
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Validate workflow execution inputs.
    
    Args:
        process_name: Process name
        ls_stages: List of workflow stages
        data: Input data dictionary
        
    Returns:
        Tuple of validated (process_name, ls_stages, data)
        
    Raises:
        DataValidationError: If inputs are invalid
    """
    # Validate process_name
    if not process_name:
        logger.error("Process name is empty or None")
        raise DataValidationError(
            "Process name cannot be empty or None",
            error_code="PROCESS_NAME_EMPTY",
            context={'process_name': process_name}
        )
    
    if not isinstance(process_name, str):
        logger.error("Process name must be a string", 
                    process_name_type=type(process_name).__name__)
        raise DataValidationError(
            f"Process name must be a string, got {type(process_name).__name__}",
            error_code="PROCESS_NAME_INVALID_TYPE",
            context={'process_name': process_name, 'process_name_type': type(process_name).__name__}
        )
    
    # Validate ls_stages
    if not isinstance(ls_stages, list):
        logger.error("Workflow stages must be a list", 
                    stages_type=type(ls_stages).__name__)
        raise DataValidationError(
            f"Workflow stages must be a list, got {type(ls_stages).__name__}",
            error_code="STAGES_INVALID_TYPE",
            context={'stages': ls_stages, 'stages_type': type(ls_stages).__name__}
        )
    
    # Validate all stages are strings
    for i, stage in enumerate(ls_stages):
        if not isinstance(stage, str):
            logger.error("Workflow stage must be a string", 
                        stage_index=i, stage=stage, stage_type=type(stage).__name__)
            raise DataValidationError(
                f"Workflow stage at index {i} must be a string, got {type(stage).__name__}",
                error_code="STAGE_INVALID_TYPE",
                context={'stage_index': i, 'stage': stage, 'stage_type': type(stage).__name__}
            )
    
    # Validate data
    if data is None:
        logger.warning("Input data is None, using empty dictionary")
        data = {}
    elif not isinstance(data, dict):
        logger.error("Input data must be a dictionary", data_type=type(data).__name__)
        raise DataValidationError(
            f"Input data must be a dictionary, got {type(data).__name__}",
            error_code="DATA_INVALID_TYPE",
            context={'data': data, 'data_type': type(data).__name__}
        )
    
    logger.debug("Workflow inputs validated successfully", 
                process_name=process_name, stages_count=len(ls_stages),
                data_keys=list(data.keys()) if data else [])
    
    return process_name, ls_stages, data


def wf_exec(
    process_name: str, 
    ls_stages: List[str] = [], 
    data: Dict[str, Any] = {}
) -> Optional[Dict[str, Any]]:
    """
    Execute workflow with given process name, stages, and data.
    
    The wf_exec is usually suited to work with a single handler. In most
    cases, it is not even aware that the handler is part of a chain.
    
    Args:
        process_name: Name of the process/workflow
        ls_stages: List of workflow stage names (defaults to standard stages if empty)
        data: Input data dictionary for workflow processing
        
    Returns:
        Final workflow result dictionary, or None if execution fails
        
    Raises:
        DataValidationError: If input data is invalid
        WorkflowError: If workflow execution fails
    """
    logger.info("Starting workflow execution", process_name=process_name, 
               stages=ls_stages, input_data_keys=list(data.keys()) if isinstance(data, dict) else [])
    
    try:
        # Validate inputs
        validated_process_name, validated_stages, validated_data = validate_workflow_inputs(
            process_name, ls_stages, data
        )
        
        # Setup workflow handlers using dependency injection
        try:
            handler = workflow_setup()
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Failed to setup workflow", error=str(e), exc_info=True)
            raise WorkflowError(
                f"Failed to setup workflow: {str(e)}",
                error_code="WORKFLOW_SETUP_ERROR",
                context={'error': str(e)}
            ) from e
        
        # Use default stages if none provided
        if len(validated_stages) == 0:
            validated_stages = ["INITIATED", "NEW", "INPROGESS", "FINISHED"]
            logger.debug("Using default workflow stages", stages=validated_stages)
        
        # Execute workflow stages
        result = None
        current_data = validated_data
        
        for step in validated_stages:
            logger.info("Processing workflow step", 
                       process_name=validated_process_name, step=step)
            
            try:
                # Validate handler exists
                if handler is None:
                    logger.error("Workflow handler is None", step=step)
                    raise WorkflowError(
                        f"Workflow handler is None at step {step}",
                        error_code="HANDLER_NONE",
                        context={'step': step}
                    )
                
                # Execute step
                result = handler.handle(validated_process_name, step, current_data)
                
                # Validate result structure
                if not isinstance(result, dict):
                    logger.error("Workflow step returned invalid result", 
                               step=step, result_type=type(result).__name__)
                    raise WorkflowError(
                        f"Workflow step {step} returned invalid result type: {type(result).__name__}",
                        error_code="STEP_RESULT_INVALID",
                        context={'step': step, 'result': result}
                    )
                
                # Update data from result
                if 'data' in result:
                    current_data = result['data']
                    if not isinstance(current_data, dict):
                        logger.warning("Workflow step result data is not a dictionary", 
                                     step=step, data_type=type(current_data).__name__)
                        current_data = {}
                else:
                    logger.warning("Workflow step result missing 'data' field", step=step)
                    current_data = {}
                
                logger.debug("Workflow step completed", 
                           process_name=validated_process_name, step=step, 
                           result_keys=list(result.keys()) if isinstance(result, dict) else [])
                
            except WorkflowError:
                raise
            except Exception as e:
                logger.error("Error processing workflow step", 
                           process_name=validated_process_name, step=step,
                           error=str(e), exc_info=True)
                raise WorkflowError(
                    f"Error processing workflow step {step}: {str(e)}",
                    error_code="STEP_EXECUTION_ERROR",
                    context={'process_name': validated_process_name, 'step': step, 'error': str(e)}
                ) from e
        
        logger.info("Workflow execution completed", 
                   process_name=validated_process_name,
                   final_data_keys=list(current_data.keys()) if isinstance(current_data, dict) else [])
        
        return result
        
    except (DataValidationError, WorkflowError):
        # Re-raise validation and workflow errors
        raise
    except Exception as e:
        logger.error("Unexpected error in workflow execution", 
                   process_name=process_name, error=str(e), exc_info=True)
        raise WorkflowError(
            f"Unexpected error in workflow execution: {str(e)}",
            error_code="WORKFLOW_EXEC_ERROR",
            context={'process_name': process_name, 'error': str(e)}
        ) from e
