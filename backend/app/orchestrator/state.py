from typing import Any, Optional, TypedDict

class OrchestratorState(TypedDict):
    workflow_id: str
    objective: str
    uploaded_files: list[str]
    plan: Optional[dict[str, Any]]
    current_task_id: Optional[str]
    task_order: list[str]
    completed_task_ids: list[str]
    task_results: dict[str, Any]
    task_statuses: dict[str, str]
    task_errors: dict[str, str]
    retry_counts: dict[str, int]
    verifications: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    logs: list[dict[str, Any]]
    status: str
    error: Optional[str]
    start_time: float
    duration_seconds: float
