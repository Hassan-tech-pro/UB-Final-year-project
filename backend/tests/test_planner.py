import pytest
from app.planner.planner import planner

def test_planner_generates_valid_execution_plan():
    objective = "Extract data from three PDF reports, organize it into Excel, calculate totals, and generate a summary report."
    plan = planner.generate_plan(
        workflow_id="wf_test_plan",
        objective=objective,
        uploaded_files=["Q1.pdf", "Q2.pdf", "Q3.pdf"]
    )

    assert plan.workflow_id == "wf_test_plan"
    assert len(plan.tasks) >= 6
    assert plan.tasks[0].tool_name == "pdf_extract_text"
    assert any(t.tool_name == "generate_excel_report" for t in plan.tasks)
    assert any(t.tool_name == "generate_pdf_report" for t in plan.tasks)

    # Verify dependencies are ordered
    task_ids = [t.task_id for t in plan.tasks]
    for task in plan.tasks:
        for dep in task.dependencies:
            assert dep in task_ids
            # Dependency must appear earlier in sequence
            assert task_ids.index(dep) < task_ids.index(task.task_id)
