import pytest
from app.verification.rules import (
    FileIntegrityRule,
    SchemaAndFieldRule,
    IndependentCalculationRule,
    DocumentStructureRule
)
from app.verification.engine import verifier
from app.models.schemas import TaskDefinition, VerificationStatus
from app.core.config import settings

def test_file_integrity_rule():
    # 1. Non-existent file
    res_fail = FileIntegrityRule.verify("ghost_file_123.pdf")
    assert res_fail.passed is False

    # 2. Real file
    test_file = settings.WORKSPACE_DIR / "real_file.txt"
    with open(test_file, "w") as f:
        f.write("Valid content with sufficient bytes.")

    res_pass = FileIntegrityRule.verify(str(test_file), min_bytes=5)
    assert res_pass.passed is True

def test_schema_and_field_rule():
    data = [{"quarter": "Q1", "revenue": 1000.0, "expenses": 600.0}]
    
    # Missing field
    res_fail = SchemaAndFieldRule.verify(data, expected_fields=["quarter", "non_existent_field"])
    assert res_fail.passed is False
    assert "non_existent_field" in res_fail.message

    # All fields present
    res_pass = SchemaAndFieldRule.verify(data, expected_fields=["quarter", "revenue"])
    assert res_pass.passed is True

def test_independent_calculation_rule_discrepancy_detection():
    # Source data sum is 500
    records = [
        {"revenue": 200.0},
        {"revenue": 300.0}
    ]

    # Correct claimed total
    res_pass = IndependentCalculationRule.verify(records, {"total_revenue": 500.0})
    assert res_pass.passed is True

    # Deliberate calculation error / fraud / discrepancy: Claimed 999.0
    res_fail = IndependentCalculationRule.verify(records, {"total_revenue": 999.0})
    assert res_fail.passed is False
    assert "Mismatch" in res_fail.message
    assert "500.00" in res_fail.message

def test_verification_engine():
    task = TaskDefinition(
        task_id="task_calc",
        title="Totals",
        tool_name="data_calculate_statistics",
        verification_criteria={
            "calculation_check": {"tolerance": 0.01}
        }
    )
    context = {
        "combined_records": [{"revenue": 100.0}, {"revenue": 200.0}]
    }
    tool_output = {
        "totals": {"total_revenue": 300.0}
    }

    verif_res = verifier.verify_task(task, "wf_test", tool_output, context)
    assert verif_res.status == VerificationStatus.PASSED
    assert verif_res.checks_passed > 0
    assert len(verif_res.detected_errors) == 0
