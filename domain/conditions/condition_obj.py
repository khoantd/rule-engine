from typing import Any, Dict
from domain.jsonobj import JsonObject


class Condition(JsonObject):
    """
    Condition class representing a single evaluation condition.
    
    A condition defines how to evaluate a single attribute against a constant
    value using a specific equation operator (e.g., ==, >, <).
    
    Attributes:
        condition_id: Unique identifier for the condition
        condition_name: Human-readable name of the condition
        attribute: Field/attribute name to check
        equation: Equation operator (e.g., '==', '>', '<')
        constant: Comparison value
    """
    
    def __init__(
        self,
        condition_id: str, 
        condition_name: str, 
        attribute: str, 
        equation: str, 
        constant: str
    ) -> None:
        """
        Initialize a Condition object.
        
        Args:
            condition_id: Unique identifier for the condition
            condition_name: Human-readable name of the condition
            attribute: Field/attribute name to check
            equation: Equation operator (e.g., '==', '>', '<', '!=')
            constant: Comparison value (string or number as string)
        """
        super().__init__()
        self.__condition_id: str = condition_id
        self.__condition_name: str = condition_name
        self.__attribute: str = attribute
        self.__equation: str = equation
        self.__constant: str = constant
        self.__json_obj: Dict[str, Any] = self.json_obj_print()

    @property
    def condition_id(self) -> str:
        """
        Get the condition's unique identifier.
        
        Returns:
            Condition ID string.
        """
        return self.__condition_id

    @condition_id.setter
    def condition_id(self, condition_id: str) -> None:
        """
        Set the condition's unique identifier.
        
        Args:
            condition_id: New condition ID string.
        """
        self.__json_obj["condition_id"] = condition_id
        self.__condition_id = condition_id

    @property
    def condition_name(self) -> str:
        """
        Get the condition's name.
        
        Returns:
            Condition name string.
        """
        return self.__condition_name

    @condition_name.setter
    def condition_name(self, condition_name: str) -> None:
        """
        Set the condition's name.
        
        Args:
            condition_name: New condition name string.
        """
        self.__json_obj["condition_name"] = condition_name
        self.__condition_name = condition_name

    @property
    def attribute(self) -> str:
        """
        Get the condition's attribute name.
        
        Returns:
            Attribute name string to check.
        """
        return self.__attribute

    @attribute.setter
    def attribute(self, attribute: str) -> None:
        """
        Set the condition's attribute name.
        
        Args:
            attribute: New attribute name string.
        """
        self.__json_obj["attribute"] = attribute
        self.__attribute = attribute

    @property
    def equation(self) -> str:
        """
        Get the condition's equation operator.
        
        Returns:
            Equation operator string (e.g., '==', '>', '<').
        """
        return self.__equation

    @equation.setter
    def equation(self, equation: str) -> None:
        """
        Set the condition's equation operator.
        
        Args:
            equation: New equation operator string (e.g., '==', '>', '<').
        """
        self.__json_obj["equation"] = equation
        self.__equation = equation

    @property
    def constant(self) -> str:
        """
        Get the condition's constant value.
        
        Returns:
            Constant value string for comparison.
        """
        return self.__constant

    @constant.setter
    def constant(self, constant: str) -> None:
        """
        Set the condition's constant value.
        
        Args:
            constant: New constant value string for comparison.
        """
        self.__json_obj["constant"] = constant
        self.__constant = constant
