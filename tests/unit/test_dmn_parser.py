"""
Unit tests for DMN parser module.
"""

import pytest
import tempfile
import os
from pathlib import Path

from common.dmn_parser import DMNParser
from common.exceptions import ConfigurationError


class TestDMNParser:
    """Test suite for DMNParser class."""
    
    def test_parse_simple_dmn_file(self):
        """Test parsing a simple DMN file."""
        # Create a temporary DMN file
        dmn_content = '''<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 id="test" name="Test">
  <dmn:decision id="Decision1" name="Test Decision">
    <dmn:decisionTable id="Table1" hitPolicy="UNIQUE">
      <dmn:input id="Input1" label="Value">
        <dmn:inputExpression id="Expr1" typeRef="number">
          <feel:text>value</feel:text>
        </dmn:inputExpression>
      </dmn:input>
      <dmn:output id="Output1" label="Result" typeRef="string"/>
      <dmn:rule id="Rule1">
        <dmn:inputEntry id="Entry1">
          <feel:text>&gt; 10</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="Out1">
          <feel:text>"Approved"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
</dmn:definitions>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dmn', delete=False) as f:
            f.write(dmn_content)
            temp_path = f.name
        
        try:
            parser = DMNParser()
            result = parser.parse_file(temp_path)
            
            assert "rules_set" in result
            assert isinstance(result["rules_set"], list)
            assert len(result["rules_set"]) == 1
            
            rule = result["rules_set"][0]
            assert rule["id"] == "Decision1_R0001"
            assert rule["rule_name"] == "Test Decision - Rule 1"
            assert rule["attribute"] == "Value"
            assert rule["condition"] == "greater_than"
            assert rule["constant"] == "10"
            assert rule["action_result"] == "Approved"
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_dmn_with_multiple_rules(self):
        """Test parsing DMN file with multiple rules."""
        dmn_content = '''<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 id="test" name="Test">
  <dmn:decision id="Decision1" name="Test Decision">
    <dmn:decisionTable id="Table1" hitPolicy="UNIQUE">
      <dmn:input id="Input1" label="Score">
        <dmn:inputExpression id="Expr1" typeRef="number">
          <feel:text>score</feel:text>
        </dmn:inputExpression>
      </dmn:input>
      <dmn:output id="Output1" label="Grade" typeRef="string"/>
      <dmn:rule id="Rule1">
        <dmn:inputEntry id="Entry1">
          <feel:text>&gt;= 90</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="Out1">
          <feel:text>"A"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
      <dmn:rule id="Rule2">
        <dmn:inputEntry id="Entry2">
          <feel:text>&gt;= 80</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="Out2">
          <feel:text>"B"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
</dmn:definitions>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dmn', delete=False) as f:
            f.write(dmn_content)
            temp_path = f.name
        
        try:
            parser = DMNParser()
            result = parser.parse_file(temp_path)
            
            assert len(result["rules_set"]) == 2
            
            rule1 = result["rules_set"][0]
            assert rule1["id"] == "Decision1_R0001"
            assert rule1["condition"] == "greater_than_or_equal"
            assert rule1["constant"] == "90"
            assert rule1["action_result"] == "A"
            assert rule1["priority"] == 1
            
            rule2 = result["rules_set"][1]
            assert rule2["id"] == "Decision1_R0002"
            assert rule2["condition"] == "greater_than_or_equal"
            assert rule2["constant"] == "80"
            assert rule2["action_result"] == "B"
            assert rule2["priority"] == 2
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_dmn_content_string(self):
        """Test parsing DMN content from string."""
        dmn_content = '''<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 id="test" name="Test">
  <dmn:decision id="Decision1" name="Test Decision">
    <dmn:decisionTable id="Table1" hitPolicy="UNIQUE">
      <dmn:input id="Input1" label="Status">
        <dmn:inputExpression id="Expr1" typeRef="string">
          <feel:text>status</feel:text>
        </dmn:inputExpression>
      </dmn:input>
      <dmn:output id="Output1" label="Action" typeRef="string"/>
      <dmn:rule id="Rule1">
        <dmn:inputEntry id="Entry1">
          <feel:text>"active"</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="Out1">
          <feel:text>"Process"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
</dmn:definitions>'''
        
        parser = DMNParser()
        result = parser.parse_content(dmn_content)
        
        assert "rules_set" in result
        assert len(result["rules_set"]) == 1
        
        rule = result["rules_set"][0]
        assert rule["condition"] == "equal"
        assert rule["constant"] == '"active"'
        assert rule["action_result"] == "Process"
    
    def test_parse_feel_expressions(self):
        """Test FEEL expression parsing."""
        parser = DMNParser()
        
        # Test greater than
        condition, constant = parser._parse_feel_expression("> 10", "number")
        assert condition == "greater_than"
        assert constant == "10"
        
        # Test greater than or equal
        condition, constant = parser._parse_feel_expression(">= 5", "number")
        assert condition == "greater_than_or_equal"
        assert constant == "5"
        
        # Test less than
        condition, constant = parser._parse_feel_expression("< 20", "number")
        assert condition == "less_than"
        assert constant == "20"
        
        # Test less than or equal
        condition, constant = parser._parse_feel_expression("<= 15", "number")
        assert condition == "less_than_or_equal"
        assert constant == "15"
        
        # Test string equality
        condition, constant = parser._parse_feel_expression('"test"', "string")
        assert condition == "equal"
        assert constant == '"test"'
        
        # Test range
        condition, constant = parser._parse_feel_expression("[5..10]", "number")
        assert condition == "range"
        assert "[5, 10]" in constant or "[5,10]" in constant
        
        # Test empty/dash
        condition, constant = parser._parse_feel_expression("-", "string")
        assert condition == "equal"
        assert constant == "''"
    
    def test_parse_invalid_xml_raises_error(self):
        """Test that invalid XML raises ConfigurationError."""
        parser = DMNParser()
        
        with pytest.raises(ConfigurationError) as exc_info:
            parser.parse_content("not valid xml")
        
        assert "DMN_PARSE_ERROR" in str(exc_info.value.error_code) or "DMN_PARSE_ERROR" == exc_info.value.error_code
    
    def test_parse_empty_dmn_returns_empty_rules(self):
        """Test parsing DMN file with no decision tables."""
        dmn_content = '''<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 id="test" name="Test">
</dmn:definitions>'''
        
        parser = DMNParser()
        result = parser.parse_content(dmn_content)
        
        assert result["rules_set"] == []
        assert result["patterns"] == {}
    
    def test_parse_dmn_file_not_found_raises_error(self):
        """Test that missing file raises ConfigurationError."""
        parser = DMNParser()
        
        with pytest.raises(ConfigurationError):
            parser.parse_file("/nonexistent/path/file.dmn")
    
    def test_build_execution_order_with_dependencies(self):
        """Test that execution order respects dependencies."""
        parser = DMNParser()
        
        # Create test metadata with dependencies
        decisions_metadata = [
            {
                "decision_id": "Decision_A",
                "decision_name": "Decision A",
                "dependencies": []
            },
            {
                "decision_id": "Decision_B",
                "decision_name": "Decision B",
                "dependencies": []
            },
            {
                "decision_id": "Decision_C",
                "decision_name": "Decision C",
                "dependencies": ["Decision_A", "Decision_B"]
            }
        ]
        
        execution_order = parser._build_execution_order(decisions_metadata)
        
        # Decision_C should come after Decision_A and Decision_B
        assert len(execution_order) == 3
        assert "Decision_C" in execution_order
        assert "Decision_A" in execution_order
        assert "Decision_B" in execution_order
        
        # Find positions
        pos_a = execution_order.index("Decision_A")
        pos_b = execution_order.index("Decision_B")
        pos_c = execution_order.index("Decision_C")
        
        # Decision_C should be executed after both A and B
        assert pos_c > pos_a
        assert pos_c > pos_b
    
    def test_build_execution_order_no_dependencies(self):
        """Test execution order with no dependencies."""
        parser = DMNParser()
        
        decisions_metadata = [
            {
                "decision_id": "Decision_A",
                "decision_name": "Decision A",
                "dependencies": []
            },
            {
                "decision_id": "Decision_B",
                "decision_name": "Decision B",
                "dependencies": []
            }
        ]
        
        execution_order = parser._build_execution_order(decisions_metadata)
        
        assert len(execution_order) == 2
        assert "Decision_A" in execution_order
        assert "Decision_B" in execution_order
