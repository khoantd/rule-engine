"""Unit tests for condition operator name mapping."""

import pytest

from common.conditions_enum import equation_operators, logical_operators


@pytest.mark.unit
def test_equation_operators_regex_aliases() -> None:
    assert equation_operators("regex_match") == "=~"
    assert equation_operators("regex_search") == "=~~"
    assert equation_operators("regex_not_match") == "!~"
    assert equation_operators("regex_not_search") == "!~~"
    assert equation_operators("regex") == "=~~"


@pytest.mark.unit
def test_equation_operators_unknown_returns_nothing() -> None:
    assert equation_operators("unknown_op") == "nothing"


@pytest.mark.unit
def test_logical_operators_and_or_aliases() -> None:
    assert logical_operators("inclusive") == "and"
    assert logical_operators("exclusive") == "or"
    assert logical_operators("AND") == "and"
