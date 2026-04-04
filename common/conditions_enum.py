def equation_operators(argument):
    switcher = {
        "equal": "==",
        "greater_than": ">",
        "greater_than_or_equal": ">=",
        "less_than": "<",
        "less_than_or_equal": "<=",
        "range": "in",
        "not_equal": "!=",
        # python rule_engine fuzzy regex ops (see rule_engine.parser op_names)
        "regex_match": "=~",
        "regex_search": "=~~",
        "regex_not_match": "!~",
        "regex_not_search": "!~~",
        # Alias for DB/API ConditionOperator.REGEX ("regex") — substring search
        "regex": "=~~",
    }
    return switcher.get(argument, "nothing")


def logical_operators(argument):
    """
    Map logical mode names to Python-style operators for compiled condition strings.

    Accepts inclusive/and and exclusive/or (case-insensitive when callers normalize).
    """
    switcher = {
        "exclusive": "or",
        "inclusive": "and",
        "or": "or",
        "and": "and",
    }
    if argument is None:
        return "nothing"
    key = str(argument).strip().lower()
    return switcher.get(key, "nothing")
