from typing import Any, Dict


class JsonObject:
    """
    Base class for JSON-serializable objects.
    
    This class provides a foundation for objects that need to be serialized
    to JSON format. It maintains an internal JSON dictionary representation
    that can be accessed and modified.
    
    Attributes:
        _json_obj: Internal dictionary representation of the object's JSON data.
    """
    
    def __init__(self) -> None:
        """
        Initialize JsonObject with empty JSON dictionary.
        """
        self._json_obj: Dict[str, Any] = {}

    def json_obj_print(self) -> Dict[str, Any]:
        """
        Get the JSON dictionary representation of this object.
        
        Returns:
            Dictionary containing the object's JSON-serializable data.
            
        Example:
            >>> obj = JsonObject()
            >>> obj.set_json_data({'key': 'value'})
            >>> obj.json_obj_print()
            {'key': 'value'}
        """
        return self._json_obj

    def set_json_data(self, json_data: Dict[str, Any]) -> None:
        """
        Set the JSON dictionary representation of this object.
        
        Args:
            json_data: Dictionary containing JSON-serializable data.
                This replaces the existing _json_obj dictionary.
                
        Example:
            >>> obj = JsonObject()
            >>> obj.set_json_data({'key': 'value'})
            >>> obj.json_obj_print()
            {'key': 'value'}
        """
        self._json_obj = json_data
