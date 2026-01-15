import datetime
import rule_engine
from domain.ticket.ticket_obj import Ticket
from domain.ticket.comic import Comic
from common.json_util import read_json_file, parse_json_v2
from common.conditions_enum import conditional_operators
from common.logger import get_logger

logger = get_logger(__name__)


def print_object():
    ticket_1 = Ticket("TICK-123", "Hello World")
    ticket_info = ticket_1.print_info()
    logger.info("Ticket object created", ticket_id="TICK-123", ticket_info=ticket_info)


def rules_set_read(json_file):
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.rules_set", json_data)
    return parsed_data_main_node


def sort_by_priority(rule_item):
    """Sort function to order rules by priority."""
    return rule_item['priority']


def rules_exec(rules_list, data):
    logger.info("Starting rules execution", rules_count=len(rules_list))
    rules_list.sort(key=sort_by_priority)
    results = []
    executed_rules = 0
    sum = 0
    for rule in rules_list:
        logger.debug("Processing rule", rule_id=rule.get('rule_name'), rule=rule)
        result = rule_run(rule, data)
        executed_rules = executed_rules+1
        sum = sum+result["rule_point"]
        results.append(result["action_result"])
    tmp_str = str("".join(results))

    tmp_action = find_action_recommendation(rule_actions_read(
        "data/input/rules_config.json"), tmp_str)
    rs = {
        "total_points": sum,
        "pattern_result": tmp_str,
        "action_recommendation": tmp_action
    }
    return rs


def find_action_recommendation(actions_list, data):
    """Find action recommendation based on pattern matching."""
    logger.debug("Processing rule action", action_data=data)
    for key, value in actions_list.items():
        logger.debug("Checking action key", action_key=key)
        if key == data:
            logger.debug("Rule action matched", action_key=key, action_value=value)
            return value
    return None


def rule_actions_read(json_file):
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.patterns", json_data)
    return parsed_data_main_node


def rule_run(rule, data):
    logger.debug("Evaluating rule", rule_id=rule.get('rule_name'), condition=rule.get("condition"))
    l_rule = rule_engine.Rule(rule["condition"])
    rs = l_rule.matches(data)
    tmp_action = ""
    tmp_weight = 0
    tmp_point = 0
    rule_point = rule['rule_point']
    logger.debug("Rule evaluation result", rule_id=rule.get('rule_name'), matched=rs, rule_point=rule_point)
    if rs:
        tmp_action = str(rule["action_result"])
        tmp_point = int(rule['rule_point'])
        logger.info("Rule matched", rule_id=rule.get('rule_name'), action_result=tmp_action, points=tmp_point)
    else:
        tmp_action = '-'
        logger.debug("Rule did not match", rule_id=rule.get('rule_name'))
    return {
        "action_result": tmp_action,
        "rule_point": tmp_point
    }


def rules_setup(rules_set):
    rules_list = []
    conditions_list = []
    for rule in rules_set:
        tmp_condition = condition_setup(rule)
        conditions_list.append(tmp_condition)
        tmp_rule = rule_setup(rule, tmp_condition)
        rules_list.append(tmp_rule)
    return rules_list


def condition_setup(rule):
    tmp_condition = []
    tmp_condition.append(rule["attribute"])
    tmp_condition.append(conditional_operators(rule["condition"]))
    tmp_condition.append(rule["constant"])
    return " ".join(tmp_condition)


def rule_setup(rule, condition):
    tmp_rule = {
        "priority": rule["priority"],
        "rule_name": rule["rule_name"],
        "condition": condition,
        "rule_point": rule["rule_point"],
        "action_result": rule["action_result"],
        "weight": rule["weight"]
    }
    return tmp_rule


def type_resolver(name):
    if name == 'title':
        return rule_engine.DataType.STRING
    elif name == 'publisher':
        return rule_engine.DataType.STRING
    elif name == 'issue':
        return rule_engine.DataType.FLOAT
    elif name == 'released':
        return rule_engine.DataType.DATETIME
    # if the name is none of those, raise a SymbolResolutionError
    raise rule_engine.errors.SymbolResolutionError(name)


def rule_testing():
    """Test rule engine with sample data."""
    rule = rule_engine.Rule(
        'first_name == "Luke" and email =~ ".*@rebels.org$"'
    )
    rs1 = rule.matches({
        'first_name': 'Luke', 'last_name': 'Skywalker', 'email': 'luke@rebels.org'
    })
    rs2 = rule.matches({
        'first_name': 'Darth', 'last_name': 'Vader', 'email': 'dvader@empire.net'
    })

    logger.debug("Rule test result 1", result=rs1)
    logger.debug("Rule test result 2", result=rs2)

    comics = [
        Comic('Batman',         'DC',     89,  datetime.date(2020, 4, 28)),
        Comic('Flash',          'DC',     753, datetime.date(2020, 4, 28)),
        Comic('Captain Marvel', 'Marvel', 18,  datetime.date(2020, 5, 6))
    ]

    for comic in comics:
        logger.debug("Comic object", comic=str(comic))
    
    context = rule_engine.Context(type_resolver=type_resolver)
    rule = rule_engine.Rule('publisher in ["DC","Marvel"]', context=context)
    
    for comic in comics:
        tmp_comic = comic
        match_result = rule.matches(tmp_comic.get_Comic())
        logger.debug("Rule match for comic", comic_title=tmp_comic.title, matched=match_result)


def list_of_rules():
    """
    List all available rules.
    
    TODO: Implement functionality to retrieve and return list of all configured rules.
    This should read from rules configuration and return structured rule information.
    
    Returns:
        Empty string (placeholder implementation)
    """
    # TODO: Implement rule listing functionality
    return ""


if __name__ == "__main__":
    logger.info("Starting main_rule_exec_v2.py execution")
    rule_testing()
    logger.info("Loading rules configuration", config_file="data/input/rules_config.json")
    rules_list = rules_setup(rules_set_read("data/input/rules_config.json"))
    data = {
        'title': 'Superman',
        'publisher': 'DC',
        'issue': 40
    }
    logger.info("Executing rules with test data", input_data=data)
    result = rules_exec(rules_list, data)
    logger.info("Rules execution completed", result=result)
