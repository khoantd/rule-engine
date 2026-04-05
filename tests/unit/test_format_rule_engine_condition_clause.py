"""Tests for compiling DB/API conditions into rule_engine.Rule text."""

import pytest

from common.exceptions import RuleCompilationError
from common.rule_engine_util import (
    _rule_engine_string_operand,
    condition_setup,
    format_rule_engine_condition_clause,
)


@pytest.mark.unit
def test_format_contains_produces_substring_in_expression() -> None:
    text = format_rule_engine_condition_clause("email", "contains", "@gmail", rule_name="t")
    assert text == '"@gmail" in email'


@pytest.mark.unit
def test_format_in_membership_expression() -> None:
    text = format_rule_engine_condition_clause(
        "email", "in", '["a@x.com", "khoa0702@gmail.com"]', rule_name="t"
    )
    assert text == 'email in ["a@x.com", "khoa0702@gmail.com"]'


@pytest.mark.unit
def test_format_not_in_membership_expression() -> None:
    text = format_rule_engine_condition_clause(
        "email", "not_in", '["blocked@x.com"]', rule_name="t"
    )
    assert text == 'not (email in ["blocked@x.com"])'


@pytest.mark.unit
def test_format_unsupported_operator_raises() -> None:
    with pytest.raises(RuleCompilationError) as exc:
        format_rule_engine_condition_clause("x", "bogus_op", "1", rule_name="r1")
    assert exc.value.error_code == "CONDITION_OPERATOR_UNSUPPORTED"


@pytest.mark.unit
def test_condition_setup_delegates_to_formatter() -> None:
    rule = {
        "attribute": "email",
        "condition": "contains",
        "constant": ".edu",
        "rule_name": "edu-leads",
    }
    text = condition_setup(rule)
    assert text == '".edu" in email'


@pytest.mark.unit
def test_format_contains_empty_attribute_raises() -> None:
    with pytest.raises(RuleCompilationError) as exc:
        format_rule_engine_condition_clause("  ", "contains", "x", rule_name="r")
    assert exc.value.error_code == "CONDITION_EMPTY"


@pytest.mark.unit
def test_format_equal_quotes_string_constant() -> None:
    # API passes bare string "open"; _rule_engine_string_operand must wrap it in quotes
    # so the rule engine treats it as a string literal, not a symbol reference.
    text = format_rule_engine_condition_clause("status", "equal", "open", rule_name="r")
    assert text == 'status == "open"'


@pytest.mark.unit
def test_format_equal_already_quoted_constant_passthrough() -> None:
    # If the caller already quotes the constant (e.g. from legacy storage), it passes through.
    text = format_rule_engine_condition_clause("status", "equal", '"open"', rule_name="r")
    assert text == 'status == "open"'


@pytest.mark.unit
def test_format_greater_than_numeric_constant() -> None:
    text = format_rule_engine_condition_clause("issue", "greater_than", "30", rule_name="r")
    assert text == "issue > 30"


@pytest.mark.unit
def test_format_less_than_numeric_constant() -> None:
    text = format_rule_engine_condition_clause("score", "less_than", "100", rule_name="r")
    assert text == "score < 100"


@pytest.mark.unit
def test_format_regex_quotes_pattern_with_caret() -> None:
    """Unquoted ^ in pattern must not be parsed as BWXOR (RuleSyntaxError)."""
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    text = format_rule_engine_condition_clause(
        "email", "regex_match", pattern, rule_name="Valid Email"
    )
    assert text == "email =~ {}".format(_rule_engine_string_operand(pattern))


@pytest.mark.unit
def test_format_regex_search_alias_quotes_rhs() -> None:
    text = format_rule_engine_condition_clause("email", "regex", ".*@gmail.com$", rule_name="r")
    assert text == 'email =~~ ".*@gmail.com$"'
