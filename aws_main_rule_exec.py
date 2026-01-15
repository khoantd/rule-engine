from common.rule_engine_util import *
from services.ruleengine_exec import rules_exec, rules_exec_batch
from common.logger import get_logger
from common.exceptions import DataValidationError, RuleEvaluationError
from common.rule_validator import validate_rules_set, get_rule_validator
import uuid
from typing import Any, Dict, Optional

logger = get_logger(__name__)


def validate_lambda_event(event: Any) -> Dict[str, Any]:
    """
    Validate Lambda event structure.
    
    Args:
        event: Lambda event object
        
    Returns:
        Validated event as dictionary
        
    Raises:
        DataValidationError: If event is invalid
    """
    if event is None:
        logger.error("Lambda event is None")
        raise DataValidationError(
            "Lambda event cannot be None",
            error_code="EVENT_NONE",
            context={'event': event}
        )
    
    # Convert to dict if not already
    if not isinstance(event, dict):
        logger.error("Lambda event must be a dictionary", event_type=type(event).__name__)
        raise DataValidationError(
            f"Lambda event must be a dictionary, got {type(event).__name__}",
            error_code="EVENT_INVALID_TYPE",
            context={'event_type': type(event).__name__, 'event': event}
        )
    
    # Validate event is not empty
    if len(event) == 0:
        logger.warning("Lambda event is empty, execution will proceed with empty data")
        # Allow empty events but warn
    
    logger.debug("Lambda event validated successfully", 
                event_keys=list(event.keys()), event_length=len(event))
    return event


def lambda_handler(event: Any, context: Any = None) -> Dict[str, Any]:
    """
    AWS Lambda handler for rule engine execution.
    
    Supports multiple operation modes:
    - Single execution: event contains input data
    - Batch execution: event contains 'batch' key with list of data items
    - Dry-run mode: event contains 'dry_run' key set to true
    - Validation: event contains 'action' key set to 'validate'
    
    Args:
        event: Lambda event containing:
            - Input data for execution (default)
            - OR 'batch': List of input data dictionaries
            - OR 'dry_run': Boolean flag for dry-run mode
            - OR 'action': 'validate' for validation mode
        context: Lambda context object
        
    Returns:
        Dictionary containing rule execution results, batch results, or validation results
        
    Raises:
        DataValidationError: If event is invalid
        RuleEvaluationError: If rule evaluation fails
    """
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())
    if context:
        request_id = getattr(context, 'aws_request_id', correlation_id)
        correlation_id = request_id
    
    logger.info("Lambda handler invoked", correlation_id=correlation_id, 
               event_keys=list(event.keys()) if isinstance(event, dict) else [],
               context_available=context is not None)
    
    try:
        # Validate event
        validated_event = validate_lambda_event(event)
        
        # Check for validation mode
        if validated_event.get('action') == 'validate':
            from common.rule_engine_util import rules_set_cfg_read
            rules_set = rules_set_cfg_read()
            validation_result = validate_rules_set(rules_set)
            logger.info("Rules validation completed", 
                       correlation_id=correlation_id,
                       is_valid=validation_result['is_valid'],
                       total_errors=validation_result['summary']['total_errors'])
            return {
                'action': 'validate',
                'correlation_id': correlation_id,
                'validation_result': validation_result
            }
        
        # Check for batch execution
        if 'batch' in validated_event:
            batch_data = validated_event['batch']
            if not isinstance(batch_data, list):
                raise DataValidationError(
                    "Batch data must be a list",
                    error_code="BATCH_INVALID_TYPE",
                    context={'batch_type': type(batch_data).__name__}
                )
            
            dry_run = validated_event.get('dry_run', False)
            max_workers = validated_event.get('max_workers')
            
            result = rules_exec_batch(
                data_list=batch_data,
                dry_run=dry_run,
                max_workers=max_workers,
                correlation_id=correlation_id
            )
            
            logger.info("Batch rules execution completed", 
                       correlation_id=correlation_id,
                       batch_id=result.get('batch_id'),
                       total_executions=result.get('summary', {}).get('total_executions'))
            return result
        
        # Single execution (default mode)
        dry_run = validated_event.get('dry_run', False)
        
        # Remove control keys from input data
        input_data = {
            k: v for k, v in validated_event.items()
            if k not in ['dry_run', 'batch', 'action', 'max_workers']
        }
        
        # Execute rules
        result = rules_exec(
            data=input_data,
            dry_run=dry_run,
            correlation_id=correlation_id
        )
        
        # Validate result structure
        if not isinstance(result, dict):
            logger.error("Rules execution returned invalid result type", 
                        result_type=type(result).__name__)
            raise RuleEvaluationError(
                f"Rules execution returned invalid result type: {type(result).__name__}",
                error_code="INVALID_RESULT_TYPE",
                context={'result_type': type(result).__name__}
            )
        
        # Validate required fields in result (unless dry_run)
        if not dry_run:
            required_fields = ['total_points', 'pattern_result', 'action_recommendation']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                logger.error("Rules execution result missing required fields", 
                            missing_fields=missing_fields)
                raise RuleEvaluationError(
                    f"Rules execution result missing required fields: {', '.join(missing_fields)}",
                    error_code="RESULT_MISSING_FIELDS",
                    context={'missing_fields': missing_fields, 'result': result}
                )
        
        logger.info("Rules execution completed successfully", correlation_id=correlation_id, 
                   total_points=result.get('total_points'), 
                   pattern_result=result.get('pattern_result'),
                   action_recommendation=result.get('action_recommendation'),
                   dry_run=dry_run)
        return result
        
    except (DataValidationError, RuleEvaluationError):
        # Re-raise validation and evaluation errors
        raise
    except Exception as e:
        logger.error("Lambda handler failed", correlation_id=correlation_id, 
                    error=str(e), exc_info=True)
        raise RuleEvaluationError(
            f"Lambda handler failed: {str(e)}",
            error_code="LAMBDA_HANDLER_ERROR",
            context={'correlation_id': correlation_id, 'error': str(e)}
        ) from e


if __name__ == "__main__":
    logger.info("Executing aws_main_rule_exec as main")
    data = {
        'age_till_now': 150,
        'status':'new',
        'days_since_starting_uat': 31,
        'days_since_bomc_approval': 3
    }
    logger.info("Executing rules with test data", input_data=data)
    result = rules_exec(data)
    logger.info("Rules execution result", result=result)
