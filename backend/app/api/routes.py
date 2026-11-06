import os
import shutil
import uuid
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse

from ..core.config import settings
from ..core.security import SecurityManager, SecurityError
from ..core.database import db
from ..tools.registry import registry
from ..orchestrator.engine import engine
from ..evaluation.benchmark_suite import benchmark_suite
from ..models.schemas import (
    WorkflowResponse,
    CreateWorkflowRequest,
    ExecutionPlan,
    TaskDefinition,
    ToolCallResult,
    VerificationResult,
    ArtifactInfo,
    ExecutionLogEntry,
    BenchmarkResult
)

logger = logging.getLogger(__name__)
api_router = APIRouter()

# Workflows Endpoints
@api_router.post("/workflows", response_model=dict)
async def create_and_run_workflow(
    objective: str = Form(...),
    files: list[UploadFile] = File(default=[])
):
    """Initiates an autonomous Agentic AI workflow with uploaded files."""
    workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
    uploaded_file_paths = []

    # Handle file uploads
    for file in files:
        if file.filename:
            sanitized = SecurityManager.sanitize_filename(file.filename)
            SecurityManager.validate_file_extension(sanitized)
            save_path = settings.UPLOAD_DIR / f"{workflow_id}_{sanitized}"
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_file_paths.append(str(save_path))

    # If no files were uploaded and prompt mentions PDFs, attach sample data PDFs
    if not uploaded_file_paths and any(k in objective.lower() for k in ["pdf", "report", "extract", "quarter"]):
        benchmark_suite.ensure_sample_files()
        uploaded_file_paths = [
            str(settings.SAMPLE_DATA_DIR / "Q1_Financial_Report.pdf"),
            str(settings.SAMPLE_DATA_DIR / "Q2_Financial_Report.pdf"),
            str(settings.SAMPLE_DATA_DIR / "Q3_Financial_Report.pdf")
        ]

    # Start async LangGraph execution
    await engine.start_workflow(workflow_id, objective, uploaded_file_paths)

    return {
        "workflow_id": workflow_id,
        "objective": objective,
        "uploaded_files_count": len(uploaded_file_paths),
        "status": "RUNNING"
    }


@api_router.get("/workflows", response_model=list[dict])
def list_workflows(limit: int = Query(default=20, le=100)):
    """Lists recent workflows with high-level statistics."""
    return db.list_workflows(limit=limit)


@api_router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow_details(workflow_id: str):
    """Retrieves full workflow execution tree: plan, tasks, tool calls, verifications, artifacts, and logs."""
    wf = db.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    tasks_raw = db.get_workflow_tasks(workflow_id)
    tasks = [TaskDefinition(**t) for t in tasks_raw]

    tool_calls_raw = db.get_workflow_tool_calls(workflow_id)
    tool_calls = [ToolCallResult(**tc) for tc in tool_calls_raw]

    verifs_raw = db.get_workflow_verifications(workflow_id)
    verifications = [VerificationResult(**v) for v in verifs_raw]

    artifacts_raw = db.get_workflow_artifacts(workflow_id)
    artifacts = [
        ArtifactInfo(
            id=a["id"],
            workflow_id=a["workflow_id"],
            task_id=a.get("task_id"),
            filename=a["filename"],
            file_path=a["file_path"],
            file_size=a["file_size"],
            file_type=a.get("file_type", ""),
            download_url=f"/api/files/download/{a['filename']}",
            created_at=a["created_at"]
        ) for a in artifacts_raw
    ]

    logs_raw = db.get_workflow_logs(workflow_id)
    logs = [ExecutionLogEntry(**l) for l in logs_raw]

    plan_data = None
    if wf.get("plan_json"):
        try:
            plan_data = ExecutionPlan(**json.loads(wf["plan_json"]))
        except Exception:
            pass

    return WorkflowResponse(
        id=wf["id"],
        objective=wf["objective"],
        status=wf["status"],
        plan=plan_data,
        tasks=tasks,
        tool_calls=tool_calls,
        verifications=verifications,
        artifacts=artifacts,
        logs=logs,
        duration_seconds=wf.get("duration_seconds", 0.0),
        created_at=wf["created_at"],
        updated_at=wf["updated_at"]
    )


@api_router.post("/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str):
    """Cancels a currently active workflow."""
    success = engine.cancel_workflow(workflow_id)
    return {"workflow_id": workflow_id, "cancelled": success}


# File Management
@api_router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a single file safely into the uploads directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    sanitized = SecurityManager.sanitize_filename(file.filename)
    SecurityManager.validate_file_extension(sanitized)
    save_path = settings.UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{sanitized}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": sanitized,
        "saved_path": str(save_path),
        "file_size": save_path.stat().st_size
    }


@api_router.get("/files/download/{filename}")
def download_artifact(filename: str):
    """Securely downloads generated report or artifact."""
    sanitized = SecurityManager.sanitize_filename(filename)

    # Search in artifacts or workspace
    potential_paths = [
        settings.ARTIFACT_DIR / sanitized,
        settings.WORKSPACE_DIR / sanitized,
        settings.SAMPLE_DATA_DIR / sanitized
    ]

    for p in potential_paths:
        if p.exists() and p.is_file():
            safe_p = SecurityManager.resolve_safe_path(p)
            return FileResponse(
                path=str(safe_p),
                filename=sanitized,
                media_type="application/octet-stream"
            )

    raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")


@api_router.get("/sample-files")
def get_sample_files():
    """Lists preloaded sample financial reports and data files."""
    benchmark_suite.ensure_sample_files()
    files = []
    for f in settings.SAMPLE_DATA_DIR.glob("*.*"):
        if f.is_file():
            files.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "type": f.suffix.lower()
            })
    return files


# Tools Catalog
@api_router.get("/tools")
def list_available_tools():
    """Returns the registered tool catalog with parameters and schema descriptions."""
    return [t.model_dump() for t in registry.list_tools()]


# Evaluation Suite Endpoints
@api_router.post("/evaluation/run", response_model=BenchmarkResult)
async def run_evaluation_benchmark():
    """Executes the 10-scenario benchmark evaluation suite."""
    return await benchmark_suite.run_all()


@api_router.get("/evaluation/history")
def list_evaluation_history(limit: int = 10):
    """Retrieves previous benchmark evaluation runs."""
    return db.list_evaluations(limit=limit)
