from common.json_util import read_json_file, parse_json_v2
from common.rule_engine_util import (
    rules_set_cfg_read,
    rules_set_setup,
    actions_set_cfg_read,
    find_action_recommendation,
    sort_by_priority,
    rule_run,
    condition_setup,
    _evaluate_feel_expression
)
from common.dmn_parser import DMNParser
from common.logger import get_logger
from common.exceptions import DataValidationError, RuleEvaluationError, ConfigurationError
from common.execution_history import get_execution_history
from common.metrics import get_metrics
from services.usage_tracking import get_usage_tracking_service
from typing import Any, Dict, Optional, List
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = get_logger(__name__)


def validate_input_data(data: Any) -> Dict[str, Any]:
    """
    Validate input data for rules execution.
    
    Args:
        data: Input data dictionary
        
    Returns:
        Validated data dictionary
        
    Raises:
        DataValidationError: If data is invalid
    """
    if data is None:
        logger.error("Input data is None")
        raise DataValidationError(
            "Input data cannot be None",
            error_code="DATA_NONE",
            context={'data': data}
        )
    
    if not isinstance(data, dict):
        logger.error("Input data must be a dictionary", data_type=type(data).__name__)
        raise DataValidationError(
            f"Input data must be a dictionary, got {type(data).__name__}",
            error_code="DATA_INVALID_TYPE",
            context={'data_type': type(data).__name__, 'data': data}
        )
    
    # Allow empty dictionaries (some rules might not need input)
    logger.debug("Input data validated successfully", 
                data_keys=list(data.keys()), data_length=len(data))
    return data


def rules_exec(
    data: Any,
    dry_run: bool = False,
    correlation_id: Optional[str] = None,
    consumer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute rules against input data.
    
    Args:
        data: Dictionary containing input data for rule evaluation
        dry_run: If True, execute rules without side effects (preview mode)
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Dictionary containing:
            - total_points: Sum of rule points (weighted)
            - pattern_result: Concatenated action results
            - action_recommendation: Recommended action based on pattern
            - rule_evaluations: (if dry_run=True) List of per-rule evaluation results
            - would_match: (if dry_run=True) List of rules that would match
            - would_not_match: (if dry_run=True) List of rules that would not match
            
    Raises:
        DataValidationError: If input data is invalid
        ConfigurationError: If configuration cannot be loaded
        RuleEvaluationError: If rule evaluation fails
    """
    start_time = time.time()
    execution_id = str(uuid.uuid4())
    correlation_id = correlation_id or str(uuid.uuid4())
    
    metrics = get_metrics()
    history = get_execution_history()
    
    logger.info("Starting rules execution", 
               execution_id=execution_id,
               correlation_id=correlation_id,
               dry_run=dry_run,
               input_data_keys=list(data.keys()) if isinstance(data, dict) else [])
    
    error = None
    error_code = None
    
    try:
        # Track execution with metrics
        with metrics.timer('rule_execution', dimensions={'dry_run': str(dry_run)}):
            # Validate input data
            validated_data = validate_input_data(data)
            
            # Initialize result tracking
            results = []
            rule_evaluations: List[Dict[str, Any]] = []
            executed_rules_count = 0
            matched_rules_count = 0
            matched_rule_ids: List[str] = []
            total_points = 0.0
            
            # Load rules configuration
            logger.debug("Loading rules configuration")
            try:
                rules_list = rules_set_setup(rules_set_cfg_read())
            except ConfigurationError:
                raise
            except Exception as e:
                logger.error("Failed to load rules configuration", error=str(e), exc_info=True)
                raise ConfigurationError(
                    f"Failed to load rules configuration: {str(e)}",
                    error_code="RULES_LOAD_ERROR",
                    context={'error': str(e)}
                ) from e
            
            if not rules_list or len(rules_list) == 0:
                logger.warning("No rules found in configuration")
                result = {
                    "total_points": 0.0,
                    "pattern_result": "",
                    "action_recommendation": None
                }
                if dry_run:
                    result.update({
                        "rule_evaluations": [],
                        "would_match": [],
                        "would_not_match": []
                    })
                return result
            
            logger.info("Loaded rules configuration", rules_count=len(rules_list))
            metrics.increment('rules_loaded', value=len(rules_list))
            
            # Execute each rule
            for rule in rules_list:
                try:
                    rule_id = rule.get('rule_name', 'unknown')
                    logger.debug("Processing rule", rule_id=rule_id, 
                               rule_priority=rule.get('priority'))
                    
                    # Validate rule structure
                    if not isinstance(rule, dict):
                        logger.error("Invalid rule structure", rule_type=type(rule).__name__)
                        raise RuleEvaluationError(
                            f"Invalid rule structure: expected dict, got {type(rule).__name__}",
                            error_code="RULE_INVALID_STRUCTURE",
                            context={'rule': rule}
                        )
                    
                    # Track per-rule metrics
                    rule_start_time = time.time()
                    
                    result = rule_run(rule, validated_data)
                    executed_rules_count += 1
                    
                    rule_execution_time = (time.time() - rule_start_time) * 1000  # ms
                    
                    # Validate result structure
                    if not isinstance(result, dict):
                        logger.error("Rule run returned invalid result", 
                                   rule_id=rule_id, result_type=type(result).__name__)
                        raise RuleEvaluationError(
                            f"Rule {rule_id} returned invalid result type: {type(result).__name__}",
                            error_code="RULE_RESULT_INVALID",
                            context={'rule_id': rule_id, 'result': result}
                        )
                    
                    # Extract and validate points and weight
                    rule_matched = result.get("action_result", "-") != "-"
                    if rule_matched:
                        matched_rules_count += 1
                        matched_rule_ids.append(rule_id)
                        metrics.increment('rules_matched', dimensions={'rule_name': rule_id})
                    else:
                        metrics.increment('rules_not_matched', dimensions={'rule_name': rule_id})
                    
                    # Track per-rule execution time
                    metrics.put_metric(
                        'rule_evaluation_time',
                        rule_execution_time,
                        'Milliseconds',
                        dimensions={'rule_name': rule_id}
                    )
                    
                    # Track enhanced analytics
                    metrics.track_rule_execution(
                        rule_name=rule_id,
                        matched=rule_matched,
                        execution_time_ms=rule_execution_time
                    )
                    
                    try:
                        # Explicit type conversion with validation
                        rule_point_value = result.get("rule_point", 0)
                        weight_value = result.get("weight", 0)
                        
                        # Validate types before conversion
                        if not isinstance(rule_point_value, (int, float, str)):
                            raise TypeError(f"Invalid rule_point type: {type(rule_point_value).__name__}")
                        if not isinstance(weight_value, (int, float, str)):
                            raise TypeError(f"Invalid weight type: {type(weight_value).__name__}")
                        
                        rule_point = float(rule_point_value)
                        weight = float(weight_value)
                        total_points += (rule_point * weight)
                    except (ValueError, TypeError) as conversion_error:
                        logger.warning("Invalid rule_point or weight", 
                                    rule_id=rule_id, rule_point=result.get("rule_point"),
                                    weight=result.get("weight"), error=str(conversion_error))
                        # Continue with 0 points if conversion fails
                        total_points += 0.0
                    
                    action_result = result.get("action_result", "-")
                    results.append(action_result)
                    
                    # Track detailed rule evaluation for dry-run mode
                    if dry_run:
                        rule_evaluation = {
                            'rule_name': rule_id,
                            'rule_priority': rule.get('priority'),
                            'condition': rule.get('condition', ''),
                            'matched': rule_matched,
                            'action_result': action_result,
                            'rule_point': result.get("rule_point", 0.0),
                            'weight': result.get("weight", 0.0),
                            'execution_time_ms': rule_execution_time
                        }
                        rule_evaluations.append(rule_evaluation)
                    
                    logger.debug("Rule processed", rule_id=rule_id, 
                               action_result=action_result, 
                               points=result.get("rule_point"), 
                               weight=result.get("weight"),
                               matched=rule_matched)
                    
                except RuleEvaluationError:
                    # Re-raise rule evaluation errors
                    raise
                except Exception as rule_error:
                    logger.error("Error processing rule", rule_id=rule.get('rule_name', 'unknown'),
                               error=str(rule_error), exc_info=True)
                    # Continue with next rule instead of failing completely
                    continue
            
            # Build pattern result (optimized string concatenation)
            tmp_str = "".join(results) if results else ""
            logger.debug("Processing action pattern", pattern_result=tmp_str)
            
            # Get action recommendation (skip in dry-run if needed, but include for preview)
            try:
                actions_set = actions_set_cfg_read()
                tmp_action = find_action_recommendation(actions_set, tmp_str)
            except ConfigurationError:
                logger.warning("Failed to load actions configuration, continuing without action recommendation")
                tmp_action = None
            except Exception as action_error:
                logger.warning("Error getting action recommendation", error=str(action_error))
                tmp_action = None
            
            # Build result
            result = {
                "total_points": total_points,
                "pattern_result": tmp_str,
                "action_recommendation": tmp_action
            }
            
            # Add dry-run specific fields
            if dry_run:
                would_match = [e for e in rule_evaluations if e['matched']]
                would_not_match = [e for e in rule_evaluations if not e['matched']]
                result.update({
                    "rule_evaluations": rule_evaluations,
                    "would_match": would_match,
                    "would_not_match": would_not_match,
                    "dry_run": True
                })
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Track metrics
            metrics.increment('executions_total', dimensions={'dry_run': str(dry_run)})
            metrics.put_metric('execution_time', execution_time_ms, 'Milliseconds')
            metrics.put_metric('total_points', total_points, 'Count')
            metrics.increment('rules_evaluated', value=executed_rules_count)
            
            # Track enhanced analytics
            metrics.track_action(tmp_action)
            metrics.track_pattern(tmp_str)
            metrics.track_points(total_points)
            
            logger.info("Rules execution completed", 
                       execution_id=execution_id,
                       correlation_id=correlation_id,
                       total_points=total_points, 
                       pattern_result=tmp_str, 
                       action_recommendation=tmp_action, 
                       executed_rules=executed_rules_count,
                       matched_rules=matched_rules_count,
                       execution_time_ms=execution_time_ms,
                       dry_run=dry_run)
            
            # Log to execution history
            history.log_execution(
                input_data=validated_data,
                output_data=result,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                rules_evaluated=executed_rules_count,
                rules_matched=matched_rules_count,
                rule_evaluations=rule_evaluations if dry_run else None
            )

            # Track consumer usage if consumer_id is provided
            if consumer_id and matched_rule_ids:
                try:
                    tracking_service = get_usage_tracking_service()
                    tracking_service.track_usage(
                        consumer_id=consumer_id,
                        rule_ids=matched_rule_ids,
                        ruleset_id=None 
                    )
                except Exception as e:
                    logger.warning("Failed to track consumer usage", error=str(e), consumer_id=consumer_id)
            
            return result
            
    except (DataValidationError, ConfigurationError, RuleEvaluationError) as e:
        error = str(e)
        error_code = getattr(e, 'error_code', None)
        # Re-raise specific errors
        raise
    except Exception as execution_error:
        error = str(execution_error)
        error_code = "RULES_EXEC_ERROR"
        logger.error("Unexpected error in rules execution", error=error, exc_info=True)
        raise RuleEvaluationError(
            f"Unexpected error in rules execution: {error}",
            error_code=error_code,
            context={'error': error}
        ) from execution_error
    finally:
        # Log failed execution to history
        if error:
            execution_time_ms = (time.time() - start_time) * 1000
            history.log_execution(
                input_data=data if isinstance(data, dict) else {},
                output_data={},
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                rules_evaluated=0,
                rules_matched=0,
                error=error,
                error_code=error_code
            )


def rules_exec_batch(
    data_list: List[Dict[str, Any]],
    dry_run: bool = False,
    max_workers: Optional[int] = None,
    correlation_id: Optional[str] = None,
    consumer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute rules against multiple data items efficiently.
    
    Args:
        data_list: List of input data dictionaries
        dry_run: If True, execute rules without side effects
        max_workers: Maximum number of parallel workers (None = auto)
        correlation_id: Optional correlation ID for batch tracking
        
    Returns:
        Dictionary containing:
            - results: List of execution results
            - summary: Summary statistics
            - total_executions: Total number of executions
            - successful_executions: Number of successful executions
            - failed_executions: Number of failed executions
            - total_execution_time_ms: Total execution time in milliseconds
            - avg_execution_time_ms: Average execution time per item
    """
    batch_start_time = time.time()
    batch_id = correlation_id or str(uuid.uuid4())
    
    metrics = get_metrics()
    history = get_execution_history()
    
    logger.info("Starting batch rules execution",
               batch_id=batch_id,
               batch_size=len(data_list),
               dry_run=dry_run,
               max_workers=max_workers)
    
    results = []
    successful = 0
    failed = 0
    
    def execute_single(data_item: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Execute rules for a single data item."""
        item_correlation_id = f"{batch_id}-{index}"
        try:
            result = rules_exec(
                data=data_item,
                dry_run=dry_run,
                correlation_id=item_correlation_id,
                consumer_id=consumer_id
            )
            result['item_index'] = index
            result['correlation_id'] = item_correlation_id
            result['status'] = 'success'
            return result
        except Exception as e:
            logger.error("Failed to execute rules for item", 
                        item_index=index,
                        correlation_id=item_correlation_id,
                        error=str(e))
            return {
                'item_index': index,
                'correlation_id': item_correlation_id,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    # Execute in parallel if max_workers is specified
    if max_workers is not None and max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(execute_single, data_item, i): i
                for i, data_item in enumerate(data_list)
            }
            
            for future in as_completed(futures):
                index = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.get('status') == 'success':
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error("Error getting result for item", 
                                item_index=index, error=str(e))
                    results.append({
                        'item_index': index,
                        'status': 'failed',
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    failed += 1
    else:
        # Execute sequentially
        for i, data_item in enumerate(data_list):
            result = execute_single(data_item, i)
            results.append(result)
            if result.get('status') == 'success':
                successful += 1
            else:
                failed += 1
    
    # Sort results by index
    results.sort(key=lambda r: r.get('item_index', 0))
    
    total_execution_time_ms = (time.time() - batch_start_time) * 1000
    avg_execution_time_ms = total_execution_time_ms / len(data_list) if data_list else 0.0
    
    # Track batch metrics
    metrics.increment('batch_executions_total', dimensions={'dry_run': str(dry_run)})
    metrics.put_metric('batch_size', len(data_list), 'Count')
    metrics.put_metric('batch_execution_time', total_execution_time_ms, 'Milliseconds')
    metrics.increment('batch_successful', value=successful)
    metrics.increment('batch_failed', value=failed)
    
    summary = {
        'total_executions': len(data_list),
        'successful_executions': successful,
        'failed_executions': failed,
        'total_execution_time_ms': total_execution_time_ms,
        'avg_execution_time_ms': avg_execution_time_ms,
        'success_rate': (successful / len(data_list) * 100) if data_list else 0.0
    }
    
    logger.info("Batch rules execution completed",
               batch_id=batch_id,
               total_executions=len(data_list),
               successful=successful,
               failed=failed,
               total_execution_time_ms=total_execution_time_ms)
    
    return {
        'batch_id': batch_id,
        'results': results,
        'summary': summary,
        'dry_run': dry_run
    }


def _group_rules_by_decision(
    rules_set: List[Dict[str, Any]], 
    decisions_metadata: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group rules by their decision ID.
    
    Args:
        rules_set: Flat list of all rules
        decisions_metadata: List of decision metadata
        
    Returns:
        Dictionary: {decision_id: [rules_for_decision]}
    """
    grouped = {}
    
    for rule in rules_set:
        decision_id = rule.get('decision_id', '')
        if decision_id:
            if decision_id not in grouped:
                grouped[decision_id] = []
            grouped[decision_id].append(rule)
    
    # Ensure all decisions have entries (even if empty)
    for metadata in decisions_metadata:
        decision_id = metadata.get('decision_id', '')
        if decision_id and decision_id not in grouped:
            grouped[decision_id] = []
    
    logger.debug("Grouped rules by decision", 
                decision_counts={k: len(v) for k, v in grouped.items()})
    
    return grouped


def _execute_decision_rules(
    decision_id: str,
    rules: List[Dict[str, Any]],
    data: Dict[str, Any],
    dry_run: bool,
    decision_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute all rules for a single decision and collect outputs.
    
    Args:
        decision_id: Decision identifier
        rules: List of prepared rules for this decision
        data: Current data dictionary
        dry_run: Dry run flag
        decision_metadata: Decision metadata with outputs info
        
    Returns:
        Dictionary with execution results including matched outputs
    """
    matched_outputs = []
    matched_outputs_dict = []  # List of dictionaries with all outputs per matched rule
    action_results = []
    rule_evaluations = []
    executed_count = 0
    matched_count = 0
    matched_rule_ids: List[str] = []
    total_points = 0.0
    
    hit_policy = 'UNIQUE'  # Default hit policy
    
    for rule in rules:
        try:
            rule_id = rule.get('rule_name', 'unknown')
            rule_start_time = time.time()
            
            result = rule_run(rule, data)
            executed_count += 1
            
            rule_execution_time = (time.time() - rule_start_time) * 1000
            
            rule_matched = result.get("action_result", "-") != "-"
            if rule_matched:
                logger.info("Rule matched in decision", 
                          decision_id=decision_id,
                          decision_name=decision_metadata.get('decision_name'),
                          rule_id=rule_id,
                          action_result=result.get("action_result", "-"))
            else:
                logger.debug("Rule did not match in decision", 
                           decision_id=decision_id,
                           decision_name=decision_metadata.get('decision_name'),
                           rule_id=rule_id,
                           condition=rule.get('condition', ''),
                           available_data_keys=list(data.keys()))
            if rule_matched:
                matched_count += 1
                action_result = result.get("action_result", "-")
                action_results.append(action_result)
                matched_outputs.append(action_result)
                matched_rule_ids.append(rule_id)
                
                # Collect all outputs from the rule if available
                rule_outputs = rule.get("outputs", {})
                if rule_outputs:
                    # Evaluate FEEL expressions in outputs
                    evaluated_outputs = {}
                    for output_label, output_value in rule_outputs.items():
                        if isinstance(output_value, str):
                            evaluated_outputs[output_label] = _evaluate_feel_expression(output_value, data)
                        else:
                            evaluated_outputs[output_label] = output_value
                    # Use outputs from rule definition (multiple outputs)
                    matched_outputs_dict.append(evaluated_outputs)
                    logger.debug("Collected multiple outputs from rule", 
                               decision_id=decision_id,
                               rule_id=rule_id,
                               outputs=rule_outputs)
                else:
                    # Fallback to single output (backward compatibility)
                    # Get output label from decision metadata
                    outputs_def = decision_metadata.get('outputs', [])
                    if outputs_def:
                        output_label = outputs_def[0].get('label', '') or outputs_def[0].get('name', '') or 'result'
                    else:
                        output_label = 'result'
                    matched_outputs_dict.append({output_label: action_result})
                
                # Calculate points
                rule_point = float(result.get("rule_point", 0))
                weight = float(result.get("weight", 1.0))
                total_points += (rule_point * weight)
            
            # Track detailed rule evaluation for dry-run mode (before potential break)
            if dry_run:
                rule_evaluation = {
                    'rule_name': rule_id,
                    'rule_priority': rule.get('priority'),
                    'condition': rule.get('condition', ''),
                    'matched': rule_matched,
                    'action_result': result.get("action_result", "-"),
                    'rule_point': result.get("rule_point", 0.0),
                    'weight': result.get("weight", 0.0),
                    'execution_time_ms': rule_execution_time
                }
                rule_evaluations.append(rule_evaluation)
            
            # Handle hit policy: UNIQUE/FIRST - return first match (after evaluation tracking)
            if rule_matched and hit_policy in ('UNIQUE', 'FIRST') and len(matched_outputs) == 1:
                break
                
        except Exception as rule_error:
            logger.warning("Error executing rule in decision", 
                         decision_id=decision_id,
                         rule_id=rule.get('rule_name', 'unknown'),
                         error=str(rule_error))
            continue
    
    return {
        'matched_outputs': matched_outputs,  # Backward compatibility: list of primary output values
        'matched_outputs_dict': matched_outputs_dict,  # New: list of dictionaries with all outputs
        'action_results': action_results,
        'executed_count': executed_count,
        'matched_count': matched_count,
        'matched_rule_ids': matched_rule_ids,
        'total_points': total_points,
        'rule_evaluations': rule_evaluations
    }


def _map_decision_outputs(
    decision_metadata: Dict[str, Any],
    execution_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Map decision outputs to input field names.
    
    Supports multiple outputs from a single rule match.
    
    Args:
        decision_metadata: Decision metadata with output mappings
        execution_result: Execution result from _execute_decision_rules()
        
    Returns:
        Dictionary mapping field names to output values: {field_name: output_value}
        For multiple outputs, returns multiple mappings: {field_name1: value1, field_name2: value2, ...}
    """
    matched_outputs_dict = execution_result.get('matched_outputs_dict', [])
    matched_outputs = execution_result.get('matched_outputs', [])
    
    if not matched_outputs_dict and not matched_outputs:
        logger.debug("No matched outputs to map", 
                    decision_id=decision_metadata.get('decision_id'),
                    decision_name=decision_metadata.get('decision_name'))
        return {}
    
    output_field_mapping = decision_metadata.get('output_field_mapping', {})
    outputs = decision_metadata.get('outputs', [])
    
    if not outputs:
        logger.warning("No outputs defined for decision", 
                      decision_id=decision_metadata.get('decision_id'),
                      decision_name=decision_metadata.get('decision_name'))
        return {}
    
    # Use matched_outputs_dict if available (supports multiple outputs)
    if matched_outputs_dict:
        # Get the first matched rule's outputs (for UNIQUE/FIRST hit policy)
        matched_outputs_from_rule = matched_outputs_dict[0]
        mapped = {}
        
        # Map each output to its field name
        for output_def in outputs:
            output_label = output_def.get('label', '') or output_def.get('name', '')
            if output_label and output_label in matched_outputs_from_rule:
                # Get field name from mapping or use label as fallback
                field_name = output_field_mapping.get(output_label, output_label)
                output_value = matched_outputs_from_rule[output_label]
                mapped[field_name] = output_value
                
                logger.debug("Mapped output", 
                           decision_id=decision_metadata.get('decision_id'),
                           decision_name=decision_metadata.get('decision_name'),
                           output_label=output_label,
                           field_name=field_name,
                           output_value=output_value)
        
        if mapped:
            logger.info("Mapped decision outputs", 
                       decision_id=decision_metadata.get('decision_id'),
                       decision_name=decision_metadata.get('decision_name'),
                       mapped_outputs=mapped,
                       output_field_mapping=output_field_mapping)
            return mapped
    
    # Fallback to single output (backward compatibility)
    if matched_outputs:
        first_output = outputs[0]
        output_label = first_output.get('label', '') or first_output.get('name', '')
        
        if not output_label:
            logger.warning("No output label found", 
                          decision_id=decision_metadata.get('decision_id'),
                          decision_name=decision_metadata.get('decision_name'),
                          output=first_output)
            return {}
        
        # Map output to field name
        field_name = output_field_mapping.get(output_label, output_label)
        output_value = matched_outputs[0] if matched_outputs else None
        
        if output_value is None:
            logger.warning("No output value to map", 
                          decision_id=decision_metadata.get('decision_id'),
                          decision_name=decision_metadata.get('decision_name'),
                          matched_outputs=matched_outputs)
            return {}
        
        mapped = {field_name: output_value}
        
        logger.info("Mapped decision outputs", 
                   decision_id=decision_metadata.get('decision_id'),
                   decision_name=decision_metadata.get('decision_name'),
                   output_label=output_label,
                   field_name=field_name,
                   output_value=output_value,
                   output_field_mapping=output_field_mapping)
        
        return mapped
    
    return {}


def dmn_rules_exec(
    dmn_file: Optional[str] = None,
    dmn_content: Optional[str] = None,
    data: Any = None,
    dry_run: bool = False,
    correlation_id: Optional[str] = None,
    consumer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute rules from a DMN file against input data.
    
    This function parses a DMN file (from file path or XML content), converts
    the DMN rules to execution format, and executes them against the provided
    input data. It returns results in the same format as rules_exec().
    
    Args:
        dmn_file: Path to DMN file (relative to data/input or absolute path)
        dmn_content: DMN XML content as string
        data: Dictionary containing input data for rule evaluation
        dry_run: If True, execute rules without side effects (preview mode)
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Dictionary containing:
            - total_points: Sum of rule points (weighted)
            - pattern_result: Concatenated action results
            - action_recommendation: Recommended action based on pattern (optional)
            - rule_evaluations: (if dry_run=True) List of per-rule evaluation results
            - would_match: (if dry_run=True) List of rules that would match
            - would_not_match: (if dry_run=True) List of rules that would not match
            
    Raises:
        DataValidationError: If input data is invalid or DMN source not provided
        ConfigurationError: If DMN file cannot be read or parsed
        RuleEvaluationError: If rule evaluation fails
    """
    start_time = time.time()
    execution_id = str(uuid.uuid4())
    correlation_id = correlation_id or str(uuid.uuid4())
    
    metrics = get_metrics()
    history = get_execution_history()
    
    logger.info("Starting DMN rules execution", 
               execution_id=execution_id,
               correlation_id=correlation_id,
               dry_run=dry_run,
               has_dmn_file=dmn_file is not None,
               has_dmn_content=dmn_content is not None,
               input_data_keys=list(data.keys()) if isinstance(data, dict) else [])
    
    error = None
    error_code = None
    
    try:
        # Validate DMN source
        if not dmn_file and not dmn_content:
            logger.error("No DMN source provided")
            raise DataValidationError(
                "Exactly one of dmn_file or dmn_content must be provided",
                error_code="MISSING_DMN_SOURCE",
                context={'dmn_file': dmn_file, 'dmn_content': dmn_content is not None}
            )
        
        if dmn_file and dmn_content:
            logger.error("Multiple DMN sources provided")
            raise DataValidationError(
                "Only one of dmn_file or dmn_content can be provided",
                error_code="MULTIPLE_DMN_SOURCES",
                context={'dmn_file': dmn_file, 'has_dmn_content': True}
            )
        
        # Track execution with metrics
        with metrics.timer('dmn_rule_execution', dimensions={'dry_run': str(dry_run)}):
            # Validate input data
            validated_data = validate_input_data(data)
            
            # Parse DMN file or content
            logger.debug("Parsing DMN", has_file=bool(dmn_file), has_content=bool(dmn_content))
            parser = DMNParser()
            
            try:
                if dmn_file:
                    # Validate file path to prevent directory traversal
                    file_path = Path(dmn_file)
                    if not file_path.is_absolute():
                        # Normalize the path - strip data/input/ prefix if present
                        normalized_dmn_file = dmn_file
                        if normalized_dmn_file.startswith("data/input/"):
                            normalized_dmn_file = normalized_dmn_file[len("data/input/"):]
                        elif normalized_dmn_file.startswith("data\\input\\"):
                            normalized_dmn_file = normalized_dmn_file[len("data\\input\\"):]
                        
                        # Try relative to data/input directory
                        data_input_dir = Path(__file__).parent.parent / "data" / "input"
                        file_path = data_input_dir / normalized_dmn_file
                    
                    if not file_path.exists():
                        logger.error("DMN file not found", file_path=str(file_path))
                        raise ConfigurationError(
                            f"DMN file not found: {dmn_file}",
                            error_code="DMN_FILE_NOT_FOUND",
                            context={'file_path': str(file_path), 'dmn_file': dmn_file}
                        )
                    
                    parse_result = parser.parse_file(str(file_path))
                else:
                    parse_result = parser.parse_content(dmn_content)
                
            except ConfigurationError:
                raise
            except Exception as parse_error:
                logger.error("Failed to parse DMN", error=str(parse_error), exc_info=True)
                raise ConfigurationError(
                    f"Failed to parse DMN: {str(parse_error)}",
                    error_code="DMN_PARSE_ERROR",
                    context={'error': str(parse_error), 'has_file': bool(dmn_file)}
                ) from parse_error
            
            rules_set = parse_result.get('rules_set', [])
            decisions_metadata = parse_result.get('decisions_metadata', [])
            execution_order = parse_result.get('execution_order', [])
            
            if not rules_set or len(rules_set) == 0:
                logger.warning("No rules found in DMN file")
                result = {
                    "total_points": 0.0,
                    "pattern_result": "",
                    "action_recommendation": None
                }
                if dry_run:
                    result.update({
                        "rule_evaluations": [],
                        "would_match": [],
                        "would_not_match": []
                    })
                return result
            
            logger.info("DMN parsed successfully", 
                       rules_count=len(rules_set),
                       decisions_count=len(decisions_metadata),
                       execution_order=execution_order)
            metrics.increment('dmn_rules_loaded', value=len(rules_set))
            
            # Initialize decision outputs collection for final result
            decision_outputs = {}
            
            # Group rules by decision_id
            rules_by_decision = _group_rules_by_decision(rules_set, decisions_metadata)
            
            # Execute decisions in dependency order
            # If no execution order provided, execute all rules together (backward compatibility)
            if execution_order and decisions_metadata:
                # Execute decisions in dependency order
                results = []
                rule_evaluations: List[Dict[str, Any]] = []
                executed_rules_count = 0
                matched_rules_count = 0
                total_points = 0.0
                current_data = validated_data.copy()
                
                for decision_id in execution_order:
                    decision_rules = rules_by_decision.get(decision_id, [])
                    if not decision_rules:
                        logger.debug("No rules found for decision", decision_id=decision_id)
                        continue
                    
                    # Get decision metadata
                    decision_metadata = next(
                        (dm for dm in decisions_metadata if dm.get('decision_id') == decision_id),
                        None
                    )
                    
                    if not decision_metadata:
                        logger.warning("Decision metadata not found", decision_id=decision_id)
                        continue
                    
                    logger.info("Executing decision", 
                               decision_id=decision_id,
                               decision_name=decision_metadata.get('decision_name'),
                               rules_count=len(decision_rules),
                               dependencies=decision_metadata.get('dependencies'),
                               current_data_keys=list(current_data.keys()),
                               current_data_values={k: v for k, v in current_data.items() if k in ['element_1', 'element_2', 'can', 'chi']})
                    
                    # Prepare rules for this decision
                    prepared_rules = []
                    for dmn_rule in decision_rules:
                        try:
                            combined_condition = dmn_rule.get('combined_condition')
                            if combined_condition:
                                condition_str = combined_condition
                            else:
                                condition_str = condition_setup({
                                    'attribute': dmn_rule.get('attribute', ''),
                                    'condition': dmn_rule.get('condition', 'equal'),
                                    'constant': dmn_rule.get('constant', '')
                                })
                            
                            prepared_rule = {
                                'rule_name': dmn_rule.get('rule_name', 'Unknown Rule'),
                                'condition': condition_str,
                                'action_result': dmn_rule.get('action_result', '-'),
                                'rule_point': float(dmn_rule.get('rule_point', 10.0)),
                                'weight': float(dmn_rule.get('weight', 1.0)),
                                'priority': int(dmn_rule.get('priority', 1))
                            }
                            # Preserve outputs if available (for multiple outputs support)
                            if 'outputs' in dmn_rule:
                                prepared_rule['outputs'] = dmn_rule['outputs']
                            
                            prepared_rules.append(prepared_rule)
                            logger.debug("Prepared rule for decision", 
                                       decision_id=decision_id,
                                       decision_name=decision_metadata.get('decision_name'),
                                       rule_name=prepared_rule['rule_name'],
                                       condition=condition_str,
                                       action_result=prepared_rule['action_result'],
                                       outputs_count=len(prepared_rule.get('outputs', {})))
                        except Exception as rule_error:
                            logger.warning("Failed to prepare DMN rule", 
                                         rule_id=dmn_rule.get('id', 'unknown'),
                                         error=str(rule_error))
                            continue
                    
                    # Sort rules by priority
                    prepared_rules.sort(key=lambda r: r['priority'])
                    
                    # Execute decision rules
                    decision_result = _execute_decision_rules(
                        decision_id=decision_id,
                        rules=prepared_rules,
                        data=current_data,
                        dry_run=dry_run,
                        decision_metadata=decision_metadata
                    )
                    
                    # Update counters
                    executed_rules_count += decision_result['executed_count']
                    matched_rules_count += decision_result['matched_count']
                    matched_rule_ids.extend(decision_result.get('matched_rule_ids', []))
                    total_points += decision_result['total_points']
                    results.extend(decision_result['action_results'])
                    
                    if dry_run:
                        rule_evaluations.extend(decision_result.get('rule_evaluations', []))
                    
                    # Map outputs and enrich data for dependent decisions
                    # Check for matched outputs (either dict format or list format)
                    has_matched_outputs = (
                        decision_result.get('matched_outputs_dict') or 
                        decision_result.get('matched_outputs')
                    )
                    if has_matched_outputs:
                        mapped_outputs = _map_decision_outputs(
                            decision_metadata=decision_metadata,
                            execution_result=decision_result
                        )
                        if mapped_outputs:
                            current_data.update(mapped_outputs)
                            # Collect outputs for final result
                            decision_outputs.update(mapped_outputs)
                            logger.info("Enriched data with dependent outputs", 
                                       decision_id=decision_id,
                                       decision_name=decision_metadata.get('decision_name'),
                                       mapped_outputs=mapped_outputs,
                                       data_keys=list(current_data.keys()))
                        else:
                            logger.warning("Failed to map decision outputs", 
                                         decision_id=decision_id,
                                         decision_name=decision_metadata.get('decision_name'),
                                         matched_outputs_dict=decision_result.get('matched_outputs_dict'),
                                         matched_outputs=decision_result.get('matched_outputs'),
                                         outputs=decision_metadata.get('outputs', []),
                                         output_field_mapping=decision_metadata.get('output_field_mapping', {}))
                    else:
                        logger.info("No matched outputs to map for decision", 
                                   decision_id=decision_id,
                                   decision_name=decision_metadata.get('decision_name'),
                                   matched_count=decision_result.get('matched_count', 0),
                                   executed_count=decision_result.get('executed_count', 0),
                                   rules_count=len(prepared_rules))
            else:
                # Backward compatibility: execute all rules together
                logger.debug("No execution order provided, executing all rules together")
                
                # Convert DMN rules to execution format
                prepared_rules = []
                matched_rule_ids: List[str] = []
                for dmn_rule in rules_set:
                    try:
                        combined_condition = dmn_rule.get('combined_condition')
                        if combined_condition:
                            condition_str = combined_condition
                        else:
                            condition_str = condition_setup({
                                'attribute': dmn_rule.get('attribute', ''),
                                'condition': dmn_rule.get('condition', 'equal'),
                                'constant': dmn_rule.get('constant', '')
                            })
                        
                        prepared_rule = {
                            'rule_name': dmn_rule.get('rule_name', 'Unknown Rule'),
                            'condition': condition_str,
                            'action_result': dmn_rule.get('action_result', '-'),
                            'rule_point': float(dmn_rule.get('rule_point', 10.0)),
                            'weight': float(dmn_rule.get('weight', 1.0)),
                            'priority': int(dmn_rule.get('priority', 1))
                        }
                        prepared_rules.append(prepared_rule)
                    except Exception as rule_error:
                        logger.warning("Failed to prepare DMN rule", 
                                     rule_id=dmn_rule.get('id', 'unknown'),
                                     error=str(rule_error))
                        continue
                
                if not prepared_rules:
                    logger.warning("No valid rules prepared from DMN")
                    result = {
                        "total_points": 0.0,
                        "pattern_result": "",
                        "action_recommendation": None
                    }
                    if dry_run:
                        result.update({
                            "rule_evaluations": [],
                            "would_match": [],
                            "would_not_match": []
                        })
                    return result
                
                prepared_rules.sort(key=lambda r: r['priority'])
                logger.info("Rules prepared for execution", prepared_count=len(prepared_rules))
                
                # Initialize result tracking
                results = []
                rule_evaluations: List[Dict[str, Any]] = []
                executed_rules_count = 0
                matched_rules_count = 0
                total_points = 0.0
                
                # Execute each rule
                for rule in prepared_rules:
                    try:
                        rule_id = rule.get('rule_name', 'unknown')
                        logger.debug("Processing DMN rule", rule_id=rule_id, 
                                   rule_priority=rule.get('priority'))
                        
                        # Track per-rule metrics
                        rule_start_time = time.time()
                        
                        result = rule_run(rule, validated_data)
                        executed_rules_count += 1
                        
                        rule_execution_time = (time.time() - rule_start_time) * 1000  # ms
                        
                        # Validate result structure
                        if not isinstance(result, dict):
                            logger.error("Rule run returned invalid result", 
                                       rule_id=rule_id, result_type=type(result).__name__)
                            raise RuleEvaluationError(
                                f"Rule {rule_id} returned invalid result type: {type(result).__name__}",
                                error_code="RULE_RESULT_INVALID",
                                context={'rule_id': rule_id, 'result': result}
                            )
                        
                        # Extract and validate points and weight
                        rule_matched = result.get("action_result", "-") != "-"
                        if rule_matched:
                            matched_rules_count += 1
                            metrics.increment('dmn_rules_matched', dimensions={'rule_name': rule_id})
                        else:
                            metrics.increment('dmn_rules_not_matched', dimensions={'rule_name': rule_id})
                        
                        # Track per-rule execution time
                        metrics.put_metric(
                            'dmn_rule_evaluation_time',
                            rule_execution_time,
                            'Milliseconds',
                            dimensions={'rule_name': rule_id}
                        )
                        
                        try:
                            # Explicit type conversion with validation
                            rule_point_value = result.get("rule_point", 0)
                            weight_value = result.get("weight", 0)
                            
                            # Validate types before conversion
                            if not isinstance(rule_point_value, (int, float, str)):
                                raise TypeError(f"Invalid rule_point type: {type(rule_point_value).__name__}")
                            if not isinstance(weight_value, (int, float, str)):
                                raise TypeError(f"Invalid weight type: {type(weight_value).__name__}")
                            
                            rule_point = float(rule_point_value)
                            weight = float(weight_value)
                            total_points += (rule_point * weight)
                        except (ValueError, TypeError) as conversion_error:
                            logger.warning("Invalid rule_point or weight", 
                                        rule_id=rule_id, rule_point=result.get("rule_point"),
                                        weight=result.get("weight"), error=str(conversion_error))
                            # Continue with 0 points if conversion fails
                            total_points += 0.0
                        
                        action_result = result.get("action_result", "-")
                        results.append(action_result)
                        
                        # Track detailed rule evaluation for dry-run mode
                        if dry_run:
                            rule_evaluation = {
                                'rule_name': rule_id,
                                'rule_priority': rule.get('priority'),
                                'condition': rule.get('condition', ''),
                                'matched': rule_matched,
                                'action_result': action_result,
                                'rule_point': result.get("rule_point", 0.0),
                                'weight': result.get("weight", 0.0),
                                'execution_time_ms': rule_execution_time
                            }
                            rule_evaluations.append(rule_evaluation)
                        
                        logger.debug("DMN rule processed", rule_id=rule_id, 
                                   action_result=action_result, 
                                   points=result.get("rule_point"), 
                                   weight=result.get("weight"),
                                   matched=rule_matched)
                        
                        if rule_matched:
                            matched_rule_ids.append(rule_id)
                    
                    except RuleEvaluationError:
                        # Re-raise rule evaluation errors
                        raise
                    except Exception as rule_error:
                        logger.error("Error processing DMN rule", rule_id=rule.get('rule_name', 'unknown'),
                                   error=str(rule_error), exc_info=True)
                        # Continue with next rule instead of failing completely
                        continue
            
            # Build pattern result (optimized string concatenation)
            tmp_str = "".join(results) if results else ""
            logger.debug("Processing action pattern", pattern_result=tmp_str)
            
            # Get action recommendation (optional - DMN doesn't include patterns)
            # Try to load actions_set, but don't fail if not available
            tmp_action = None
            try:
                actions_set = actions_set_cfg_read()
                tmp_action = find_action_recommendation(actions_set, tmp_str)
            except Exception as action_error:
                logger.debug("Action recommendation not available", error=str(action_error))
                tmp_action = None
            
            # Build result
            result = {
                "total_points": total_points,
                "pattern_result": tmp_str,
                "action_recommendation": tmp_action
            }
            
            # Include decision outputs if available (from dependency-ordered execution)
            if decision_outputs:
                result["decision_outputs"] = decision_outputs
            
            # Add dry-run specific fields
            if dry_run:
                would_match = [e for e in rule_evaluations if e['matched']]
                would_not_match = [e for e in rule_evaluations if not e['matched']]
                result.update({
                    "rule_evaluations": rule_evaluations,
                    "would_match": would_match,
                    "would_not_match": would_not_match,
                    "dry_run": True
                })
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Track metrics
            metrics.increment('dmn_executions_total', dimensions={'dry_run': str(dry_run)})
            metrics.put_metric('dmn_execution_time', execution_time_ms, 'Milliseconds')
            metrics.put_metric('dmn_total_points', total_points, 'Count')
            metrics.increment('dmn_rules_evaluated', value=executed_rules_count)
            
            logger.info("DMN rules execution completed", 
                       execution_id=execution_id,
                       correlation_id=correlation_id,
                       total_points=total_points, 
                       pattern_result=tmp_str, 
                       action_recommendation=tmp_action, 
                       executed_rules=executed_rules_count,
                       matched_rules=matched_rules_count,
                       execution_time_ms=execution_time_ms,
                       dry_run=dry_run)
            
            # Log to execution history
            history.log_execution(
                input_data=validated_data,
                output_data=result,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                rules_evaluated=executed_rules_count,
                rules_matched=matched_rules_count,
                rule_evaluations=rule_evaluations if dry_run else None
            )

            # Track consumer usage if consumer_id is provided
            if consumer_id and matched_rule_ids:
                try:
                    tracking_service = get_usage_tracking_service()
                    tracking_service.track_usage(
                        consumer_id=consumer_id,
                        rule_ids=matched_rule_ids,
                        ruleset_id=None 
                    )
                except Exception as e:
                    logger.warning("Failed to track consumer usage", error=str(e), consumer_id=consumer_id)
            
            return result
            
    except (DataValidationError, ConfigurationError, RuleEvaluationError) as e:
        error = str(e)
        error_code = getattr(e, 'error_code', None)
        # Re-raise specific errors
        raise
    except Exception as execution_error:
        error = str(execution_error)
        error_code = "DMN_RULES_EXEC_ERROR"
        logger.error("Unexpected error in DMN rules execution", error=error, exc_info=True)
        raise RuleEvaluationError(
            f"Unexpected error in DMN rules execution: {error}",
            error_code=error_code,
            context={'error': error}
        ) from execution_error
    finally:
        # Log failed execution to history
        if error:
            execution_time_ms = (time.time() - start_time) * 1000
            history.log_execution(
                input_data=data if isinstance(data, dict) else {},
                output_data={},
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                rules_evaluated=0,
                rules_matched=0,
                error=error,
                error_code=error_code
            )


if __name__ == "__main__":
    logger.info("Executing services.ruleengine_exec as main")
