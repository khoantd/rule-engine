"""
Rule Testing Framework Module.

This module provides comprehensive rule testing capabilities including:
- Test case execution
- Assertion validation
- Test report generation
- Integration with pytest
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from common.logger import get_logger
from common.exceptions import RuleEvaluationError, DataValidationError
from common.rule_validator import validate_rule, RuleValidationResult
from services.ruleengine_exec import rules_exec

logger = get_logger(__name__)


@dataclass
class RuleTestCase:
    """Single test case for rule testing."""
    
    name: str
    description: Optional[str]
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]]
    expected_total_points: Optional[float]
    expected_pattern_result: Optional[str]
    expected_action_recommendation: Optional[str]
    expected_rules_matched: Optional[List[str]]
    skip: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
        return asdict(self)


@dataclass
class RuleTestResult:
    """Result of a single test case execution."""
    
    test_name: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    actual_output: Optional[Dict[str, Any]]
    expected_output: Optional[Dict[str, Any]]
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return asdict(self)


@dataclass
class RuleTestSuite:
    """Test suite containing multiple test cases."""
    
    name: str
    description: Optional[str]
    test_cases: List[RuleTestCase]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test suite to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'test_cases': [tc.to_dict() for tc in self.test_cases]
        }


@dataclass
class RuleTestReport:
    """Test execution report."""
    
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    test_results: List[RuleTestResult]
    total_execution_time_ms: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return asdict(self)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics."""
        return {
            'suite_name': self.suite_name,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'pass_rate': (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0.0,
            'total_execution_time_ms': self.total_execution_time_ms,
            'avg_execution_time_ms': (
                self.total_execution_time_ms / self.total_tests 
                if self.total_tests > 0 else 0.0
            ),
            'timestamp': self.timestamp
        }


class RuleTester:
    """Rule testing framework."""
    
    def __init__(self):
        """Initialize rule tester."""
        pass
    
    def run_test_case(
        self,
        test_case: RuleTestCase,
        dry_run: bool = True
    ) -> RuleTestResult:
        """
        Execute a single test case.
        
        Args:
            test_case: Test case to execute
            dry_run: Whether to run in dry-run mode (default: True)
            
        Returns:
            RuleTestResult with test execution results
        """
        import time
        start_time = time.time()
        
        errors = []
        warnings = []
        actual_output = None
        
        if test_case.skip:
            logger.info("Test case skipped", test_name=test_case.name)
            return RuleTestResult(
                test_name=test_case.name,
                passed=True,
                errors=[],
                warnings=["Test case was skipped"],
                actual_output=None,
                expected_output=test_case.expected_output,
                execution_time_ms=0.0
            )
        
        logger.info("Running test case", test_name=test_case.name)
        
        try:
            # Execute rules
            actual_output = rules_exec(
                data=test_case.input_data,
                dry_run=dry_run
            )
            
            # Validate assertions
            if test_case.expected_total_points is not None:
                actual_points = actual_output.get('total_points', 0.0)
                expected_points = test_case.expected_total_points
                if abs(actual_points - expected_points) > 0.01:  # Allow small floating point differences
                    errors.append(
                        f"Total points mismatch: expected {expected_points}, got {actual_points}"
                    )
            
            if test_case.expected_pattern_result is not None:
                actual_pattern = actual_output.get('pattern_result', '')
                if actual_pattern != test_case.expected_pattern_result:
                    errors.append(
                        f"Pattern result mismatch: expected '{test_case.expected_pattern_result}', "
                        f"got '{actual_pattern}'"
                    )
            
            if test_case.expected_action_recommendation is not None:
                actual_action = actual_output.get('action_recommendation')
                expected_action = test_case.expected_action_recommendation
                if actual_action != expected_action:
                    errors.append(
                        f"Action recommendation mismatch: expected '{expected_action}', "
                        f"got '{actual_action}'"
                    )
            
            if test_case.expected_rules_matched is not None:
                if dry_run and 'would_match' in actual_output:
                    matched_rules = [
                        e['rule_name'] 
                        for e in actual_output.get('would_match', [])
                    ]
                    expected_rules = set(test_case.expected_rules_matched)
                    actual_rules = set(matched_rules)
                    
                    missing = expected_rules - actual_rules
                    unexpected = actual_rules - expected_rules
                    
                    if missing:
                        errors.append(
                            f"Expected rules not matched: {list(missing)}"
                        )
                    
                    if unexpected:
                        warnings.append(
                            f"Unexpected rules matched: {list(unexpected)}"
                        )
                else:
                    warnings.append(
                        "Cannot validate expected_rules_matched without dry_run mode"
                    )
            
            # Generic expected_output comparison
            if test_case.expected_output is not None:
                for key, expected_value in test_case.expected_output.items():
                    if key in actual_output:
                        actual_value = actual_output[key]
                        if actual_value != expected_value:
                            errors.append(
                                f"Output mismatch for '{key}': expected {expected_value}, "
                                f"got {actual_value}"
                            )
                    else:
                        errors.append(f"Missing output key: '{key}'")
            
        except Exception as e:
            errors.append(f"Test execution failed: {str(e)}")
            logger.error("Test case execution failed", 
                        test_name=test_case.name, error=str(e), exc_info=True)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        passed = len(errors) == 0
        
        logger.info("Test case completed", 
                   test_name=test_case.name, 
                   passed=passed,
                   errors_count=len(errors),
                   execution_time_ms=execution_time_ms)
        
        return RuleTestResult(
            test_name=test_case.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            actual_output=actual_output,
            expected_output=test_case.expected_output,
            execution_time_ms=execution_time_ms
        )
    
    def run_test_suite(
        self,
        test_suite: RuleTestSuite,
        dry_run: bool = True
    ) -> RuleTestReport:
        """
        Execute a test suite.
        
        Args:
            test_suite: Test suite to execute
            dry_run: Whether to run in dry-run mode (default: True)
            
        Returns:
            RuleTestReport with test execution results
        """
        import time
        start_time = time.time()
        
        logger.info("Running test suite", suite_name=test_suite.name, 
                   test_cases_count=len(test_suite.test_cases))
        
        test_results = []
        passed = 0
        failed = 0
        skipped = 0
        
        for test_case in test_suite.test_cases:
            result = self.run_test_case(test_case, dry_run=dry_run)
            test_results.append(result)
            
            if test_case.skip:
                skipped += 1
            elif result.passed:
                passed += 1
            else:
                failed += 1
        
        total_execution_time_ms = (time.time() - start_time) * 1000
        
        report = RuleTestReport(
            suite_name=test_suite.name,
            total_tests=len(test_suite.test_cases),
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            test_results=test_results,
            total_execution_time_ms=total_execution_time_ms,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info("Test suite completed", 
                   suite_name=test_suite.name,
                   total_tests=len(test_suite.test_cases),
                   passed=passed,
                   failed=failed,
                   skipped=skipped,
                   total_execution_time_ms=total_execution_time_ms)
        
        return report
    
    def load_test_suite_from_dict(self, data: Dict[str, Any]) -> RuleTestSuite:
        """
        Load test suite from dictionary.
        
        Args:
            data: Dictionary containing test suite data
            
        Returns:
            RuleTestSuite instance
        """
        test_cases = []
        
        for tc_data in data.get('test_cases', []):
            test_case = RuleTestCase(
                name=tc_data.get('name', 'Unnamed Test'),
                description=tc_data.get('description'),
                input_data=tc_data.get('input_data', {}),
                expected_output=tc_data.get('expected_output'),
                expected_total_points=tc_data.get('expected_total_points'),
                expected_pattern_result=tc_data.get('expected_pattern_result'),
                expected_action_recommendation=tc_data.get('expected_action_recommendation'),
                expected_rules_matched=tc_data.get('expected_rules_matched'),
                skip=tc_data.get('skip', False)
            )
            test_cases.append(test_case)
        
        return RuleTestSuite(
            name=data.get('name', 'Unnamed Suite'),
            description=data.get('description'),
            test_cases=test_cases
        )
    
    def load_test_suite_from_file(self, file_path: str) -> RuleTestSuite:
        """
        Load test suite from JSON file.
        
        Args:
            file_path: Path to JSON file containing test suite
            
        Returns:
            RuleTestSuite instance
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        return self.load_test_suite_from_dict(data)
    
    def save_test_suite_to_file(
        self,
        test_suite: RuleTestSuite,
        file_path: str
    ) -> None:
        """
        Save test suite to JSON file.
        
        Args:
            test_suite: Test suite to save
            file_path: Path to JSON file
        """
        with open(file_path, 'w') as f:
            json.dump(test_suite.to_dict(), f, indent=2)
    
    def save_report_to_file(
        self,
        report: RuleTestReport,
        file_path: str
    ) -> None:
        """
        Save test report to JSON file.
        
        Args:
            report: Test report to save
            file_path: Path to JSON file
        """
        with open(file_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2, default=str)


# Global tester instance
_tester: Optional[RuleTester] = None


def get_rule_tester() -> RuleTester:
    """
    Get global rule tester instance.
    
    Returns:
        RuleTester instance
    """
    global _tester
    if _tester is None:
        _tester = RuleTester()
    return _tester


def test_rule(
    input_data: Dict[str, Any],
    expected_output: Optional[Dict[str, Any]] = None,
    **kwargs
) -> RuleTestResult:
    """
    Test a rule with input data (convenience function).
    
    Args:
        input_data: Input data for rule execution
        expected_output: Expected output dictionary
        **kwargs: Additional test case parameters
        
    Returns:
        RuleTestResult with test execution results
        
    Example:
        >>> result = test_rule(
        ...     input_data={'status': 'open'},
        ...     expected_total_points=10.0,
        ...     expected_pattern_result='APPROVE'
        ... )
        >>> assert result.passed
    """
    tester = get_rule_tester()
    test_case = RuleTestCase(
        name=kwargs.get('name', 'Quick Test'),
        description=kwargs.get('description'),
        input_data=input_data,
        expected_output=expected_output,
        expected_total_points=kwargs.get('expected_total_points'),
        expected_pattern_result=kwargs.get('expected_pattern_result'),
        expected_action_recommendation=kwargs.get('expected_action_recommendation'),
        expected_rules_matched=kwargs.get('expected_rules_matched'),
        skip=kwargs.get('skip', False)
    )
    return tester.run_test_case(test_case, dry_run=kwargs.get('dry_run', True))

