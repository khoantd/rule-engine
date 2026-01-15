from domain.jsonobj import JsonObject


class Action(JsonObject):
    def __init__(self, pattern: str, message: str):
        super.__init__()
        self.__pattern = pattern
        self.__message = message
        self.__json_obj = self.json_obj_print()

    @property
    def pattern(self):
        return self.__pattern

    @pattern.setter
    def pattern(self, pattern):
        self.__json_obj["pattern"] = pattern
        self.__pattern = pattern

    @property
    def message(self):
        return self.__message

    @message.setter
    def message(self, message):
        self.__json_obj["message"] = message
        self.__message = message
