from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"

class VerificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    PENDING = "PENDING"

class TaskDefinition(BaseModel):
    task_id: str
    task_order: int = 0
    title: str
    description: str = ""
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    verification_criteria: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    actual_output: Optional[dict[str, Any]] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0

class ExecutionPlan(BaseModel):
    workflow_id: str
    objective: str
    reasoning: str = ""
    tasks: list[TaskDefinition] = Field(default_factory=list)
    uploaded_files: list[str] = Field(default_factory=list)

class ToolCallResult(BaseModel):
    id: str
    task_id: str
    workflow_id: str
    tool_name: str
    input_params: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    success: bool
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: str

class VerificationResult(BaseModel):
    id: str
    task_id: str
    workflow_id: str
    status: VerificationStatus
    expected_result: str = ""
    actual_result: str = ""
    checks_passed: int = 0
    checks_failed: int = 0
    detected_errors: list[str] = Field(default_factory=list)
    explanation: str = ""
    suggested_recovery: Optional[str] = None
    timestamp: str

class ArtifactInfo(BaseModel):
    id: str
    workflow_id: str
    task_id: Optional[str] = None
    filename: str
    file_path: str
    file_size: int = 0
    file_type: str = ""
    download_url: str = ""
    created_at: str

class ExecutionLogEntry(BaseModel):
    workflow_id: str
    task_id: Optional[str] = None
    level: str = "INFO"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str

class WorkflowResponse(BaseModel):
    id: str
    objective: str
    status: str
    plan: Optional[ExecutionPlan] = None
    tasks: list[TaskDefinition] = Field(default_factory=list)
    tool_calls: list[ToolCallResult] = Field(default_factory=list)
    verifications: list[VerificationResult] = Field(default_factory=list)
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    logs: list[ExecutionLogEntry] = Field(default_factory=list)
    duration_seconds: float = 0.0
    created_at: str
    updated_at: str

class CreateWorkflowRequest(BaseModel):
    objective: str
    file_ids: list[str] = Field(default_factory=list)

class EvaluationMetrics(BaseModel):
    task_completion_rate: float = 0.0
    planning_accuracy: float = 0.0
    tool_selection_accuracy: float = 0.0
    execution_success_rate: float = 0.0
    verification_accuracy: float = 0.0
    error_recovery_rate: float = 0.0
    average_execution_time_sec: float = 0.0
    total_retries: int = 0
    overall_workflow_success_rate: float = 0.0

class BenchmarkResult(BaseModel):
    id: str
    suite_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    metrics: EvaluationMetrics
    scenario_results: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
