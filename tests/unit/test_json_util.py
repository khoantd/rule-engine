"""
Unit tests for common.json_util module.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, Any

from common.json_util import (
    read_json_file,
    parse_json,
    parse_json_v2,
    create_json_file
)
from common.exceptions import ConfigurationError, SecurityError


class TestReadJsonFile:
    """Tests for read_json_file function."""
    
    def test_read_json_file_success(self, temp_config_file):
        """Test successfully reading a JSON file."""
        result = read_json_file(str(temp_config_file))
        assert isinstance(result, dict)
        assert "rules_set" in result
    
    def test_read_json_file_not_found(self):
        """Test reading non-existent file raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            read_json_file("nonexistent.json")
        
        assert exc_info.value.error_code == "FILE_NOT_FOUND"
    
    @patch('builtins.open', mock_open(read_data='{"invalid": json}'))
    def test_read_json_file_invalid_json(self):
        """Test reading invalid JSON raises ConfigurationError."""
        with patch('common.json_util.validate_file_path', return_value=Path("test.json")):
            with pytest.raises(ConfigurationError) as exc_info:
                read_json_file("test.json")
            
            assert exc_info.value.error_code == "INVALID_JSON"
    
    def test_read_json_file_list_root(self, tmp_path):
        """Test reading JSON file with list as root."""
        json_file = tmp_path / "list.json"
        json_data = [1, 2, 3]
        with open(json_file, 'w') as f:
            json.dump(json_data, f)
        
        result = read_json_file(str(json_file), allowed_base=str(tmp_path))
        assert isinstance(result, list)
        assert result == [1, 2, 3]


class TestParseJson:
    """Tests for parse_json function."""
    
    def test_parse_json_success(self):
        """Test successfully parsing JSON with JSONPath."""
        data = {"fields": {"status": "open"}}
        result = parse_json("$.fields.status", data)
        assert result == "open"
    
    def test_parse_json_not_found(self):
        """Test parsing non-existent path returns default."""
        data = {"fields": {"status": "open"}}
        result = parse_json("$.fields.nonexistent", data)
        assert result == "Not Available"
    
    def test_parse_json_none_data(self):
        """Test parsing with None data returns default."""
        result = parse_json("$.fields.status", None)
        assert result == "Not Available"
    
    def test_parse_json_invalid_path(self):
        """Test parsing with invalid JSONPath raises ConfigurationError."""
        data = {"fields": {"status": "open"}}
        with pytest.raises(ConfigurationError) as exc_info:
            parse_json("invalid path", data)
        
        assert exc_info.value.error_code == "JSONPATH_ERROR"
    
    def test_parse_json_change_type_field_zero(self):
        """Test parsing change type field with value 0 returns default."""
        data = {"fields": {"customfield_13805": [{"value": 0}]}}
        path = "$.fields[*].customfield_13805[*].value"
        result = parse_json(path, data)
        assert result == "Not Available"
    
    def test_parse_json_empty_path_pattern(self):
        """Test parsing with empty path pattern raises ConfigurationError."""
        data = {"fields": {"status": "open"}}
        with pytest.raises(ConfigurationError) as exc_info:
            parse_json("", data)
        
        assert exc_info.value.error_code == "INVALID_JSONPATH_PATTERN"


class TestParseJsonV2:
    """Tests for parse_json_v2 function."""
    
    def test_parse_json_v2_success(self):
        """Test successfully parsing JSON with JSONPath."""
        data = {"rules_set": [{"name": "Rule1"}]}
        result = parse_json_v2("$.rules_set", data)
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_parse_json_v2_not_found(self):
        """Test parsing non-existent path returns 0."""
        data = {"fields": {"status": "open"}}
        result = parse_json_v2("$.fields.nonexistent", data)
        assert result == 0
    
    def test_parse_json_v2_none_data(self):
        """Test parsing with None data returns 0."""
        result = parse_json_v2("$.fields.status", None)
        assert result == 0
    
    def test_parse_json_v2_invalid_path(self):
        """Test parsing with invalid JSONPath raises ConfigurationError."""
        data = {"fields": {"status": "open"}}
        with pytest.raises(ConfigurationError) as exc_info:
            parse_json_v2("invalid path", data)
        
        assert exc_info.value.error_code == "JSONPATH_ERROR"
    
    def test_parse_json_v2_empty_path_pattern(self):
        """Test parsing with empty path pattern raises ConfigurationError."""
        data = {"fields": {"status": "open"}}
        with pytest.raises(ConfigurationError) as exc_info:
            parse_json_v2("", data)
        
        assert exc_info.value.error_code == "INVALID_JSONPATH_PATTERN"


class TestCreateJsonFile:
    """Tests for create_json_file function."""
    
    def test_create_json_file_success(self, tmp_path):
        """Test successfully creating a JSON file."""
        data = {"key": "value"}
        file_name = "test.json"
        output_dir = str(tmp_path)
        
        create_json_file(data, file_name, output_dir)
        
        # Verify file was created
        output_file = tmp_path / file_name
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            result = json.load(f)
        assert result == data
    
    def test_create_json_file_list_data(self, tmp_path):
        """Test creating JSON file with list data."""
        data = [1, 2, 3]
        create_json_file(data, "list.json", str(tmp_path))
        
        output_file = tmp_path / "list.json"
        with open(output_file, 'r') as f:
            result = json.load(f)
        assert result == [1, 2, 3]
    
    def test_create_json_file_string_data(self, tmp_path):
        """Test creating JSON file with string JSON data."""
        json_string = '{"key": "value"}'
        create_json_file(json_string, "string.json", str(tmp_path))
        
        output_file = tmp_path / "string.json"
        with open(output_file, 'r') as f:
            result = json.load(f)
        assert result == {"key": "value"}
    
    @patch('common.json_util.validate_file_path')
    def test_create_json_file_path_validation(self, mock_validate, tmp_path):
        """Test creating JSON file validates path."""
        mock_validate.side_effect = SecurityError("Path validation failed", error_code="PATH_ERROR")
        
        with pytest.raises(SecurityError):
            create_json_file({"key": "value"}, "test.json", str(tmp_path))
    
    def test_create_json_file_creates_directory(self, tmp_path):
        """Test creating JSON file creates directory if needed."""
        new_dir = tmp_path / "new_dir"
        assert not new_dir.exists()
        
        create_json_file({"key": "value"}, "test.json", str(new_dir))
        
        assert new_dir.exists()
        assert (new_dir / "test.json").exists()

