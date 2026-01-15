from typing import Any, Dict, List, Union
from domain.jsonobj import JsonObject
from domain.actions.action_obj import Action


class Rule(JsonObject):
    """
    Base rule class representing a rule with conditions and results.
    
    This class represents a basic rule that can be evaluated against data.
    It includes an ID, name, description, conditions, and result.
    
    Attributes:
        id: Unique identifier for the rule
        rulename: Human-readable name of the rule
        description: Description of what the rule does
        conditions: List or dictionary of conditions to evaluate
        result: Result string returned when rule matches
    """
    
    def __init__(
        self, 
        id: str, 
        rule_name: str, 
        conditions: Union[List[Any], Dict[str, Any]], 
        description: str, 
        result: str
    ) -> None:
        """
        Initialize a Rule object.
        
        Args:
            id: Unique identifier for the rule
            rule_name: Human-readable name of the rule
            conditions: Conditions to evaluate. Can be a list or dictionary.
            description: Description of what the rule does
            result: Result string returned when rule matches
        """
        super().__init__()
        self.__id: str = id
        self.__rulename: str = rule_name
        self.__description: str = description
        self.__conditions: Union[List[Any], Dict[str, Any]] = conditions
        self.__result: str = result
        self._json_obj = self.json_obj_print()

    @property
    def id(self) -> str:
        """
        Get the rule's unique identifier.
        
        Returns:
            Rule ID string.
        """
        return self.__id

    @id.setter
    def id(self, id: str) -> None:
        """
        Set the rule's unique identifier.
        
        Args:
            id: New rule ID string.
        """
        self._json_obj["id"] = id
        self.__id = id

    @property
    def rulename(self) -> str:
        """
        Get the rule's name.
        
        Returns:
            Rule name string.
        """
        return self.__rulename

    @rulename.setter
    def rulename(self, rulename: str) -> None:
        """
        Set the rule's name.
        
        Args:
            rulename: New rule name string.
        """
        self._json_obj["rulename"] = rulename
        self.__rulename = rulename

    @property
    def description(self) -> str:
        """
        Get the rule's description.
        
        Returns:
            Rule description string.
        """
        return self.__description

    @description.setter
    def description(self, description: str) -> None:
        """
        Set the rule's description.
        
        Args:
            description: New rule description string.
        """
        self._json_obj["description"] = description
        self.__description = description

    @property
    def conditions(self) -> Union[List[Any], Dict[str, Any]]:
        """
        Get the rule's conditions.
        
        Returns:
            Conditions as list or dictionary depending on rule type.
        """
        return self.__conditions

    @conditions.setter
    def conditions(self, conditions: Union[List[Any], Dict[str, Any]]) -> None:
        """
        Set the rule's conditions.
        
        Args:
            conditions: New conditions as list or dictionary.
        """
        self._json_obj["conditions"] = conditions
        self.__conditions = conditions

    @property
    def result(self) -> str:
        """
        Get the rule's result string.
        
        Returns:
            Result string returned when rule matches.
        """
        return self.__result

    @result.setter
    def result(self, result: str) -> None:
        """
        Set the rule's result string.
        
        Args:
            result: New result string.
        """
        self._json_obj["result"] = result
        self.__result = result

    def get_json_data(self) -> Dict[str, Any]:
        """
        Get the JSON dictionary representation of this rule.
        
        Returns:
            Dictionary containing all rule data in JSON-serializable format.
            
        Example:
            >>> rule = Rule('rule1', 'Rule1', [], 'Test rule', 'APPROVE')
            >>> data = rule.get_json_data()
            >>> data['id']
            'rule1'
        """
        return self._json_obj


class ExtRule(Rule):
    """
    Extended rule class with additional execution metadata.
    
    This class extends the base Rule class with additional properties needed
    for rule execution: rule points, weight, priority, rule type, and action result.
    
    Attributes:
        rulepoint: Points awarded when rule matches (float)
        weight: Weight multiplier for rule points (float)
        priority: Execution priority (lower numbers execute first) (int)
        type: Rule type - 'simple' or 'complex' (str)
        action_result: Action string returned when rule matches (str)
    """
    
    def __init__(
        self, 
        id: str, 
        rule_name: str, 
        conditions: Union[List[Any], Dict[str, Any]], 
        description: str, 
        result: str, 
        rule_point: float, 
        weight: float, 
        priority: int, 
        type: str, 
        action_result: str
    ) -> None:
        """
        Initialize an ExtRule object.
        
        Args:
            id: Unique identifier for the rule
            rule_name: Human-readable name of the rule
            conditions: Conditions to evaluate. Can be a list or dictionary.
            description: Description of what the rule does
            result: Result string returned when rule matches
            rule_point: Points awarded when rule matches
            weight: Weight multiplier for rule points
            priority: Execution priority (lower numbers = higher priority)
            type: Rule type - must be 'simple' or 'complex'
            action_result: Action string returned when rule matches
        """
        super().__init__(id, rule_name, conditions, description, result)
        self.__rule_point: float = rule_point
        self.__weight: float = weight
        self.__priority: int = priority
        self.__conditions: Union[List[Any], Dict[str, Any]] = conditions
        self.__type: str = type
        self.__action_result: str = action_result

    @property
    def rulepoint(self) -> float:
        """
        Get the rule's point value.
        
        Returns:
            Points awarded when rule matches.
        """
        return self.__rule_point

    @rulepoint.setter
    def rulepoint(self, rule_point: float) -> None:
        """
        Set the rule's point value.
        
        Args:
            rule_point: New rule point value.
        """
        self._json_obj["rule_point"] = rule_point
        self.__rule_point = rule_point

    @property
    def conditions(self) -> Union[List[Any], Dict[str, Any]]:
        """
        Get the rule's conditions (overridden from base class).
        
        Returns:
            Conditions as list or dictionary depending on rule type.
        """
        return self.__conditions

    @conditions.setter
    def conditions(self, conditions: Union[List[Any], Dict[str, Any]]) -> None:
        """
        Set the rule's conditions (overridden from base class).
        
        Args:
            conditions: New conditions as list or dictionary.
        """
        self._json_obj["conditions"] = conditions
        self.__conditions = conditions

    @property
    def weight(self) -> float:
        """
        Get the rule's weight multiplier.
        
        Returns:
            Weight multiplier for rule points.
        """
        return self.__weight

    @weight.setter
    def weight(self, weight: float) -> None:
        """
        Set the rule's weight multiplier.
        
        Args:
            weight: New rule weight value.
        """
        self._json_obj["weight"] = weight
        self.__weight = weight

    @property
    def priority(self) -> int:
        """
        Get the rule's execution priority.
        
        Returns:
            Priority value (lower numbers = higher priority).
        """
        return self.__priority

    @priority.setter
    def priority(self, priority: int) -> None:
        """
        Set the rule's execution priority.
        
        Args:
            priority: New priority value (lower numbers = higher priority).
        """
        self._json_obj["priority"] = priority
        self.__priority = priority
        
    @property
    def type(self) -> str:
        """
        Get the rule's type.
        
        Returns:
            Rule type - 'simple' or 'complex'.
        """
        return self.__type

    @type.setter
    def type(self, type: str) -> None:
        """
        Set the rule's type.
        
        Args:
            type: New rule type - must be 'simple' or 'complex'.
        """
        self._json_obj["type"] = type
        self.__type = type
        
    @property
    def action_result(self) -> str:
        """
        Get the rule's action result string.
        
        Returns:
            Action string returned when rule matches.
        """
        return self.__action_result

    @action_result.setter
    def action_result(self, action_result: str) -> None:
        """
        Set the rule's action result string.
        
        Args:
            action_result: New action result string.
        """
        self._json_obj["action_result"] = action_result
        self.__action_result = action_result
