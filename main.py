import datetime
import rule_engine
from domain.ticket.ticket_obj import Ticket
from domain.ticket.comic import Comic
from common.json_util import read_json_file, parse_json_v2
from common.conditions_enum import conditional_operators
from common.s3_aws_util import aws_s3_config_file_read
from common.rule_engine_util import rule_run
from services.workflow_exec import wf_exec
from services.ruleengine_exec import rules_exec
from services.ruleengine_exec import rules_set_cfg_read, rules_set_setup
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


def find_action_recommendation(actions_list, data):
    """Find action recommendation based on pattern matching."""
    logger.debug("Processing rule action", action_data=data)
    for key, value in actions_list.items():
        if key == data:
            logger.debug("Rule action matched", action_key=key, action_value=value)
            return value
    return None


def rule_actions_read(json_file):
    json_data = read_json_file(json_file)
    parsed_data_main_node = parse_json_v2("$.patterns", json_data)
    return parsed_data_main_node


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


# Constants for configuration
S3_BUCKET_ITCR = "itcrstatusreports"

def config_file_read(location, config_file):
    if location == "S3":
        bucket = S3_BUCKET_ITCR
        obj = aws_s3_config_file_read(bucket, config_file)
        return obj


if __name__ == "__main__":
    logger.info("Starting main.py execution")
    data = {'id': 1, 'name': 'Khoa', 'dob': '07/02/1986'}
    logger.info("Executing workflow", process_name='process 1', stages=['NEW', 'INPROGESS', 'FINISHED'], input_data=data)
    result = wf_exec('process 1', ['NEW', 'INPROGESS', 'FINISHED'], data)
    logger.info("Workflow execution completed", result=result)
