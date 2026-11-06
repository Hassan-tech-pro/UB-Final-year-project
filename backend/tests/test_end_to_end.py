import pytest
import asyncio
import uuid
from app.orchestrator.engine import engine
from app.core.database import db
from app.core.config import settings
from app.evaluation.benchmark_suite import benchmark_suite

@pytest.mark.asyncio
async def test_end_to_end_workflow_example():
    # Ensure sample PDFs exist
    benchmark_suite.ensure_sample_files()

    workflow_id = f"test_e2e_run_{uuid.uuid4().hex[:8]}"
    objective = "Extract data from three PDF reports, organize it into Excel, calculate totals, and generate a summary report."
    uploaded = [
        str(settings.SAMPLE_DATA_DIR / "Q1_Financial_Report.pdf"),
        str(settings.SAMPLE_DATA_DIR / "Q2_Financial_Report.pdf"),
        str(settings.SAMPLE_DATA_DIR / "Q3_Financial_Report.pdf")
    ]

    task = await engine.start_workflow(workflow_id, objective, uploaded)
    await task

    # Verify workflow state in SQLite
    wf = db.get_workflow(workflow_id)
    assert wf is not None
    assert wf["status"] == "COMPLETED"
    assert wf["completed_tasks"] >= 6
    assert wf["failed_tasks"] == 0

    # Verify artifacts
    artifacts = db.get_workflow_artifacts(workflow_id)
    assert len(artifacts) >= 2
    extensions = [a["file_type"] for a in artifacts]
    assert ".xlsx" in extensions
    assert ".pdf" in extensions

    # Verify verifications were performed
    verifs = db.get_workflow_verifications(workflow_id)
    assert len(verifs) >= 6
    assert all(v["status"] in ["PASSED", "WARNING"] for v in verifs)
