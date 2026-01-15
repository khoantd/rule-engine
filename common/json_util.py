# from asyncio.windows_events import NULL
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
from jsonpath_ng import jsonpath, parse
from jsonpath_ng.exceptions import JSONPathError
from common.logger import get_logger
from common.exceptions import ConfigurationError
from common.security import validate_file_path, sanitize_filename, get_secure_file_permissions

logger = get_logger(__name__)


def parse_json(
    path_pattern: str, 
    json_data: Union[Dict[str, Any], List[Any], None]
) -> str:
    """
    Parse JSON data using JSONPath expression (legacy function with default value handling).
    
    This is a legacy function that provides special handling for change type fields.
    For new code, prefer parse_json_v2 which has more consistent behavior.
    
    Args:
        path_pattern: JSONPath expression to match (e.g., "$.fields[*].customfield_13805[*].value").
            Must be a valid JSONPath expression string.
        json_data: JSON data to parse. Can be a dictionary, list, or None.
            If None, returns "Not Available".
    
    Returns:
        Parsed value as string, or "Not Available" if:
            - path_pattern not found
            - json_data is None
            - value is 0 for specific change type fields (customfield_13805, customfield_13806, customfield_13807)
    
    Raises:
        ConfigurationError: If JSONPath expression is invalid or parsing fails
        
    Example:
        >>> data = {'fields': {'customfield_13805': [{'value': 'Test'}]}}
        >>> parse_json('$.fields[*].customfield_13805[*].value', data)
        'Test'
        >>> parse_json('$.nonexistent', data)
        'Not Available'
    """
    logger.debug("Parsing JSON with jsonpath", path_pattern=path_pattern)
    
    if json_data is None:
        logger.warning("JSON data is None, using default value", path_pattern=path_pattern)
        return "Not Available"
    
    gotdata = "Not Available"
    change_type_field_array = [
        "$.fields[*].customfield_13805[*].value",
        "$.fields[*].customfield_13806[*].value",
        "$.fields[*].customfield_13807[*].value"
    ]
    
    try:
        # Validate path_pattern is not empty
        if not path_pattern or not isinstance(path_pattern, str):
            logger.error("Invalid JSONPath pattern", path_pattern=path_pattern)
            raise ConfigurationError(
                f"Invalid JSONPath pattern: {path_pattern}",
                error_code="INVALID_JSONPATH_PATTERN",
                context={'path_pattern': path_pattern}
            )
        
        status_jsonpath_expr = parse(path_pattern)
        value = status_jsonpath_expr.find(json_data)
        
        if not value or len(value) == 0:
            logger.debug("JSON path not found", path_pattern=path_pattern)
            if path_pattern in change_type_field_array:
                gotdata = "Not Available"
            return gotdata
        
        gotdata = value[0].value
        
        # Handle special case for change type fields
        if path_pattern in change_type_field_array and gotdata == 0:
            gotdata = "Not Available"
            logger.debug("Using default value for change type field", path_pattern=path_pattern)
        else:
            logger.debug("JSON path parsed successfully", path_pattern=path_pattern, 
                        value=gotdata, value_type=type(gotdata).__name__)
        
        return gotdata
        
    except JSONPathError as e:
        logger.error("Invalid JSONPath expression", path_pattern=path_pattern, 
                    error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Invalid JSONPath expression '{path_pattern}': {str(e)}",
            error_code="JSONPATH_ERROR",
            context={'path_pattern': path_pattern, 'error': str(e)}
        ) from e
    except IndexError:
        logger.debug("JSON path not found", path_pattern=path_pattern)
        if path_pattern in change_type_field_array:
            gotdata = "Not Available"
        return gotdata
    except Exception as e:
        logger.error("Unexpected error parsing JSON", path_pattern=path_pattern, 
                    error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Unexpected error parsing JSON with path '{path_pattern}': {str(e)}",
            error_code="JSON_PARSE_ERROR",
            context={'path_pattern': path_pattern, 'error': str(e)}
        ) from e


def json_to_row_data_convert(
    pasring_path_file: str, 
    data: List[Dict[str, Any]]
) -> List[List[Any]]:
    """
    Convert JSON data to row format using parsing paths from a configuration file.
    
    This function reads parsing paths from a JSON file and applies each path
    to each record in the input data to create a tabular row structure.
    
    Args:
        pasring_path_file: Path to JSON file containing parsing path mappings.
            File should contain a dictionary mapping field names to JSONPath expressions.
        data: List of record dictionaries to convert. Each record will be converted
            to a row by applying all parsing paths.
    
    Returns:
        List of rows, where each row is a list of values extracted using parsing paths.
        Each row corresponds to one record from the input data.
    
    Raises:
        ConfigurationError: If parsing path file cannot be read or JSON is invalid
        
    Example:
        >>> paths = {'field1': '$.field1', 'field2': '$.field2'}
        >>> # Assuming paths are saved in file
        >>> data = [{'field1': 'value1', 'field2': 'value2'}]
        >>> rows = json_to_row_data_convert('paths.json', data)
        >>> rows[0]
        ['value1', 'value2']
    """
    parsing_path_data = read_json_file(pasring_path_file)
    rows: List[List[Any]] = []
    for rec in data:
        row: List[Any] = []
        for json_path_item in parsing_path_data:
            row.append(parse_json_v2(parsing_path_data[json_path_item], rec))
        rows.append(row)
    return rows


def parse_json_v2(
    path_pattern: str, 
    json_data: Union[Dict[str, Any], List[Any], None]
) -> Union[Any, int]:
    """
    Parse JSON data using JSONPath expression.
    
    This is the recommended function for JSONPath parsing. It returns the actual
    value found or 0 (zero) if the path is not found (unlike parse_json which
    returns "Not Available").
    
    Args:
        path_pattern: JSONPath expression to match (e.g., "$.rules_set").
            Must be a valid JSONPath expression string.
        json_data: JSON data to parse. Can be a dictionary, list, or None.
            If None, returns 0.
    
    Returns:
        Parsed value of any type (str, int, float, dict, list, etc.) if found,
        or 0 (integer zero) if path not found or json_data is None.
    
    Raises:
        ConfigurationError: If JSONPath expression is invalid or parsing fails
        
    Note:
        The return type is Union[Any, int] because the function can return
        any JSON-serializable type when successful, or 0 when not found.
        Callers should check the return value type if needed.
        
    Example:
        >>> data = {'rules_set': [{'name': 'Rule1'}]}
        >>> parse_json_v2('$.rules_set', data)
        [{'name': 'Rule1'}]
        >>> parse_json_v2('$.nonexistent', data)
        0
    """
    logger.debug("Parsing JSON with jsonpath", path_pattern=path_pattern)
    
    if json_data is None:
        logger.warning("JSON data is None, using default value", path_pattern=path_pattern)
        return 0
    
    try:
        # Validate path_pattern is not empty
        if not path_pattern or not isinstance(path_pattern, str):
            logger.error("Invalid JSONPath pattern", path_pattern=path_pattern)
            raise ConfigurationError(
                f"Invalid JSONPath pattern: {path_pattern}",
                error_code="INVALID_JSONPATH_PATTERN",
                context={'path_pattern': path_pattern}
            )
        
        status_jsonpath_expr = parse(path_pattern)
        value = status_jsonpath_expr.find(json_data)
        
        if not value or len(value) == 0:
            logger.debug("JSON path not found, using default value", path_pattern=path_pattern)
            return 0
        
        gotdata = value[0].value
        logger.debug("JSON path parsed successfully", path_pattern=path_pattern, 
                    value_type=type(gotdata).__name__)
        return gotdata
        
    except JSONPathError as e:
        logger.error("Invalid JSONPath expression", path_pattern=path_pattern, 
                    error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Invalid JSONPath expression '{path_pattern}': {str(e)}",
            error_code="JSONPATH_ERROR",
            context={'path_pattern': path_pattern, 'error': str(e)}
        ) from e
    except IndexError:
        logger.debug("JSON path not found, using default value", path_pattern=path_pattern)
        return 0
    except Exception as e:
        logger.error("Unexpected error parsing JSON", path_pattern=path_pattern, 
                    error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Unexpected error parsing JSON with path '{path_pattern}': {str(e)}",
            error_code="JSON_PARSE_ERROR",
            context={'path_pattern': path_pattern, 'error': str(e)}
        ) from e


def read_json_file(file_path: str, allowed_base: Optional[str] = None) -> Union[Dict[str, Any], List[Any]]:
    """
    Read and parse a JSON file securely.
    
    This function safely reads a JSON file and parses its contents. It uses
    context managers for file handling, validates paths to prevent directory
    traversal attacks, and provides comprehensive error handling.
    
    Args:
        file_path: Path to the JSON file to read. Can be relative or absolute path.
            File must exist and be readable.
        allowed_base: Optional base directory that the path must be within.
            If None, only validates against directory traversal attacks.
            This prevents accessing files outside the intended directory.
    
    Returns:
        Parsed JSON data as dictionary or list depending on file contents.
        The root JSON element can be either an object (dict) or array (list).
    
    Raises:
        SecurityError: If path contains directory traversal or is outside allowed base
        ConfigurationError: If:
            - File not found (FileNotFoundError)
            - JSON is invalid or malformed (JSONDecodeError)
            - File cannot be read (permission errors, etc.)
            - Any other unexpected error occurs
    
    Example:
        >>> data = read_json_file('data/input/rules_config.json', allowed_base='data')
        >>> isinstance(data, dict)
        True
        >>> 'rules_set' in data
        True
    """
    logger.info("Reading JSON file", file_path=file_path, allowed_base=allowed_base)
    
    # Validate path to prevent directory traversal
    try:
        validated_path = validate_file_path(file_path, allowed_base=allowed_base, must_exist=True)
        file_path = str(validated_path)
    except Exception as e:
        # Re-raise security errors as-is
        raise
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info("JSON file read successfully", file_path=file_path, 
                   data_keys=list(data.keys()) if isinstance(data, dict) else [])
        return data
    except FileNotFoundError:
        logger.error("JSON file not found", file_path=file_path, exc_info=True)
        raise ConfigurationError(
            f"Config file not found: {file_path}",
            error_code="FILE_NOT_FOUND",
            context={'file_path': file_path}
        )
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in file", file_path=file_path, error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Invalid JSON in {file_path}: {e}",
            error_code="INVALID_JSON",
            context={'file_path': file_path, 'error': str(e)}
        ) from e
    except PermissionError as e:
        logger.error("Permission denied reading file", file_path=file_path, exc_info=True)
        raise ConfigurationError(
            f"Permission denied reading file {file_path}: {str(e)}",
            error_code="PERMISSION_DENIED",
            context={'file_path': file_path, 'error': str(e)}
        ) from e
    except Exception as e:
        logger.error("Unexpected error reading JSON file", file_path=file_path, error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Failed to read JSON file {file_path}: {str(e)}",
            error_code="FILE_READ_ERROR",
            context={'file_path': file_path, 'error': str(e)}
        ) from e


def create_json_file(
    json_string: Union[Dict[str, Any], List[Any], str], 
    file_name: str,
    output_dir: str = "data",
    is_sensitive: bool = False
) -> None:
    """
    Create a JSON file from JSON-serializable data securely.
    
    This function serializes the input data to JSON format and writes it to a file.
    It includes special handling for malformed JSON strings by replacing '][' with ','.
    The function validates paths to prevent directory traversal attacks and sets
    appropriate file permissions.
    
    Args:
        json_string: Data to serialize to JSON. Can be:
            - Dictionary (dict)
            - List (list)
            - String containing JSON (will be serialized again)
        file_name: Name of the output file. Will be sanitized to prevent path injection.
            Example: "output.json" will create "data/output.json"
        output_dir: Output directory (default: "data"). Must be relative and safe.
        is_sensitive: If True, sets restrictive file permissions (owner-only read/write)
    
    Returns:
        None
    
    Raises:
        SecurityError: If path contains directory traversal or is outside allowed base
        ConfigurationError: If:
            - File cannot be created or written
            - Data cannot be serialized to JSON
            - Any other error occurs during file writing
    
    Note:
        The function performs a special string replacement ('][' -> ',') on the
        serialized JSON string before writing, which suggests handling of
        malformed JSON from legacy systems.
        
    Example:
        >>> data = {'key': 'value'}
        >>> create_json_file(data, 'output.json')
        >>> # File created at data/output.json
    """
    logger.info("Creating JSON file", file_name=file_name, output_dir=output_dir, 
               is_sensitive=is_sensitive)
    
    try:
        # Sanitize filename to prevent path injection
        safe_filename = sanitize_filename(file_name)
        if safe_filename != file_name:
            logger.warning("Filename sanitized", original=file_name, sanitized=safe_filename)
        
        # Build and validate path
        file_path = os.path.join(output_dir, safe_filename)
        
        # Validate path to prevent directory traversal
        validated_path = validate_file_path(file_path, allowed_base=output_dir, must_exist=False)
        file_path = str(validated_path)
        
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Serialize JSON
        json_object = json.dumps(json_string, ensure_ascii=False, indent=4)
        
        # Get secure file permissions
        file_mode = get_secure_file_permissions(is_sensitive=is_sensitive)
        
        # Write file with secure permissions
        with open(file_path, "w") as outfile:
            outfile.write(json_object.replace('][', ','))
        
        # Set file permissions (Unix only, will fail silently on Windows)
        try:
            os.chmod(file_path, file_mode)
            logger.debug("File permissions set", file_path=file_path, mode=oct(file_mode))
        except (OSError, NotImplementedError):
            # Windows doesn't support chmod in the same way
            logger.debug("File permissions not set (platform limitation)", file_path=file_path)
        
        logger.info("JSON file created successfully", file_name=file_name, file_path=file_path)
    except SecurityError:
        # Re-raise security errors as-is
        raise
    except json.JSONEncodeError as e:
        logger.error("Failed to serialize JSON", error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Failed to serialize JSON data: {str(e)}",
            error_code="JSON_SERIALIZATION_ERROR",
            context={'error': str(e)}
        ) from e
    except PermissionError as e:
        logger.error("Permission denied writing file", file_path=file_path, exc_info=True)
        raise ConfigurationError(
            f"Permission denied writing file {file_path}: {str(e)}",
            error_code="PERMISSION_DENIED",
            context={'file_path': file_path, 'error': str(e)}
        ) from e
    except Exception as e:
        logger.error("Failed to create JSON file", file_name=file_name, error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Failed to create JSON file {file_name}: {str(e)}",
            error_code="FILE_WRITE_ERROR",
            context={'file_name': file_name, 'error': str(e)}
        ) from e


if __name__ == "__main__":
    json_object = read_json_file(
        "cr_type_update/data/input/parsing_paths_v2.json")
    # json_data = json.loads(json_object)
