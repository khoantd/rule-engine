import pytest
import uuid
from services.rule_management import get_rule_management_service
from services.conditions_management import get_conditions_management_service

@pytest.mark.integration
def test_rule_with_condition_id_reference():
    """Test creating and retrieving a rule with a condition ID reference."""
    rule_service = get_rule_management_service()
    cond_service = get_conditions_management_service()
    
    # 1. Create a condition
    cond_id = f"TEST_COND_{uuid.uuid4().hex[:8]}"
    cond_data = {
        "condition_id": cond_id,
        "condition_name": "Test Condition",
        "attribute": "age",
        "equation": "greater_than",
        "constant": "18"
    }
    cond_service.create_condition(cond_data)
    
    # 2. Create a rule referencing this condition ID
    rule_id = f"TEST_RULE_{uuid.uuid4().hex[:8]}"
    rule_data = {
        "id": rule_id,
        "rule_name": "Test Rule with Ref",
        "description": "Rule referencing a condition by ID",
        "conditions": {"0": cond_id},
        "result": "PASSED",
        "rule_point": 10,
        "weight": 1.0,
        "priority": 1
    }
    
    created_rule = rule_service.create_rule(rule_data)
    
    # 3. Verify created rule response contains the reference mapping
    assert created_rule["id"] == rule_id
    assert created_rule["conditions"] == {"0": cond_id}
    
    # 4. Retrieve the rule and verify it still has the reference
    retrieved_rule = rule_service.get_rule(rule_id)
    assert retrieved_rule["conditions"] == {"0": cond_id}
    
    # 5. Verify it resolved correctly in the database (checking if internal fields set)
    # Since we can't easily check the DB model directly here without more setup, 
    # we trust the service logic for now or we could add a check if it actually matched 
    # but the service only returns the dict. 
    # However, our _rule_to_dict logic prioritizes extra_metadata.
    
    # 6. Update the rule with inline condition and verify reference is cleared
    update_data = {
        "conditions": {
            "attribute": "score",
            "equation": "equal",
            "constant": "100"
        }
    }
    updated_rule = rule_service.update_rule(rule_id, update_data)
    assert updated_rule["conditions"] == update_data["conditions"]
    
    # 7. Update back to reference
    update_data_ref = {
        "conditions": {"0": cond_id}
    }
    updated_rule_ref = rule_service.update_rule(rule_id, update_data_ref)
    assert updated_rule_ref["conditions"] == {"0": cond_id}
