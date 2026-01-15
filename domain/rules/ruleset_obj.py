from domain.jsonobj import JsonObject


class RuleSet(JsonObject):
    def __init__(self, ruleset_name: str, rules: list, actionset: list):
        super()
        self.__ruleset_name = ruleset_name
        self.__rules = rules
        self.__actionset = actionset
        # self.__json_obj = self.json_obj_print()

    @property
    def rulesetname(self):
        return self.__ruleset_name

    @rulesetname.setter
    def rulesetname(self, rulesetname):
        self.__json_obj["rulesetname"] = rulesetname
        self.__ruleset_name = rulesetname

    @property
    def rules(self):
        return self.__rules

    @rules.setter
    def rules(self, rules):
        self.__json_obj["rules"] = rules
        self.__rules = rules

    @property
    def actionset(self):
        return self.__actionset

    @actionset.setter
    def actionset(self, actionset):
        self.__json_obj["actionset"] = actionset
        self.__actionset = actionset
