
def equation_operators(argument):
    switcher = {
        "equal": "==",
        "greater_than": ">",
        "greater_than_or_equal": ">=",
        "less_than": "<",
        "less_than_or_equal": "<=",
        "range": "in",
        "not_equal": "!="
    }
    return switcher.get(argument, "nothing")

def logical_operators(argument):
    switcher = {
        "exclusive": "or",
        "inclusive": "and"
    }
    return switcher.get(argument, "nothing")