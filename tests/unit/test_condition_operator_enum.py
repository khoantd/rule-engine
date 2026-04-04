"""Unit tests for ConditionOperator vs equation_operators names."""

import pytest

from common.db_models import ConditionOperator


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "regex_match",
        "regex_search",
        "regex_not_match",
        "regex_not_search",
    ],
)
def test_condition_operator_accepts_explicit_regex_equations(value: str) -> None:
    """DB/API equation strings must match enum values used by equation_operators."""
    assert ConditionOperator(value).value == value
