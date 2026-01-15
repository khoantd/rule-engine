#!/usr/bin/env python3
"""
Simple test script for Tương Sinh Tương Khắc DMN rules.

This script tests the DMN rules by providing element combinations directly,
testing both the "Can"/"Chi" decisions and the "Ngu Hanh" decision separately.
"""

import json
from pathlib import Path

from services.ruleengine_exec import dmn_rules_exec
from common.logger import get_logger

logger = get_logger(__name__)


def test_can_decision():
    """Test the Can decision (maps celestial stems to elements)."""
    print("\n" + "=" * 80)
    print("TESTING: Can Decision")
    print("=" * 80)
    
    dmn_file = "Tương Sinh Tương Khắc.dmn"
    test_cases = [
        {"can": "giap", "expected": "wood"},
        {"can": "at", "expected": "wood"},
        {"can": "binh", "expected": "fire"},
        {"can": "dinh", "expected": "fire"},
        {"can": "mau", "expected": "earth"},
        {"can": "ky", "expected": "earth"},
        {"can": "canh", "expected": "metal"},
        {"can": "tan", "expected": "metal"},
        {"can": "nham", "expected": "water"},
        {"can": "quy", "expected": "water"},
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = dmn_rules_exec(dmn_file=dmn_file, data={"can": test["can"]}, dry_run=True)
        
        # Find the matched "Can" rule
        matched_can_rule = None
        for rule in result.get("would_match", []):
            if "Can" in rule.get("rule_name", ""):
                matched_can_rule = rule
                break
        
        if matched_can_rule and matched_can_rule.get("action_result") == test["expected"]:
            print(f"✓ {test['can']} -> {matched_can_rule.get('action_result')}")
            passed += 1
        else:
            actual = matched_can_rule.get("action_result") if matched_can_rule else "None"
            print(f"✗ {test['can']} -> Expected: {test['expected']}, Got: {actual}")
            failed += 1
    
    print(f"\nCan Decision: {passed} passed, {failed} failed")
    return failed == 0


def test_chi_decision():
    """Test the Chi decision (maps earthly branches to elements)."""
    print("\n" + "=" * 80)
    print("TESTING: Chi Decision")
    print("=" * 80)
    
    dmn_file = "Tương Sinh Tương Khắc.dmn"
    # Note: "ty" appears twice in the DMN (water and fire), we'll test the first one
    test_cases = [
        {"chi": "ty", "expected": "water"},  # First occurrence
        {"chi": "suu", "expected": "earth"},
        {"chi": "dan", "expected": "wood"},
        {"chi": "meo", "expected": "wood"},
        {"chi": "thin", "expected": "earth"},
        {"chi": "ngo", "expected": "fire"},
        {"chi": "mui", "expected": "earth"},
        {"chi": "than", "expected": "metal"},
        {"chi": "dau", "expected": "metal"},
        {"chi": "tuat", "expected": "earth"},
        {"chi": "hoi", "expected": "water"},
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = dmn_rules_exec(dmn_file=dmn_file, data={"chi": test["chi"]}, dry_run=True)
        
        # Find matched "Chi" rules (there might be multiple for "ty")
        matched_chi_rules = [r for r in result.get("would_match", []) if "Chi" in r.get("rule_name", "")]
        
        # Check if any matched rule has the expected result
        found = False
        for rule in matched_chi_rules:
            if rule.get("action_result") == test["expected"]:
                print(f"✓ {test['chi']} -> {rule.get('action_result')}")
                passed += 1
                found = True
                break
        
        if not found:
            actuals = [r.get("action_result") for r in matched_chi_rules]
            print(f"✗ {test['chi']} -> Expected: {test['expected']}, Got: {actuals}")
            failed += 1
    
    print(f"\nChi Decision: {passed} passed, {failed} failed")
    return failed == 0


def test_ngu_hanh_decision():
    """Test the Ngu Hanh decision (element compatibility scores)."""
    print("\n" + "=" * 80)
    print("TESTING: Ngu Hanh Decision (Element Compatibility)")
    print("=" * 80)
    
    dmn_file = "Tương Sinh Tương Khắc.dmn"
    
    # Test cases: element_1-element_2 -> expected_score
    # Based on DMN rules: element_1 generates/restricts element_2
    test_cases = [
        # Generation rules (score = 1)
        {"element_1": "metal", "element_2": "water", "expected": "1", "desc": "metal generates water"},
        {"element_1": "wood", "element_2": "fire", "expected": "1", "desc": "wood generates fire"},
        {"element_1": "water", "element_2": "wood", "expected": "1", "desc": "water generates wood"},
        {"element_1": "fire", "element_2": "earth", "expected": "1", "desc": "fire generates earth"},
        {"element_1": "earth", "element_2": "metal", "expected": "1", "desc": "earth generates metal"},
        
        # Restriction rules (score = -1)
        {"element_1": "metal", "element_2": "wood", "expected": "-1", "desc": "metal restricts wood"},
        {"element_1": "wood", "element_2": "earth", "expected": "-1", "desc": "wood restricts earth"},
        {"element_1": "water", "element_2": "fire", "expected": "-1", "desc": "water restricts fire"},
        {"element_1": "fire", "element_2": "metal", "expected": "-1", "desc": "fire restricts metal"},
        {"element_1": "earth", "element_2": "water", "expected": "-1", "desc": "earth restricts water"},
        
        # Same element (score = 0) - these rules check element_1 with empty element_2
        {"element_1": "metal", "element_2": "", "expected": "0", "desc": "metal-metal (same)"},
        {"element_1": "wood", "element_2": "", "expected": "0", "desc": "wood-wood (same)"},
        {"element_1": "water", "element_2": "", "expected": "0", "desc": "water-water (same)"},
        {"element_1": "fire", "element_2": "", "expected": "0", "desc": "fire-fire (same)"},
        {"element_1": "earth", "element_2": "", "expected": "0", "desc": "earth-earth (same)"},
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        data = {"element_1": test["element_1"]}
        if test["element_2"]:
            data["element_2"] = test["element_2"]
        
        result = dmn_rules_exec(dmn_file=dmn_file, data=data, dry_run=True)
        
        # Find matched "Ngu Hanh" rule
        matched_rule = None
        for rule in result.get("would_match", []):
            if "Ngu Hanh" in rule.get("rule_name", ""):
                action_result = rule.get("action_result", "")
                if action_result in ["-1", "0", "1"]:
                    matched_rule = rule
                    break
        
        if matched_rule and matched_rule.get("action_result") == test["expected"]:
            print(f"✓ {test['element_1']}-{test['element_2'] or 'same'} -> {matched_rule.get('action_result')} ({test['desc']})")
            passed += 1
        else:
            actual = matched_rule.get("action_result") if matched_rule else "None"
            print(f"✗ {test['element_1']}-{test['element_2'] or 'same'} -> Expected: {test['expected']}, Got: {actual} ({test['desc']})")
            if matched_rule:
                print(f"    Condition: {matched_rule.get('condition')}")
            failed += 1
    
    print(f"\nNgu Hanh Decision: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TESTING DMN RULES: Tương Sinh Tương Khắc")
    print("=" * 80)
    
    results = []
    results.append(("Can Decision", test_can_decision()))
    results.append(("Chi Decision", test_chi_decision()))
    results.append(("Ngu Hanh Decision", test_ngu_hanh_decision()))
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
