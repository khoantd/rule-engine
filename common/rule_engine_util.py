import configparser
import json
import re
import rule_engine
from typing import Any, Dict, List, Optional, Union
from common.json_util import read_json_file
from common.json_util import parse_json_v2
from common.s3_aws_util import config_file_read
from domain.conditions.condition_obj import Condition
from domain.rules.rule_obj import ExtRule
from common.conditions_enum import equation_operators, logical_operators
from common.util import cfg_read
from common.logger import get_logger
from common.exceptions import ConfigurationError, RuleEvaluationError, RuleCompilationError
from common.cache import memoize_with_cache, lru_cache_with_ttl, get_file_cache

logger = get_logger(__name__)


def rules_set_cfg_read() -> List[Dict[str, Any]]:
    """
    Read and parse rules configuration from repository (cached via ConfigLoader).
    
    This function is a wrapper around ConfigLoader for backward compatibility.
    The actual caching is handled by ConfigLoader.
    
    Returns:
        List of rules from configuration. Each rule is a dictionary containing
        rule configuration data.
        
    Raises:
        ConfigurationError: If configuration file cannot be read or parsed
        
    Example:
        >>> rules = rules_set_cfg_read()
        >>> len(rules)
        5
    """
    from common.config_loader import get_config_loader
    config_loader = get_config_loader()
    return config_loader.load_rules_set()


def actions_set_cfg_read() -> Dict[str, Any]:
    """
    Read and parse actions/patterns configuration from repository (cached via ConfigLoader).
    
    This function is a wrapper around ConfigLoader for backward compatibility.
    The actual caching is handled by ConfigLoader.
    
    Returns:
        Dictionary of action patterns from configuration. Keys are pattern strings,
        values are action recommendations.
        
    Raises:
        ConfigurationError: If configuration file cannot be read or parsed
        
    Example:
        >>> actions = actions_set_cfg_read()
        >>> 'ABC' in actions
        True
    """
    from common.config_loader import get_config_loader
    config_loader = get_config_loader()
    return config_loader.load_actions_set()


def conditions_set_cfg_read() -> List[Dict[str, Any]]:
    """
    Read and parse conditions configuration from repository (cached via ConfigLoader).
    
    This function is a wrapper around ConfigLoader for backward compatibility.
    The actual caching is handled by ConfigLoader.
    
    Returns:
        List of conditions from configuration. Each condition is a dictionary
        containing condition configuration data (condition_id, attribute,
        equation, constant, etc.).
        
    Raises:
        ConfigurationError: If configuration file cannot be read or parsed
        
    Example:
        >>> conditions = conditions_set_cfg_read()
        >>> len(conditions)
        10
    """
    from common.config_loader import get_config_loader
    config_loader = get_config_loader()
    return config_loader.load_conditions_set()


def rules_set_setup(rules_set: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Set up rules by loading conditions and preparing rules for execution (cached).
    
    This function caches the prepared rules list and automatically sorts them
    by priority to avoid re-sorting on every execution.
    
    Args:
        rules_set: List of rule dictionaries from configuration. Each rule should
            contain rule metadata (rulename, type, priority, conditions, etc.).
    
    Returns:
        List of prepared and sorted rule execution dictionaries. Each dictionary contains:
            - priority: Rule priority (int)
            - rule_name: Rule name (str)
            - condition: Prepared condition string (str)
            - rule_point: Rule point value (float)
            - action_result: Action result string (str)
            - weight: Rule weight (float)
        Rules are sorted by priority (ascending).
    
    Raises:
        ConfigurationError: If conditions cannot be loaded
        RuleCompilationError: If rules cannot be prepared
        
    Example:
        >>> rules = [{'rulename': 'Rule1', 'type': 'simple', ...}]
        >>> prepared = rules_set_setup(rules)
        >>> len(prepared)
        1
    """
    # Check cache first using hash of rules set
    cache = get_file_cache()
    # Generate stable cache key from rules set content
    import hashlib
    rules_hash = hashlib.md5(
        json.dumps([{k: v for k, v in sorted(r.items())} for r in rules_set], sort_keys=True).encode()
    ).hexdigest()
    cache_key = f"rules_setup_{rules_hash}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug("Using cached rules setup")
        return cached_result
    
    # Load conditions and prepare rules
    conditionss_set = conditions_set_load()
    rule_exec_result_list = rules_set_exec(rules_set, conditionss_set)
    
    # Sort rules by priority once (cache sorted result)
    rule_exec_result_list = sorted(rule_exec_result_list, key=sort_by_priority)
    
    # Cache the result (get file paths for change detection)
    try:
        conditions_file = cfg_read("CONDITIONS", "file_name")
        cache.set(cache_key, rule_exec_result_list, file_paths=[conditions_file])
    except Exception:
        # Fallback if config read fails
        cache.set(cache_key, rule_exec_result_list)
    
    logger.debug("Rules setup completed and cached", rules_count=len(rule_exec_result_list))
    return rule_exec_result_list


def rules_set_exec(
    rules_set: List[Dict[str, Any]], 
    conditionss_set: List[Condition]
) -> List[Dict[str, Any]]:
    """
    Execute rule preparation for a set of rules.
    
    Args:
        rules_set: List of rule dictionaries to prepare
        conditionss_set: List of Condition objects available for rule construction
    
    Returns:
        List of prepared rule execution dictionaries. Each contains rule metadata
        with compiled condition strings ready for evaluation.
    
    Raises:
        RuleCompilationError: If any rule cannot be prepared
        
    Example:
        >>> rules = [{'rulename': 'Rule1', ...}]
        >>> conditions = [Condition(...), ...]
        >>> prepared = rules_set_exec(rules, conditions)
        >>> len(prepared) == len(rules)
        True
    """
    rules_list = rules_set
    prepared_rules_list = []
    for rule in rules_list:
        prepared_rules_list.append(rule_prepare(conditionss_set, rule))
    return prepared_rules_list


# Keys accepted by ExtRule.__init__ (domain/rules/rule_obj.py)
_EXTRULE_KEYS = frozenset({
    "id", "rule_name", "conditions", "description", "result",
    "rule_point", "weight", "priority", "type", "action_result",
})


def _rule_dict_to_extrule_kwargs(
    conditionss_set: List[Condition],
    rule: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize a rule dict to kwargs accepted by ExtRule.__init__.

    Handles two config formats:
    - Structured: rule has 'conditions' (with 'item' or 'items'), 'description', 'result'.
    - Flat: rule has 'attribute', 'condition', 'constant', 'message' (inline condition).
      Resolves the inline condition via conditionss_set and builds conditions.item.
    """
    # Flat format: attribute, condition (equation), constant, message
    if "attribute" in rule or "condition" in rule or "constant" in rule:
        attr = rule.get("attribute")
        equation = rule.get("condition")
        constant = rule.get("constant")
        if attr is not None and equation is not None:
            constant_str = str(constant) if constant is not None else ""
            condition_id = None
            for cond in conditionss_set:
                if (
                    getattr(cond, "attribute", None) == attr
                    and getattr(cond, "equation", None) == equation
                    and str(getattr(cond, "constant", "")) == constant_str
                ):
                    condition_id = cond.condition_id
                    break
            if condition_id is None:
                raise RuleCompilationError(
                    f"No matching condition for attribute={attr!r}, condition={equation!r}, constant={constant_str!r}",
                    error_code="CONDITION_NOT_FOUND",
                    context={
                        "rule_name": rule.get("rule_name", rule.get("rulename", "unknown")),
                        "attribute": attr,
                        "condition": equation,
                        "constant": constant,
                    },
                )
            kwargs = {
                "id": rule.get("id", ""),
                "rule_name": rule.get("rule_name", rule.get("rulename", "unknown")),
                "conditions": {"item": condition_id},
                "description": rule.get("message", rule.get("description", "")),
                "result": rule.get("action_result", rule.get("result", "")),
                "rule_point": float(rule.get("rule_point", 0)),
                "weight": float(rule.get("weight", 0)),
                "priority": int(rule.get("priority", 0)),
                "type": "simple",
                "action_result": rule.get("action_result", rule.get("result", "")),
            }
            return kwargs
    # Structured format: only pass keys ExtRule accepts (with aliases)
    raw_type = rule.get("type", "simple")
    if raw_type == "standard":
        raw_type = "simple"
    kwargs = {
        k: rule[k]
        for k in _EXTRULE_KEYS
        if k in rule
    }
    # Support alternate config keys: rulename -> rule_name, rulepoint -> rule_point
    if "rule_name" not in kwargs and "rulename" in rule:
        kwargs["rule_name"] = rule["rulename"]
    if "rule_point" not in kwargs and "rulepoint" in rule:
        kwargs["rule_point"] = float(rule["rulepoint"])
    if "type" not in kwargs:
        kwargs["type"] = raw_type
    else:
        kwargs["type"] = "simple" if kwargs["type"] == "standard" else kwargs["type"]
    # Ensure required ExtRule fields exist
    kwargs.setdefault("id", rule.get("id", ""))
    kwargs.setdefault("rule_name", rule.get("rule_name", rule.get("rulename", "unknown")))
    kwargs.setdefault("conditions", rule.get("conditions"))
    kwargs.setdefault("description", rule.get("description", rule.get("message", "")))
    kwargs.setdefault("result", rule.get("result", rule.get("action_result", "")))
    kwargs.setdefault("rule_point", float(rule.get("rule_point", rule.get("rulepoint", 0))))
    kwargs.setdefault("weight", float(rule.get("weight", 0)))
    kwargs.setdefault("priority", int(rule.get("priority", 0)))
    kwargs.setdefault("action_result", rule.get("action_result", rule.get("result", "")))
    return kwargs


def rule_prepare(
    conditionss_set: List[Condition], 
    rule: Union[Dict[str, Any], ExtRule]
) -> Dict[str, Any]:
    """
    Prepare a rule for execution by constructing its condition string.
    
    This function converts a rule configuration into an executable format by:
    - Resolving condition references to actual condition objects
    - Building condition strings using equation operators
    - Combining multiple conditions with logical operators (for complex rules)
    - Compiling the final condition string ready for rule engine evaluation
    
    Args:
        conditionss_set: List of Condition objects available for rule construction.
            Conditions are matched by condition_id.
        rule: Rule to prepare. Can be either:
            - A dictionary containing rule configuration (rulename, type, priority,
              conditions, rulepoint, weight, action_result, etc.)
            - An ExtRule object with the same attributes
    
    Returns:
        Dictionary containing prepared rule execution metadata:
            - priority: Rule priority (int) - used for sorting execution order
            - rule_name: Rule name/identifier (str)
            - condition: Compiled condition string ready for rule engine (str)
            - rule_point: Point value awarded if rule matches (float)
            - action_result: Action string returned if rule matches (str)
            - weight: Weight multiplier for rule points (float)
    
    Raises:
        RuleCompilationError: If rule cannot be prepared due to:
            - Invalid rule structure or missing required fields
            - Invalid rule type (must be 'simple' or 'complex')
            - Missing conditions structure or items
            - Missing mode for complex rules
        ConfigurationError: If required conditions are not found in conditions_set
        
    Example:
        >>> conditions = [Condition('cond1', 'Test', 'status', '==', 'open')]
        >>> rule = {'rulename': 'Rule1', 'type': 'simple', 'priority': 1,
        ...         'conditions': {'item': 'cond1'}, 'rulepoint': 10.0,
        ...         'weight': 1.0, 'action_result': 'APPROVE'}
        >>> prepared = rule_prepare(conditions, rule)
        >>> prepared['condition']
        'status == open'
    """
    rule_name = rule.get('rulename', 'unknown') if isinstance(rule, dict) else getattr(rule, 'rulename', 'unknown')
    logger.debug("Preparing rule for execution", rule_name=rule_name)
    
    try:
        # Validate rule structure
        if not rule:
            logger.error("Rule is None or empty", rule_name=rule_name)
            raise RuleCompilationError(
                "Rule cannot be None or empty",
                error_code="RULE_EMPTY",
                context={'rule': rule}
            )
        
        # Convert rule to ExtRule if needed
        if isinstance(rule, dict):
            try:
                kwargs = _rule_dict_to_extrule_kwargs(conditionss_set, rule)
                tmp_rule = ExtRule(**kwargs)
            except RuleCompilationError:
                raise
            except TypeError as e:
                logger.error("Invalid rule structure", rule_name=rule_name, error=str(e), exc_info=True)
                raise RuleCompilationError(
                    f"Invalid rule structure: {str(e)}",
                    error_code="RULE_INVALID_STRUCTURE",
                    context={'rule': rule, 'error': str(e)}
                ) from e
        else:
            tmp_rule = rule
        
        rule_exec_result = {}
        tmp_cond_concated_str = ""
        tmp_logical_operator = ""
        tmp_cond_ls = []
        
        # Validate rule type
        if tmp_rule.type not in ['complex', 'simple']:
            logger.error("Invalid rule type", rule_name=rule_name, rule_type=tmp_rule.type)
            raise RuleCompilationError(
                f"Invalid rule type: {tmp_rule.type}. Must be 'complex' or 'simple'",
                error_code="RULE_INVALID_TYPE",
                context={'rule_name': rule_name, 'rule_type': tmp_rule.type}
            )
        
        if tmp_rule.type == 'complex':
            # Validate conditions structure for complex rules
            if not hasattr(tmp_rule, 'conditions') or not isinstance(tmp_rule.conditions, dict):
                logger.error("Invalid conditions structure for complex rule", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Complex rule must have 'conditions' dictionary",
                    error_code="RULE_INVALID_CONDITIONS",
                    context={'rule_name': rule_name, 'rule_type': 'complex'}
                )
            
            if 'items' not in tmp_rule.conditions:
                logger.error("Missing 'items' in complex rule conditions", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Complex rule must have 'conditions.items'",
                    error_code="RULE_MISSING_CONDITIONS_ITEMS",
                    context={'rule_name': rule_name}
                )
            
            tmp_conditions = tmp_rule.conditions['items']
            
            if not isinstance(tmp_conditions, list) or len(tmp_conditions) == 0:
                logger.error("Empty conditions items list", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Complex rule must have at least one condition item",
                    error_code="RULE_EMPTY_CONDITIONS",
                    context={'rule_name': rule_name}
                )
            
            # Build condition strings
            for condition_index in range(len(tmp_conditions)):
                condition_id = tmp_conditions[condition_index]
                condition_found = False
                
                for cond in conditionss_set:
                    if cond.condition_id == condition_id:
                        condition_found = True
                        # Optimized string formatting using f-string
                        tmp_str = f"{cond.attribute} {equation_operators(cond.equation)} {cond.constant}"
                        tmp_cond_ls.append(tmp_str)
                        logger.debug("Condition found and added", rule_name=rule_name, 
                                   condition_id=condition_id, condition_str=tmp_str)
                        break
                
                if not condition_found:
                    logger.warning("Condition not found in conditions set", 
                                rule_name=rule_name, condition_id=condition_id)
                    # Continue processing but log warning
            
            if len(tmp_cond_ls) == 0:
                logger.error("No valid conditions found for complex rule", rule_name=rule_name)
                raise ConfigurationError(
                    f"No valid conditions found for rule {rule_name}",
                    error_code="CONDITIONS_NOT_FOUND",
                    context={'rule_name': rule_name, 'required_conditions': tmp_conditions}
                )
            
            # Get logical operator
            if 'mode' not in tmp_rule.conditions:
                logger.error("Missing 'mode' in complex rule conditions", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Complex rule must have 'conditions.mode'",
                    error_code="RULE_MISSING_MODE",
                    context={'rule_name': rule_name}
                )
            
            tmp_logical_operator = logical_operators(tmp_rule.conditions['mode'])
            tmp_cond_concated_str = f' {tmp_logical_operator} '.join(map(str, tmp_cond_ls))
            
            logger.debug("Complex rule condition prepared", rule_name=rule_name, 
                       condition_str=tmp_cond_concated_str, logical_operator=tmp_logical_operator)
            
        elif tmp_rule.type == 'simple':
            # Validate conditions structure for simple rules
            if not hasattr(tmp_rule, 'conditions') or not isinstance(tmp_rule.conditions, dict):
                logger.error("Invalid conditions structure for simple rule", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Simple rule must have 'conditions' dictionary",
                    error_code="RULE_INVALID_CONDITIONS",
                    context={'rule_name': rule_name, 'rule_type': 'simple'}
                )
            
            if 'item' not in tmp_rule.conditions:
                logger.error("Missing 'item' in simple rule conditions", rule_name=rule_name)
                raise RuleCompilationError(
                    f"Simple rule must have 'conditions.item'",
                    error_code="RULE_MISSING_CONDITION_ITEM",
                    context={'rule_name': rule_name}
                )
            
            tmp_condition = tmp_rule.conditions['item']
            condition_found = False
            tmp_str = ""
            
            for cond in conditionss_set:
                if cond.condition_id == tmp_condition:
                    condition_found = True
                    # Optimized string formatting using f-string
                    tmp_str = f"{cond.attribute} {equation_operators(cond.equation)} {cond.constant}"
                    logger.debug("Condition found for simple rule", rule_name=rule_name, 
                               condition_id=tmp_condition, condition_str=tmp_str)
                    break
            
            if not condition_found:
                logger.error("Condition not found in conditions set", 
                           rule_name=rule_name, condition_id=tmp_condition)
                raise ConfigurationError(
                    f"Condition {tmp_condition} not found in conditions set for rule {rule_name}",
                    error_code="CONDITION_NOT_FOUND",
                    context={'rule_name': rule_name, 'condition_id': tmp_condition}
                )
            
            tmp_cond_concated_str = tmp_str
            logger.debug("Simple rule condition prepared", rule_name=rule_name, 
                       condition_str=tmp_cond_concated_str)
        
        # Build rule execution result
        rule_exec_result = {
            "priority": tmp_rule.priority,
            "rule_name": tmp_rule.rulename,
            "condition": tmp_cond_concated_str,
            "rule_point": tmp_rule.rulepoint,
            "action_result": tmp_rule.action_result,
            "weight": tmp_rule.weight
        }
        
        logger.debug("Rule prepared successfully", rule_name=rule_name, 
                   priority=tmp_rule.priority, condition_length=len(tmp_cond_concated_str))
        
        return rule_exec_result
        
    except (RuleCompilationError, ConfigurationError):
        raise
    except Exception as error:
        logger.error("Unexpected error preparing rule", rule_name=rule_name, 
                    error=str(error), exc_info=True)
        raise RuleCompilationError(
            f"Failed to prepare rule {rule_name}: {str(error)}",
            error_code="RULE_PREPARE_ERROR",
            context={'rule_name': rule_name, 'error': str(error)}
        ) from error


def conditions_set_load() -> List[Condition]:
    """
    Load conditions from configuration file and convert to Condition objects.
    
    Returns:
        List of Condition objects created from configuration. Each Condition
        contains condition_id, condition_name, attribute, equation, and constant.
    
    Raises:
        ConfigurationError: If conditions configuration cannot be read
        ValueError: If condition data is invalid and cannot create Condition objects
        
    Example:
        >>> conditions = conditions_set_load()
        >>> len(conditions)
        10
        >>> isinstance(conditions[0], Condition)
        True
    """
    conditions_list: List[Condition] = []
    loaded_conditions_set = conditions_set_cfg_read()
    for item in loaded_conditions_set:
        tmp_condition = Condition(**item)
        conditions_list.append(tmp_condition)
    return conditions_list

def rule_setup(rule: Dict[str, Any], condition: str) -> Dict[str, Any]:
    """
    Create a rule execution dictionary from rule data and condition string.
    
    Args:
        rule: Dictionary containing rule metadata:
            - priority: Rule priority (int)
            - rule_name: Rule name (str)
            - rule_point: Rule point value (float)
            - action_result: Action result string (str)
            - weight: Rule weight (float)
        condition: Compiled condition string ready for rule engine evaluation
    
    Returns:
        Dictionary containing rule execution metadata:
            - priority: Rule priority (int)
            - rule_name: Rule name (str)
            - condition: Condition string (str)
            - rule_point: Rule point value (float)
            - action_result: Action result string (str)
            - weight: Rule weight (float)
    
    Example:
        >>> rule = {'priority': 1, 'rule_name': 'Rule1', 'rule_point': 10.0,
        ...         'action_result': 'APPROVE', 'weight': 1.0}
        >>> condition = 'status == open'
        >>> prepared = rule_setup(rule, condition)
        >>> prepared['condition']
        'status == open'
    """
    tmp_rule = {
        "priority": rule["priority"],
        "rule_name": rule["rule_name"],
        "condition": condition,
        "rule_point": rule["rule_point"],
        "action_result": rule["action_result"],
        "weight": rule["weight"]
    }
    return tmp_rule


def condition_setup(rule: Dict[str, Any]) -> str:
    """
    Build a condition string from rule attributes.
    
    Args:
        rule: Dictionary containing:
            - attribute: Field/attribute name to check (str)
            - condition: Equation operator (str, e.g., '==', '>', '<')
            - constant: Comparison value (str or number)
    
    Returns:
        Condition string in format: "attribute operator constant"
        Example: "status == open" or "amount > 100"
    
    Raises:
        KeyError: If required keys are missing from rule dictionary
        ValueError: If equation operator is invalid
        
    Example:
        >>> rule = {'attribute': 'status', 'condition': '==', 'constant': 'open'}
        >>> condition_setup(rule)
        'status == open'
    """
    tmp_condition: List[str] = []
    tmp_condition.append(rule["attribute"])
    tmp_condition.append(equation_operators(rule["condition"]))
    tmp_condition.append(str(rule["constant"]))
    return " ".join(tmp_condition)


def rules_set_read(json_file: str) -> List[Dict[str, Any]]:
    """
    Read rules set from a JSON file.
    
    Args:
        json_file: Path to JSON file containing rules configuration.
            File should contain a "rules_set" key with array of rules.
    
    Returns:
        List of rule dictionaries from the "rules_set" key in JSON file.
        Returns empty list if rules_set not found.
    
    Raises:
        ConfigurationError: If file cannot be read or JSON is invalid
        
    Example:
        >>> rules = rules_set_read('data/input/rules_config.json')
        >>> len(rules)
        5
    """
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.rules_set", json_data)
    return parsed_data_main_node


def condition_set_read(json_file: str) -> List[Dict[str, Any]]:
    """
    Read conditions set from a JSON file.
    
    Args:
        json_file: Path to JSON file containing conditions configuration.
            File should contain a "conditions_set" key with array of conditions.
    
    Returns:
        List of condition dictionaries from the "conditions_set" key in JSON file.
        Returns 0 (zero) if conditions_set not found (due to parse_json_v2 behavior).
    
    Raises:
        ConfigurationError: If file cannot be read or JSON is invalid
        
    Note:
        The function uses parse_json_v2 which returns 0 for missing paths.
        Caller should check return value.
        
    Example:
        >>> conditions = condition_set_read('data/input/conditions_config.json')
        >>> len(conditions) if isinstance(conditions, list) else 0
        10
    """
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.conditions_set", json_data)
    return parsed_data_main_node


def rules_set_from_s3_read(config_file: str) -> List[Dict[str, Any]]:
    """
    Read rules set from S3 configuration file.
    
    Args:
        config_file: S3 key/path to configuration file containing rules.
            File should be JSON format with "rules_set" key.
    
    Returns:
        List of rule dictionaries from the "rules_set" key in S3 file.
        Returns 0 (zero) if rules_set not found.
    
    Raises:
        StorageError: If S3 access fails or file cannot be read
        ConfigurationError: If JSON parsing fails
        
    Example:
        >>> rules = rules_set_from_s3_read('config/rules_config.json')
        >>> len(rules) if isinstance(rules, list) else 0
        5
    """
    cfg_content = config_file_read("S3", config_file)
    parsed_data_main_node = parse_json_v2(
        "$.rules_set", json.loads(cfg_content))
    return parsed_data_main_node


def rule_actions_read(json_file: str) -> Dict[str, Any]:
    """
    Read rule actions/patterns from a JSON file.
    
    Args:
        json_file: Path to JSON file containing patterns/actions configuration.
            File should contain a "patterns" key with dictionary mapping
            pattern strings to action recommendations.
    
    Returns:
        Dictionary mapping pattern strings to action recommendations.
        Returns 0 (zero) if patterns not found.
    
    Raises:
        ConfigurationError: If file cannot be read or JSON is invalid
        
    Example:
        >>> actions = rule_actions_read('data/input/rules_config.json')
        >>> 'ABC' in actions if isinstance(actions, dict) else False
        True
    """
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.patterns", json_data)
    return parsed_data_main_node


def rule_actions_from_S3_read(config_file: str) -> Dict[str, Any]:
    """
    Read rule actions/patterns from S3 configuration file.
    
    Args:
        config_file: S3 key/path to configuration file containing patterns.
            File should be JSON format with "patterns" key.
    
    Returns:
        Dictionary mapping pattern strings to action recommendations.
        Returns 0 (zero) if patterns not found.
    
    Raises:
        StorageError: If S3 access fails or file cannot be read
        ConfigurationError: If JSON parsing fails
        
    Example:
        >>> actions = rule_actions_from_S3_read('config/rules_config.json')
        >>> 'ABC' in actions if isinstance(actions, dict) else False
        True
    """
    cfg_content = config_file_read("S3", config_file)
    parsed_data_main_node = parse_json_v2(
        "$.patterns", json.loads(cfg_content))
    return parsed_data_main_node


def find_action_recommendation(
    actions_list: Dict[str, Any], 
    data: str
) -> Optional[str]:
    """
    Find action recommendation by matching pattern result against actions dictionary.
    
    Args:
        actions_list: Dictionary mapping pattern strings to action recommendations.
            Keys are pattern strings (e.g., 'ABC', 'DEF'), values are action strings.
        data: Pattern result string to match against action keys.
            This is typically a concatenated string of action results from
            multiple rules (e.g., 'ABC', 'DEF', etc.).
    
    Returns:
        Action recommendation string if exact match found, None otherwise.
        Returns None if actions_list is empty or data is None.
    
    Raises:
        ValueError: If actions_list is not a dictionary
    
    Example:
        >>> actions = {'ABC': 'APPROVE', 'DEF': 'REJECT'}
        >>> find_action_recommendation(actions, 'ABC')
        'APPROVE'
        >>> find_action_recommendation(actions, 'XYZ')
        None
    """
    if not actions_list:
        logger.warning("Actions list is empty")
        return None
    
    if not isinstance(actions_list, dict):
        logger.error("Actions list must be a dictionary", actions_list_type=type(actions_list).__name__)
        raise ValueError(f"Actions list must be a dictionary, got {type(actions_list).__name__}")
    
    if data is None:
        logger.warning("Data is None for action lookup")
        return None
    
    logger.debug("Looking up action", pattern_data=data, available_patterns=list(actions_list.keys()))
    
    try:
        for key, value in actions_list.items():
            if key == data:
                logger.debug("Action found", pattern=key, action=value)
                return value
        
        logger.debug("No action found for pattern", pattern_data=data)
        return None
    except Exception as e:
        logger.error("Error in action lookup", error=str(e), exc_info=True)
        raise ValueError(f"Failed to lookup action: {str(e)}") from e


def rule_run(rule: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single rule against input data using the rule engine.
    
    This function evaluates whether a rule's condition matches the input data.
    If the rule matches, it returns the action result, points, and weight.
    If the rule doesn't match or evaluation fails, it returns default values.
    
    Args:
        rule: Dictionary containing prepared rule data:
            - rule_name: Rule identifier (str)
            - condition: Compiled condition string for rule engine (str)
            - action_result: Action to return if rule matches (str)
            - rule_point: Points awarded if rule matches (float)
            - weight: Weight multiplier for points (float)
        data: Dictionary containing input data to evaluate against rule condition.
            Data should contain attributes referenced in rule condition.
    
    Returns:
        Dictionary containing rule evaluation result:
            - action_result: Action string if rule matched, '-' otherwise (str)
            - rule_point: Points awarded if rule matched, 0.0 otherwise (float)
            - weight: Weight value from rule, or 0.0 if rule didn't match (float)
    
    Raises:
        None: All exceptions are caught and logged. Function returns default values
        ('-', 0.0, 0.0) on any error.
    
    Example:
        >>> rule = {
        ...     'rule_name': 'Rule1',
        ...     'condition': 'status == "open"',
        ...     'action_result': 'APPROVE',
        ...     'rule_point': 10.0,
        ...     'weight': 1.0
        ... }
        >>> data = {'status': 'open', 'priority': 'high'}
        >>> result = rule_run(rule, data)
        >>> result['action_result']
        'APPROVE'
        >>> result['rule_point']
        10.0
    """
    rule_id = rule.get('rule_name', 'unknown')
    rule_condition = rule.get("condition", "")
    logger.debug("Starting rule evaluation", rule_id=rule_id, condition=rule_condition)
    tmp_action: str = ""
    tmp_weight: float = 0.0
    tmp_point: float = 0.0
    try:
        logger.debug("Creating rule engine rule", rule_id=rule_id, condition=rule_condition)
        rule_engine_rule = rule_engine.Rule(rule["condition"])
        rule_matched = rule_engine_rule.matches(data)
        logger.debug("Rule evaluation result", rule_id=rule_id, matched=rule_matched, rule_point=rule.get('rule_point'))
        if rule_matched:
            action_result_raw = rule.get("action_result", "")
            # Evaluate FEEL expressions in action_result if present
            if action_result_raw and isinstance(action_result_raw, str):
                tmp_action = _evaluate_feel_expression(action_result_raw, data)
            else:
                tmp_action = str(action_result_raw)
            
            # Explicit type conversion with validation
            rule_point_value = rule.get('rule_point', 0)
            weight_value = rule.get('weight', 0)
            
            try:
                # Validate types before conversion
                if not isinstance(rule_point_value, (int, float, str)):
                    raise TypeError(f"Invalid rule_point type: {type(rule_point_value).__name__}")
                if not isinstance(weight_value, (int, float, str)):
                    raise TypeError(f"Invalid weight type: {type(weight_value).__name__}")
                
                tmp_point = float(rule_point_value)
                tmp_weight = float(weight_value)
            except (ValueError, TypeError) as conversion_error:
                logger.warning("Failed to convert rule_point or weight", 
                            rule_id=rule_id, rule_point=rule_point_value, 
                            weight=weight_value, error=str(conversion_error))
                tmp_point = 0.0
                tmp_weight = 0.0
            logger.info("Rule matched successfully", rule_id=rule_id, action_result=tmp_action, 
                       points=tmp_point, weight=tmp_weight)
        else:
            tmp_action = '-'
            logger.debug("Rule did not match", rule_id=rule_id)
    except rule_engine.errors.SymbolResolutionError as symbol_error:
        # Log available keys in data to help debug missing field issues
        available_keys = list(data.keys()) if isinstance(data, dict) else []
        missing_symbol = str(symbol_error).split("'")[1] if "'" in str(symbol_error) else str(symbol_error)
        logger.warning("Rule evaluation failed - symbol not found", 
                      rule_id=rule_id, 
                      error=missing_symbol,
                      available_keys=available_keys,
                      condition=rule_condition)
        tmp_action = '-'
    except Exception as evaluation_error:
        logger.error("Unexpected error in rule evaluation", rule_id=rule_id, error=str(evaluation_error), exc_info=True)
        tmp_action = '-'
    logger.debug("Rule evaluation completed", rule_id=rule_id, action_result=tmp_action, 
                points=tmp_point, weight=tmp_weight)
    return {
        "action_result": tmp_action,
        "rule_point": tmp_point,
        "weight": tmp_weight
    }


def _evaluate_feel_expression(expression: str, data: Dict[str, Any]) -> str:
    """
    Evaluate FEEL (Friendly Enough Expression Language) expressions.
    
    Supports FEEL expressions like:
    - Variable references: {variable_name}
    - String join function: string join({var1}, "-", {var2})
    - Simple variable substitution: {variable_name}
    
    Args:
        expression: FEEL expression string to evaluate
        data: Dictionary containing variable values
        
    Returns:
        Evaluated expression string
        
    Example:
        >>> data = {'can': 'wood', 'chi': 'water'}
        >>> _evaluate_feel_expression('string join({can}, "-", {chi})', data)
        'wood-water'
        >>> _evaluate_feel_expression('{can}', data)
        'wood'
    """
    if not expression or not isinstance(expression, str):
        return str(expression) if expression else ""
    
    expression = expression.strip()
    
    # Check if this looks like a FEEL expression (contains {variable} or FEEL functions)
    if '{' not in expression and 'string join' not in expression.lower():
        # Not a FEEL expression, return as-is
        return expression
    
    try:
        # Handle string join function: string join({var1}, "sep", {var2})
        # Pattern: string join(...) or string join (...)
        join_pattern = r'string\s+join\s*\(([^)]+)\)'
        match = re.search(join_pattern, expression, re.IGNORECASE)
        
        if match:
            # Extract arguments from string join
            args_str = match.group(1)
            # Parse arguments: {var1}, "separator", {var2}
            # Split by comma, but respect quoted strings
            args = []
            current_arg = ""
            in_quotes = False
            quote_char = None
            
            for char in args_str:
                if char in ('"', "'") and (not in_quotes or char == quote_char):
                    if in_quotes and char == quote_char:
                        in_quotes = False
                        quote_char = None
                    else:
                        in_quotes = True
                        quote_char = char
                    current_arg += char
                elif char == ',' and not in_quotes:
                    args.append(current_arg.strip())
                    current_arg = ""
                else:
                    current_arg += char
            
            if current_arg.strip():
                args.append(current_arg.strip())
            
            # Evaluate each argument
            evaluated_args = []
            for arg in args:
                arg = arg.strip()
                # Remove quotes from string literals
                if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                    evaluated_args.append(arg[1:-1])
                # Evaluate variable references
                elif arg.startswith('{') and arg.endswith('}'):
                    var_name = arg[1:-1].strip()
                    value = data.get(var_name, '')
                    evaluated_args.append(str(value) if value is not None else '')
                else:
                    # Try to evaluate as variable reference without braces
                    value = data.get(arg, arg)
                    evaluated_args.append(str(value) if value is not None else '')
            
            # Join the evaluated arguments
            # Format: string join(value1, separator, value2, separator, value3, ...)
            # For string join({can}, "-", {chi}): args = [value1, separator, value2]
            # For string join({a}, " ", {b}, " ", {c}): args = [value1, sep1, value2, sep2, value3]
            if len(evaluated_args) >= 3:
                # Extract separator (should be consistent, typically the second argument)
                separator = evaluated_args[1]
                # Extract values (odd indices: 0, 2, 4, ...)
                values_to_join = []
                for i in range(0, len(evaluated_args), 2):
                    if i < len(evaluated_args):
                        values_to_join.append(str(evaluated_args[i]))
                result = separator.join(v for v in values_to_join if v)
                return result
            elif len(evaluated_args) == 2:
                # Two args: could be value1, separator (single value) or value1, value2 (no separator)
                # If second looks like a separator (short string), treat as value + separator
                # Otherwise treat as two values with empty separator
                if len(str(evaluated_args[1])) <= 5:  # Likely a separator
                    return str(evaluated_args[0])
                else:
                    result = ''.join(str(v) for v in evaluated_args if v)
                    return result
            else:
                # Single arg or empty: return as-is
                return ''.join(str(v) for v in evaluated_args if v)
        
        # Handle simple variable references: {variable_name}
        # Replace all {variable} references with actual values
        var_pattern = r'\{([^}]+)\}'
        
        def replace_var(match_obj: re.Match) -> str:
            var_name = match_obj.group(1).strip()
            value = data.get(var_name, '')
            return str(value) if value is not None else ''
        
        result = re.sub(var_pattern, replace_var, expression)
        return result
        
    except Exception as eval_error:
        logger.warning("Failed to evaluate FEEL expression", 
                      expression=expression, 
                      error=str(eval_error),
                      exc_info=True)
        # Return original expression if evaluation fails
        return expression


def sort_by_priority(rule_item: Dict[str, Any]) -> int:
    """
    Sort key function to order rules by priority.
    
    This function is used with sorted() or list.sort() to sort rules
    by their priority value in ascending order (lower priority numbers first).
    
    Args:
        rule_item: Dictionary containing rule data with 'priority' key.
            Priority should be an integer where lower values have higher priority.
    
    Returns:
        Priority value (int) from rule_item['priority'].
    
    Example:
        >>> rules = [{'priority': 2, 'name': 'Rule2'}, {'priority': 1, 'name': 'Rule1'}]
        >>> sorted(rules, key=sort_by_priority)
        [{'priority': 1, 'name': 'Rule1'}, {'priority': 2, 'name': 'Rule2'}]
    """
    return rule_item['priority']
