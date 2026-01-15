"""
DMN (Decision Model Notation) Parser Module.

This module provides functionality to parse DMN XML files and convert them
to the rule engine's internal rule format.

DMN files are XML-based decision models that contain decision tables.
Each decision table contains rules with input conditions and output values.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from common.logger import get_logger
from common.exceptions import ConfigurationError, DataValidationError
from common.conditions_enum import equation_operators

logger = get_logger(__name__)

# DMN namespace
DMN_NS = {
    'dmn': 'https://www.omg.org/spec/DMN/20191111/MODEL/',
    'dmn12': 'https://www.omg.org/spec/DMN/20180521/MODEL/',
    'dmn13': 'https://www.omg.org/spec/DMN/20191111/MODEL/',
    'feel': 'https://www.omg.org/spec/DMN/20191111/FEEL/',
}


class DMNParser:
    """
    Parser for DMN (Decision Model Notation) XML files.
    
    This parser extracts decision tables from DMN files and converts them
    to the rule engine's internal rule format.
    """
    
    def __init__(self):
        """Initialize DMN parser."""
        logger.debug("DMNParser initialized")
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a DMN XML file and convert to rule format.
        
        Args:
            file_path: Path to DMN XML file
            
        Returns:
            Dictionary containing:
            - rules_set: List of rules converted from DMN decision tables
            - patterns: Dictionary of patterns (if any)
            
        Raises:
            ConfigurationError: If file cannot be read or parsed
            DataValidationError: If DMN structure is invalid
        """
        logger.info("Parsing DMN file", file_path=file_path)
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Detect namespace
            namespace = self._detect_namespace(root)
            logger.debug("Detected DMN namespace", namespace=namespace)
            
            # Find all decision tables
            decisions = self._find_decisions(root, namespace)
            
            if not decisions:
                logger.warning("No decision tables found in DMN file", file_path=file_path)
                return {
                    "rules_set": [], 
                    "patterns": {},
                    "decisions_metadata": [],
                    "execution_order": []
                }
            
            # Parse decisions and extract metadata
            rules_set = []
            decisions_metadata = []
            
            for decision in decisions:
                decision_id = decision.get('id', '')
                decision_name = decision.get('name', 'Unknown Decision')
                
                # Parse dependencies
                dependencies = self._parse_information_requirements(decision, namespace)
                
                # Parse decision table
                decision_rules, inputs, outputs = self._parse_decision_table(decision, namespace)
                rules_set.extend(decision_rules)
                
                # Build output field mapping
                output_field_mapping = self._get_output_field_mapping(outputs, decision_id)
                
                # Store decision metadata
                decisions_metadata.append({
                    "decision_id": decision_id,
                    "decision_name": decision_name,
                    "dependencies": dependencies,
                    "inputs": inputs,
                    "outputs": outputs,
                    "output_field_mapping": output_field_mapping
                })
            
            # Build execution order
            execution_order = self._build_execution_order(decisions_metadata)
            
            logger.info("DMN file parsed successfully", 
                       file_path=file_path, 
                       rules_count=len(rules_set),
                       decisions_count=len(decisions_metadata),
                       execution_order=execution_order)
            
            return {
                "rules_set": rules_set,
                "patterns": {},  # DMN doesn't have patterns, but we maintain structure
                "decisions_metadata": decisions_metadata,
                "execution_order": execution_order
            }
            
        except ET.ParseError as e:
            logger.error("Failed to parse DMN XML", file_path=file_path, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Invalid DMN XML format in {file_path}: {str(e)}",
                error_code="DMN_PARSE_ERROR",
                context={'file_path': file_path, 'error': str(e)}
            ) from e
        except Exception as e:
            logger.error("Failed to parse DMN file", file_path=file_path, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to parse DMN file {file_path}: {str(e)}",
                error_code="DMN_READ_ERROR",
                context={'file_path': file_path, 'error': str(e)}
            ) from e
    
    def parse_content(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse DMN XML content from string.
        
        Args:
            xml_content: DMN XML content as string
            
        Returns:
            Dictionary containing rules_set and patterns
            
        Raises:
            ConfigurationError: If content cannot be parsed
        """
        logger.debug("Parsing DMN XML content")
        
        try:
            root = ET.fromstring(xml_content)
            namespace = self._detect_namespace(root)
            
            decisions = self._find_decisions(root, namespace)
            
            if not decisions:
                logger.warning("No decision tables found in DMN content")
                return {
                    "rules_set": [], 
                    "patterns": {},
                    "decisions_metadata": [],
                    "execution_order": []
                }
            
            # Parse decisions and extract metadata
            rules_set = []
            decisions_metadata = []
            
            for decision in decisions:
                decision_id = decision.get('id', '')
                decision_name = decision.get('name', 'Unknown Decision')
                
                # Parse dependencies
                dependencies = self._parse_information_requirements(decision, namespace)
                
                # Parse decision table
                decision_rules, inputs, outputs = self._parse_decision_table(decision, namespace)
                rules_set.extend(decision_rules)
                
                # Build output field mapping
                output_field_mapping = self._get_output_field_mapping(outputs, decision_id)
                
                # Store decision metadata
                decisions_metadata.append({
                    "decision_id": decision_id,
                    "decision_name": decision_name,
                    "dependencies": dependencies,
                    "inputs": inputs,
                    "outputs": outputs,
                    "output_field_mapping": output_field_mapping
                })
            
            # Build execution order
            execution_order = self._build_execution_order(decisions_metadata)
            
            logger.info("DMN content parsed successfully", 
                       rules_count=len(rules_set),
                       decisions_count=len(decisions_metadata),
                       execution_order=execution_order)
            
            return {
                "rules_set": rules_set,
                "patterns": {},
                "decisions_metadata": decisions_metadata,
                "execution_order": execution_order
            }
            
        except ET.ParseError as e:
            logger.error("Failed to parse DMN XML content", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Invalid DMN XML format: {str(e)}",
                error_code="DMN_PARSE_ERROR",
                context={'error': str(e)}
            ) from e
        except Exception as e:
            logger.error("Failed to parse DMN content", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to parse DMN content: {str(e)}",
                error_code="DMN_CONTENT_ERROR",
                context={'error': str(e)}
            ) from e
    
    def _detect_namespace(self, root: Element) -> Dict[str, str]:
        """
        Detect DMN namespace from root element.
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary of namespace prefixes to URIs
        """
        # Check for common DMN namespaces
        ns_map = {}
        
        # Check root tag namespace
        if root.tag.startswith('{'):
            ns_uri = root.tag[1:].split('}')[0]
            ns_map['dmn'] = ns_uri
        
        # Check for namespace declarations
        for prefix, uri in root.attrib.items():
            if prefix.startswith('xmlns'):
                if prefix == 'xmlns':
                    ns_map['dmn'] = uri
                elif prefix.startswith('xmlns:'):
                    prefix_name = prefix.split(':')[1]
                    ns_map[prefix_name] = uri
        
        # Use default namespace if not found
        if 'dmn' not in ns_map:
            # Try common DMN namespaces
            for ns_uri in DMN_NS.values():
                ns_map['dmn'] = ns_uri
                break
        
        return ns_map
    
    def _find_decisions(self, root: Element, namespace: Dict[str, str]) -> List[Element]:
        """
        Find all decision elements in DMN file.
        
        Args:
            root: XML root element
            namespace: Namespace mapping
            
        Returns:
            List of decision elements
        """
        decisions = []
        ns_prefix = namespace.get('dmn', DMN_NS['dmn'])
        
        # Try different namespace formats
        for ns_uri in [ns_prefix] + list(DMN_NS.values()):
            decisions = root.findall(f'.//{{{ns_uri}}}decision')
            if decisions:
                break
        
        return decisions
    
    def _parse_decision_table(self, decision: Element, namespace: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse a decision table and convert to rules.
        
        Args:
            decision: Decision XML element
            namespace: Namespace mapping
            
        Returns:
            Tuple of (rules, inputs, outputs)
        """
        ns_uri = namespace.get('dmn', DMN_NS['dmn'])
        
        # Get decision ID and name
        decision_id = decision.get('id', '')
        decision_name = decision.get('name', 'Unknown Decision')
        
        logger.debug("Parsing decision table", 
                    decision_id=decision_id, 
                    decision_name=decision_name)
        
        # Find decision table
        decision_table = decision.find(f'{{{ns_uri}}}decisionTable')
        if decision_table is None:
            logger.warning("No decision table found in decision", decision_id=decision_id)
            return [], [], []
        
        # Get hit policy
        hit_policy = decision_table.get('hitPolicy', 'UNIQUE')
        
        # Get input and output columns
        inputs = self._parse_inputs(decision_table, ns_uri)
        outputs = self._parse_outputs(decision_table, ns_uri)
        
        if not inputs:
            logger.warning("No input columns found in decision table", decision_id=decision_id)
            return [], inputs, outputs
        
        if not outputs:
            logger.warning("No output columns found in decision table", decision_id=decision_id)
            return [], inputs, outputs
        
        # Parse rules
        rules = []
        rule_elements = decision_table.findall(f'{{{ns_uri}}}rule')
        
        for rule_idx, rule_elem in enumerate(rule_elements, start=1):
            rule = self._parse_rule(
                rule_elem, 
                ns_uri, 
                inputs, 
                outputs, 
                decision_id, 
                decision_name,
                rule_idx,
                hit_policy
            )
            if rule:
                rules.append(rule)
        
        logger.info("Decision table parsed", 
                   decision_id=decision_id, 
                   rules_count=len(rules))
        
        return rules, inputs, outputs
    
    def _parse_inputs(self, decision_table: Element, ns_uri: str) -> List[Dict[str, Any]]:
        """
        Parse input columns from decision table.
        
        Args:
            decision_table: Decision table XML element
            ns_uri: Namespace URI
            
        Returns:
            List of input column dictionaries with 'id', 'label', 'type', 'field_name'
        """
        inputs = []
        input_elements = decision_table.findall(f'{{{ns_uri}}}input')
        
        # Camunda namespace for inputVariable attribute
        camunda_ns_uri = 'http://camunda.org/schema/1.0/dmn'
        camunda_ns_attr = f'{{{camunda_ns_uri}}}inputVariable'
        
        for input_elem in input_elements:
            input_id = input_elem.get('id', '')
            input_label = input_elem.get('label', '')
            
            # Get input expression
            input_expression = input_elem.find(f'{{{ns_uri}}}inputExpression')
            input_type = 'string'  # default
            field_name = input_label.lower().replace(' ', '_')  # Default fallback
            
            # Priority 1: Check for camunda:inputVariable attribute (explicit variable name)
            # Try with namespace first, then try common variations
            camunda_var = input_elem.get(camunda_ns_attr)
            if not camunda_var:
                # Try without namespace prefix (some parsers handle namespaces differently)
                for attr_name in input_elem.attrib:
                    if attr_name.endswith('inputVariable') or 'inputVariable' in attr_name:
                        camunda_var = input_elem.get(attr_name)
                        break
            
            if camunda_var:
                field_name = camunda_var.strip()
            elif input_expression is not None:
                type_ref = input_expression.get('typeRef', 'string')
                input_type = type_ref
                
                # Priority 2: Extract field name from feel:text or text element
                feel_text = input_expression.find(f'{{{DMN_NS["feel"]}}}text')
                if feel_text is None:
                    # Try without namespace (for non-namespaced text elements)
                    feel_text = input_expression.find('.//text')
                if feel_text is not None and feel_text.text and feel_text.text.strip():
                    field_name = feel_text.text.strip()
            
            inputs.append({
                'id': input_id,
                'label': input_label or input_id,
                'type': input_type,
                'field_name': field_name  # Actual field name in data (e.g., "season", "guests", "element_1")
            })
        
        return inputs
    
    def _parse_outputs(self, decision_table: Element, ns_uri: str) -> List[Dict[str, Any]]:
        """
        Parse output columns from decision table.
        
        Args:
            decision_table: Decision table XML element
            ns_uri: Namespace URI
            
        Returns:
            List of output column dictionaries with 'id', 'label', 'name', 'type'
        """
        outputs = []
        output_elements = decision_table.findall(f'{{{ns_uri}}}output')
        
        for output_elem in output_elements:
            output_id = output_elem.get('id', '')
            output_label = output_elem.get('label', '')
            output_name = output_elem.get('name', '')
            output_type = output_elem.get('typeRef', 'string')
            
            outputs.append({
                'id': output_id,
                'label': output_label or output_name or output_id,
                'name': output_name or output_label or output_id,
                'type': output_type
            })
        
        return outputs
    
    def _parse_rule(
        self, 
        rule_elem: Element, 
        ns_uri: str, 
        inputs: List[Dict[str, Any]], 
        outputs: List[Dict[str, Any]],
        decision_id: str,
        decision_name: str,
        rule_idx: int,
        hit_policy: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single rule from decision table.
        
        Args:
            rule_elem: Rule XML element
            ns_uri: Namespace URI
            inputs: List of input column definitions
            outputs: List of output column definitions
            decision_id: Decision table ID
            decision_name: Decision table name
            rule_idx: Rule index (1-based)
            hit_policy: Hit policy of the decision table
            
        Returns:
            Rule dictionary or None if rule is invalid
        """
        # Get input entries
        input_entries = rule_elem.findall(f'{{{ns_uri}}}inputEntry')
        # Get output entries
        output_entries = rule_elem.findall(f'{{{ns_uri}}}outputEntry')
        
        if len(input_entries) != len(inputs):
            logger.warning("Input entry count mismatch", 
                         expected=len(inputs), 
                         actual=len(input_entries),
                         decision_id=decision_id,
                         rule_idx=rule_idx)
            return None
        
        if len(output_entries) != len(outputs):
            logger.warning("Output entry count mismatch",
                         expected=len(outputs),
                         actual=len(output_entries),
                         decision_id=decision_id,
                         rule_idx=rule_idx)
            return None
        
        # DMN decision tables can have multiple input columns that must all be satisfied (AND logic)
        # We need to parse all input entries and combine them into a single condition string
        
        if not inputs or not outputs:
            return None
        
        # Parse all input entries and build condition strings
        condition_parts = []
        message_parts = []
        
        for input_idx, input_def in enumerate(inputs):
            input_entry = input_entries[input_idx]
            input_text = self._get_text_content(input_entry)
            
            # Parse condition and constant from FEEL expression
            condition_op, constant = self._parse_feel_expression(input_text, input_def['type'])
            
            # Get the field name from input definition (e.g., "season", "guests")
            # This is the actual field name in the input data dictionary
            field_name = input_def.get('field_name', input_def.get('label', '').lower().replace(' ', '_'))
            
            # Build condition string for this input
            operator = equation_operators(condition_op)
            if operator == "nothing":
                logger.warning("Unknown condition operator", 
                             operator=condition_op, 
                             decision_id=decision_id,
                             rule_idx=rule_idx,
                             input_idx=input_idx)
                continue
            
            # Build condition part: field_name operator constant
            condition_part = f"{field_name} {operator} {constant}"
            condition_parts.append(condition_part)
            
            # Build message part
            message_parts.append(f"{input_def['label']} {condition_op} {constant}")
        
        if not condition_parts:
            logger.warning("No valid conditions found for rule", 
                         decision_id=decision_id, 
                         rule_idx=rule_idx)
            return None
        
        # Combine all conditions with AND logic
        combined_condition = " and ".join(condition_parts)
        
        # Parse all output entries
        output_values = {}
        for output_idx, output_def in enumerate(outputs):
            if output_idx < len(output_entries):
                output_entry = output_entries[output_idx]
                output_text = self._get_text_content(output_entry)
                output_label = output_def.get('label', '') or output_def.get('name', '') or output_def.get('id', '')
                if output_label:
                    # Store output value, removing quotes
                    output_values[output_label] = output_text.strip('"\'')
        
        # Parse first output entry (primary result) for backward compatibility
        first_output = outputs[0]
        first_output_entry = output_entries[0]
        output_text = self._get_text_content(first_output_entry)
        
        # Generate rule ID
        rule_id = f"{decision_id}_R{rule_idx:04d}"
        
        # Generate rule name
        rule_name = f"{decision_name} - Rule {rule_idx}"
        
        # Generate message from all input conditions
        message = " and ".join(message_parts)
        
        # Use first input for backward compatibility (attribute, condition, constant)
        first_input = inputs[0]
        first_input_entry = input_entries[0]
        first_input_text = self._get_text_content(first_input_entry)
        first_condition, first_constant = self._parse_feel_expression(first_input_text, first_input['type'])
        
        # Create rule dictionary
        rule = {
            "id": rule_id,
            "rule_name": rule_name,
            "decision_id": decision_id,  # Add decision_id for grouping
            "attribute": first_input['label'],  # Keep for backward compatibility
            "condition": first_condition,  # Keep for backward compatibility
            "constant": first_constant,  # Keep for backward compatibility
            "combined_condition": combined_condition,  # New: combined condition string with all inputs
            "message": message,
            "weight": 1.0,  # Default weight
            "rule_point": 10.0,  # Default rule point
            "priority": rule_idx,  # Use rule index as priority
            "action_result": output_text.strip('"\'')  # Remove quotes from output (backward compatibility)
        }
        
        # Add all outputs if there are multiple outputs
        if len(outputs) > 1:
            rule["outputs"] = output_values
        elif output_values:
            # Even for single output, store it for consistency
            rule["outputs"] = output_values
        
        return rule
    
    def _get_text_content(self, elem: Element) -> str:
        """
        Get text content from XML element, handling nested elements.
        
        Args:
            elem: XML element
            
        Returns:
            Text content as string
        """
        # Get direct text
        text_parts = []
        if elem.text and elem.text.strip():
            text_parts.append(elem.text.strip())
        
        # Recursively get text from all descendants
        for child in elem.iter():
            if child.text and child.text.strip():
                text_parts.append(child.text.strip())
            if child.tail and child.tail.strip():
                text_parts.append(child.tail.strip())
        
        # Join all text parts
        result = ' '.join(text_parts).strip()
        
        # Handle XML entities
        result = result.replace('&lt;', '<')
        result = result.replace('&gt;', '>')
        result = result.replace('&amp;', '&')
        result = result.replace('&quot;', '"')
        result = result.replace('&apos;', "'")
        
        return result
    
    def _parse_feel_expression(self, expression: str, input_type: str) -> Tuple[str, str]:
        """
        Parse FEEL expression to extract condition operator and constant.
        
        FEEL (Friendly Enough Expression Language) is used in DMN for expressions.
        This is a simplified parser that handles common patterns.
        
        Args:
            expression: FEEL expression string
            input_type: Type of the input (string, number, etc.)
            
        Returns:
            Tuple of (condition_operator, constant_value)
        """
        expression = expression.strip()
        
        # Handle empty or dash (matches anything)
        if not expression or expression == '-':
            return "equal", "''"
        
        # Handle quoted strings
        if expression.startswith('"') and expression.endswith('"'):
            return "equal", expression
        
        if expression.startswith("'") and expression.endswith("'"):
            return "equal", expression
        
        # Handle numeric comparisons
        if expression.startswith('>='):
            value = expression[2:].strip()
            return "greater_than_or_equal", value
        
        if expression.startswith('<='):
            value = expression[2:].strip()
            return "less_than_or_equal", value
        
        if expression.startswith('>'):
            value = expression[1:].strip()
            return "greater_than", value
        
        if expression.startswith('<'):
            value = expression[1:].strip()
            return "less_than", value
        
        # Handle ranges [a..b]
        if expression.startswith('[') and '..' in expression and expression.endswith(']'):
            # Extract range values
            range_content = expression[1:-1].strip()
            parts = range_content.split('..')
            if len(parts) == 2:
                # For range, we'll use 'range' condition with list
                return "range", f"[{parts[0].strip()}, {parts[1].strip()}]"
        
        # Handle lists (for 'in' condition)
        if expression.startswith('[') and expression.endswith(']'):
            return "range", expression
        
        # Handle not equal
        if expression.startswith('not('):
            inner = expression[4:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                return "not_equal", inner
            return "not_equal", f'"{inner}"'
        
        # Default: equality
        # If it's a number, return as-is, otherwise quote it
        try:
            float(expression)
            return "equal", expression
        except ValueError:
            return "equal", f'"{expression}"'
    
    def _parse_information_requirements(self, decision: Element, namespace: Dict[str, str]) -> List[str]:
        """
        Parse InformationRequirement dependencies from decision element.
        
        Extracts dependent decision IDs from InformationRequirement elements.
        
        Args:
            decision: Decision XML element
            namespace: DMN namespace mapping
            
        Returns:
            List of dependent decision IDs (e.g., ["Decision_0nq1td4", "Decision_0kgjdku"])
        """
        ns_uri = namespace.get('dmn', DMN_NS['dmn'])
        dependencies = []
        
        # Find all informationRequirement elements
        info_requirements = decision.findall(f'{{{ns_uri}}}informationRequirement')
        
        for info_req in info_requirements:
            # Find requiredDecision element
            required_decision = info_req.find(f'{{{ns_uri}}}requiredDecision')
            if required_decision is not None:
                href = required_decision.get('href', '')
                if href:
                    # Remove '#' prefix if present
                    decision_id = href.lstrip('#')
                    if decision_id:
                        dependencies.append(decision_id)
        
        return dependencies
    
    def _build_execution_order(self, decisions_metadata: List[Dict[str, Any]]) -> List[str]:
        """
        Build dependency graph and return topological sort order.
        
        Args:
            decisions_metadata: List of decision metadata dictionaries with 'decision_id' and 'dependencies'
            
        Returns:
            Ordered list of decision IDs (independent first, dependent last)
        """
        # Build dependency graph: {decision_id: set(dependent_ids)}
        graph: Dict[str, set] = {}
        all_decision_ids = set()
        
        for metadata in decisions_metadata:
            decision_id = metadata.get('decision_id', '')
            if decision_id:
                all_decision_ids.add(decision_id)
                graph[decision_id] = set(metadata.get('dependencies', []))
        
        # Calculate in-degrees
        # In-degree = number of dependencies a decision has (decisions it depends on)
        in_degree: Dict[str, int] = {}
        
        for decision_id in all_decision_ids:
            dependencies = graph.get(decision_id, set())
            in_degree[decision_id] = len(dependencies)
            
            # Validate that all dependencies exist
            for dep_id in dependencies:
                if dep_id not in all_decision_ids:
                    logger.warning("Dependent decision not found", 
                                 dependent_id=dep_id, 
                                 decision_id=decision_id)
        
        # Topological sort using Kahn's algorithm
        queue: List[str] = []
        result: List[str] = []
        
        # Start with nodes having in-degree = 0 (independent decisions)
        for decision_id, degree in in_degree.items():
            if degree == 0:
                queue.append(decision_id)
        
        while queue:
            # Process node with no dependencies
            current = queue.pop(0)
            result.append(current)
            
            # Decrement in-degrees of dependent nodes
            for decision_id, dependencies in graph.items():
                if current in dependencies:
                    in_degree[decision_id] -= 1
                    if in_degree[decision_id] == 0:
                        queue.append(decision_id)
        
        # Check for cycles (remaining nodes with in-degree > 0)
        remaining = [decision_id for decision_id, degree in in_degree.items() 
                     if degree > 0 and decision_id not in result]
        
        if remaining:
            logger.warning(
                "Circular dependency detected. Using original order for remaining decisions",
                decisions=remaining
            )
            # Add remaining decisions in original order
            for metadata in decisions_metadata:
                decision_id = metadata.get('decision_id', '')
                if decision_id in remaining:
                    result.append(decision_id)
        else:
            # Add any decisions not in result (shouldn't happen, but safety check)
            for metadata in decisions_metadata:
                decision_id = metadata.get('decision_id', '')
                if decision_id not in result:
                    result.append(decision_id)
        
        logger.info("Built execution order", 
                   execution_order=result,
                   total_decisions=len(result))
        
        return result
    
    def _get_output_field_mapping(self, outputs: List[Dict[str, Any]], decision_id: str) -> Dict[str, str]:
        """
        Map output labels to input field names for dependent decisions.
        
        Args:
            outputs: List of output column definitions
            decision_id: Decision ID for logging
            
        Returns:
            Dictionary mapping output labels to field names: {output_label: field_name}
        """
        mapping = {}
        
        for output in outputs:
            output_label = output.get('label', '') or output.get('name', '')
            if output_label:
                # Use label as both output identifier and input field name
                mapping[output_label] = output_label
        
        if not mapping:
            logger.warning("No output labels found for decision", decision_id=decision_id)
        
        return mapping
