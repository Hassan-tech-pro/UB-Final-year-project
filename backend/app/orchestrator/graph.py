import time
import json
import re
import logging
from typing import Any, Optional, Literal
from pathlib import Path
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END

from .state import OrchestratorState
from ..planner.planner import planner
from ..planner.replanner import replanner
from ..tools.registry import registry
from ..verification.engine import verifier
from ..recovery.recovery_manager import recovery_manager, RecoveryActionType
from ..core.database import db
from ..core.config import settings
from ..models.schemas import TaskStatus, VerificationStatus, TaskDefinition, ExecutionPlan

logger = logging.getLogger(__name__)

def resolve_template_vars(param_val: Any, task_results: dict[str, Any]) -> Any:
    """
    Recursively resolves template expressions like '{{task_1.records}}'
    or '{{task_2.totals}}' by pulling from previous task results.
    """
    if isinstance(param_val, str):
        # Match single whole placeholder {{task_id.attr}}
        whole_match = re.fullmatch(r'\{\{([\w_]+)(?:\.([\w_]+))?\}\}', param_val.strip())
        if whole_match:
            t_id, attr = whole_match.groups()
            res = task_results.get(t_id, {})
            if attr:
                if isinstance(res, dict):
                    return res.get(attr)
                return getattr(res, attr, None)
            return res

        # Match inline placeholders in text
        def replace_fn(m):
            t_id, attr = m.groups()
            res = task_results.get(t_id, {})
            val = res.get(attr, "") if isinstance(res, dict) and attr else res
            return str(val)

        return re.sub(r'\{\{([\w_]+)(?:\.([\w_]+))?\}\}', replace_fn, param_val)

    elif isinstance(param_val, list):
        return [resolve_template_vars(item, task_results) for item in param_val]
    elif isinstance(param_val, dict):
        return {k: resolve_template_vars(v, task_results) for k, v in param_val.items()}
    return param_val


def plan_node(state: OrchestratorState) -> dict[str, Any]:
    """Generates the execution plan from objective and uploaded files."""
    workflow_id = state["workflow_id"]
    objective = state["objective"]
    uploaded_files = state["uploaded_files"]

    db.add_log(workflow_id, "INFO", f"Analyzing objective: '{objective}'")
    db.update_workflow_status(workflow_id, "RUNNING")

    plan: ExecutionPlan = planner.generate_plan(workflow_id, objective, uploaded_files)
    plan_dict = plan.model_dump()

    task_order = [t.task_id for t in plan.tasks]
    task_statuses = {t.task_id: TaskStatus.PENDING.value for t in plan.tasks}
    retry_counts = {t.task_id: 0 for t in plan.tasks}

    # Persist tasks to database
    for t in plan.tasks:
        db.upsert_task({
            "workflow_id": workflow_id,
            "task_id": t.task_id,
            "task_order": t.task_order,
            "title": t.title,
            "description": t.description,
            "tool_name": t.tool_name,
            "status": TaskStatus.PENDING.value,
            "dependencies": t.dependencies,
            "parameters": t.parameters,
            "expected_output": t.expected_output,
            "verification_criteria": t.verification_criteria
        })

    db.add_log(workflow_id, "INFO", f"Plan generated with {len(plan.tasks)} structured tasks.")
    db.update_workflow_status(workflow_id, "RUNNING", plan_json=json.dumps(plan_dict), total_tasks=len(plan.tasks))

    return {
        "plan": plan_dict,
        "task_order": task_order,
        "task_statuses": task_statuses,
        "retry_counts": retry_counts,
        "status": "RUNNING"
    }


def select_next_task_node(state: OrchestratorState) -> dict[str, Any]:
    """Finds the next executable task whose dependencies have completed."""
    plan_tasks = state["plan"]["tasks"]
    completed_ids = set(state.get("completed_task_ids", []))
    task_statuses = dict(state.get("task_statuses", {}))

    next_task_id = None
    for task_dict in plan_tasks:
        t_id = task_dict["task_id"] if isinstance(task_dict, dict) else task_dict.task_id
        status = task_statuses.get(t_id, TaskStatus.PENDING.value)

        # Candidate if pending or retrying
        if status in [TaskStatus.PENDING.value, TaskStatus.RETRYING.value]:
            deps = task_dict.get("dependencies", []) if isinstance(task_dict, dict) else task_dict.dependencies
            # Check if all dependencies are satisfied
            if all(d in completed_ids for d in deps):
                next_task_id = t_id
                break

    return {
        "current_task_id": next_task_id
    }


def should_continue(state: OrchestratorState) -> Literal["execute_task", "finalize"]:
    """Conditional edge: determines if another task is ready or if workflow is complete."""
    if state.get("current_task_id"):
        return "execute_task"
    return "finalize"


def execute_task_node(state: OrchestratorState) -> dict[str, Any]:
    """Resolves inputs, executes the selected tool, and captures outputs."""
    workflow_id = state["workflow_id"]
    task_id = state["current_task_id"]
    plan_tasks = state["plan"]["tasks"]
    task_results = dict(state.get("task_results", {}))
    task_statuses = dict(state.get("task_statuses", {}))

    # Retrieve current task definition
    task_dict = next(t for t in plan_tasks if (t["task_id"] if isinstance(t, dict) else t.task_id) == task_id)
    tool_name = task_dict["tool_name"] if isinstance(task_dict, dict) else task_dict.tool_name
    raw_params = task_dict.get("parameters", {}) if isinstance(task_dict, dict) else task_dict.parameters
    task_title = task_dict.get("title", "") if isinstance(task_dict, dict) else task_dict.title

    # Mark RUNNING
    task_statuses[task_id] = TaskStatus.RUNNING.value
    db.upsert_task({
        "workflow_id": workflow_id,
        "task_id": task_id,
        "status": TaskStatus.RUNNING.value
    })
    db.add_log(workflow_id, "INFO", f"Executing task '{task_id}': {task_title} using tool '{tool_name}'", task_id=task_id)

    # Resolve variables from upstream outputs
    resolved_params = resolve_template_vars(raw_params, task_results)

    # Execute tool
    exec_res = registry.execute(tool_name, **resolved_params)

    # Log tool call in DB
    db.log_tool_call({
        "id": f"tc_{task_id}_{int(time.time()*1000)}",
        "task_id": task_id,
        "workflow_id": workflow_id,
        "tool_name": tool_name,
        "input_params": resolved_params,
        "output_data": exec_res.data if exec_res.success else {"error": exec_res.error},
        "success": exec_res.success,
        "error_message": exec_res.error,
        "duration_ms": exec_res.execution_time_ms
    })

    if exec_res.success:
        task_results[task_id] = exec_res.data
        return {
            "task_results": task_results,
            "task_statuses": task_statuses,
            "error": None
        }
    else:
        task_errors = dict(state.get("task_errors", {}))
        task_errors[task_id] = exec_res.error or "Tool execution failed"
        return {
            "task_statuses": task_statuses,
            "task_errors": task_errors,
            "error": exec_res.error
        }


def verify_task_node(state: OrchestratorState) -> dict[str, Any]:
    """Runs rigorous verification on task output."""
    workflow_id = state["workflow_id"]
    task_id = state["current_task_id"]
    plan_tasks = state["plan"]["tasks"]
    task_dict = next(t for t in plan_tasks if (t["task_id"] if isinstance(t, dict) else t.task_id) == task_id)
    task_obj = TaskDefinition(**task_dict) if isinstance(task_dict, dict) else task_dict

    task_results = state.get("task_results", {})
    output_data = task_results.get(task_id)
    completed_task_ids = list(state.get("completed_task_ids", []))
    task_statuses = dict(state.get("task_statuses", {}))
    verifications = list(state.get("verifications", []))
    artifacts = list(state.get("artifacts", []))

    # Verification context - find source records from upstream tasks
    combined_records = None
    for upstream_res in task_results.values():
        if isinstance(upstream_res, dict) and "records" in upstream_res and upstream_res["records"]:
            combined_records = upstream_res["records"]

    context = {
        "objective": state["objective"],
        "combined_records": combined_records,
        "records": output_data.get("records") if isinstance(output_data, dict) else None
    }

    # Run verification engine
    verif_res = verifier.verify_task(task_obj, workflow_id, output_data, context)
    verif_dict = verif_res.model_dump()
    verifications.append(verif_dict)
    db.save_verification(verif_dict)

    if verif_res.status in [VerificationStatus.PASSED, VerificationStatus.WARNING]:
        task_statuses[task_id] = TaskStatus.COMPLETED.value
        completed_task_ids.append(task_id)

        # Check if an artifact was generated
        if isinstance(output_data, dict) and "file_path" in output_data:
            fp = Path(output_data["file_path"])
            if fp.exists():
                artifact_entry = {
                    "id": f"art_{int(time.time()*1000)}",
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "filename": fp.name,
                    "file_path": str(fp),
                    "file_size": fp.stat().st_size,
                    "file_type": fp.suffix.lower(),
                    "download_url": f"/api/files/download/{fp.name}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                artifacts.append(artifact_entry)
                db.save_artifact(artifact_entry)
                db.add_log(workflow_id, "INFO", f"Artifact created: {fp.name} ({fp.stat().st_size} bytes)", task_id=task_id)

        db.upsert_task({
            "workflow_id": workflow_id,
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value,
            "actual_output": output_data
        })
        db.add_log(workflow_id, "INFO", f"Task '{task_id}' verified: {verif_res.actual_result}", task_id=task_id)

        return {
            "task_statuses": task_statuses,
            "completed_task_ids": completed_task_ids,
            "verifications": verifications,
            "artifacts": artifacts,
            "error": None
        }
    else:
        # Verification failed
        task_statuses[task_id] = TaskStatus.FAILED.value
        task_errors = dict(state.get("task_errors", {}))
        task_errors[task_id] = verif_res.explanation
        db.upsert_task({
            "workflow_id": workflow_id,
            "task_id": task_id,
            "status": TaskStatus.FAILED.value,
            "error_message": verif_res.explanation
        })
        db.add_log(workflow_id, "WARNING", f"Verification failed for '{task_id}': {verif_res.explanation}", task_id=task_id)

        return {
            "task_statuses": task_statuses,
            "verifications": verifications,
            "task_errors": task_errors,
            "error": verif_res.explanation
        }


def check_verification_outcome(state: OrchestratorState) -> Literal["select_next_task", "recover_task"]:
    """Determines whether to proceed to next task or attempt recovery."""
    task_id = state.get("current_task_id")
    status = state.get("task_statuses", {}).get(task_id)
    if status == TaskStatus.COMPLETED.value:
        return "select_next_task"
    return "recover_task"


def recover_task_node(state: OrchestratorState) -> dict[str, Any]:
    """Evaluates failure cause and triggers retry, tool fallback, or plan mutation."""
    workflow_id = state["workflow_id"]
    task_id = state["current_task_id"]
    plan_dict = state["plan"]
    plan_obj = ExecutionPlan(**plan_dict)
    task_obj = next(t for t in plan_obj.tasks if t.task_id == task_id)
    if isinstance(task_obj, dict):
        task_obj = TaskDefinition(**task_obj)

    error_msg = state.get("error") or state.get("task_errors", {}).get(task_id, "Unknown error")
    recent_verif = None
    if state.get("verifications"):
        recent_verif = verifier.verify_task(task_obj, workflow_id, {}, {})

    retry_counts = dict(state.get("retry_counts", {}))
    task_obj.retry_count = retry_counts.get(task_id, 0)

    decision = recovery_manager.formulate_recovery_plan(
        task_obj,
        error_msg,
        verification=recent_verif,
        execution_context={"state": state}
    )

    db.add_log(workflow_id, "WARNING", f"Recovery decision for '{task_id}': {decision.explanation}", task_id=task_id)

    if decision.can_retry:
        retry_counts[task_id] = task_obj.retry_count + 1
        updated_plan = replanner.replan_workflow(plan_obj, task_id, decision, {"state": state})
        task_statuses = dict(state.get("task_statuses", {}))
        task_statuses[task_id] = TaskStatus.RETRYING.value
        
        db.upsert_task({
            "workflow_id": workflow_id,
            "task_id": task_id,
            "status": TaskStatus.RETRYING.value,
            "retry_count": retry_counts[task_id],
            "parameters": decision.modified_parameters
        })

        return {
            "plan": updated_plan.model_dump(),
            "retry_counts": retry_counts,
            "task_statuses": task_statuses,
            "error": None
        }
    else:
        # Cannot recover
        task_statuses = dict(state.get("task_statuses", {}))
        task_statuses[task_id] = TaskStatus.FAILED.value
        db.add_log(workflow_id, "ERROR", f"Recovery exhausted for '{task_id}'. Workflow halting.", task_id=task_id)
        return {
            "task_statuses": task_statuses,
            "status": "FAILED",
            "error": decision.explanation
        }


def check_recovery_outcome(state: OrchestratorState) -> Literal["execute_task", "finalize"]:
    """If recovery allowed retry, re-execute the task; otherwise finalize/fail."""
    task_id = state.get("current_task_id")
    status = state.get("task_statuses", {}).get(task_id)
    if status == TaskStatus.RETRYING.value:
        return "execute_task"
    return "finalize"


def finalize_node(state: OrchestratorState) -> dict[str, Any]:
    """Finalizes workflow metrics, durations, and state in SQLite."""
    workflow_id = state["workflow_id"]
    completed = state.get("completed_task_ids", [])
    total_tasks = len(state.get("plan", {}).get("tasks", []))
    failed_tasks = [t for t, s in state.get("task_statuses", {}).items() if s == TaskStatus.FAILED.value]

    start_time = state.get("start_time", time.time())
    duration_sec = round(time.time() - start_time, 2)

    final_status = "COMPLETED" if (len(completed) == total_tasks and len(failed_tasks) == 0) else "FAILED"
    
    db.update_workflow_status(
        workflow_id=workflow_id,
        status=final_status,
        total_tasks=total_tasks,
        completed_tasks=len(completed),
        failed_tasks=len(failed_tasks),
        duration_seconds=duration_sec
    )
    db.add_log(workflow_id, "INFO", f"Workflow finalized with status '{final_status}' in {duration_sec}s. Completed {len(completed)}/{total_tasks} tasks.")

    return {
        "status": final_status,
        "duration_seconds": duration_sec
    }


def create_agent_graph() -> Any:
    """Builds and compiles the stateful LangGraph orchestration graph."""
    graph = StateGraph(OrchestratorState)

    # Add Nodes
    graph.add_node("plan_node", plan_node)
    graph.add_node("select_next_task_node", select_next_task_node)
    graph.add_node("execute_task_node", execute_task_node)
    graph.add_node("verify_task_node", verify_task_node)
    graph.add_node("recover_task_node", recover_task_node)
    graph.add_node("finalize_node", finalize_node)

    # Add Edges
    graph.add_edge(START, "plan_node")
    graph.add_edge("plan_node", "select_next_task_node")

    # Conditional edge from select_next_task_node
    graph.add_conditional_edges(
        "select_next_task_node",
        should_continue,
        {
            "execute_task": "execute_task_node",
            "finalize": "finalize_node"
        }
    )

    graph.add_edge("execute_task_node", "verify_task_node")

    # Conditional edge from verify_task_node
    graph.add_conditional_edges(
        "verify_task_node",
        check_verification_outcome,
        {
            "select_next_task": "select_next_task_node",
            "recover_task": "recover_task_node"
        }
    )

    # Conditional edge from recover_task_node
    graph.add_conditional_edges(
        "recover_task_node",
        check_recovery_outcome,
        {
            "execute_task": "execute_task_node",
            "finalize": "finalize_node"
        }
    )

    graph.add_edge("finalize_node", END)

    return graph.compile()
