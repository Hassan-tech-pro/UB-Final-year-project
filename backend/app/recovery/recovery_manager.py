import logging
from enum import Enum
from typing import Any, Optional
from ..models.schemas import TaskDefinition, TaskStatus, VerificationResult
from ..core.config import settings

logger = logging.getLogger(__name__)

class ErrorCategory(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    CALCULATION_DISCREPANCY = "CALCULATION_DISCREPANCY"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    UNKNOWN = "UNKNOWN"

class RecoveryActionType(str, Enum):
    RETRY_WITH_MODIFIED_PARAMS = "RETRY_WITH_MODIFIED_PARAMS"
    FALLBACK_TOOL = "FALLBACK_TOOL"
    REPLAN_DEPENDENTS = "REPLAN_DEPENDENTS"
    FAIL_AND_ALERT_USER = "FAIL_AND_ALERT_USER"

class RecoveryDecision:
    def __init__(
        self,
        action: RecoveryActionType,
        can_retry: bool,
        explanation: str,
        modified_parameters: Optional[dict[str, Any]] = None,
        alternative_tool: Optional[str] = None,
        replan_required: bool = False
    ):
        self.action = action
        self.can_retry = can_retry
        self.explanation = explanation
        self.modified_parameters = modified_parameters or {}
        self.alternative_tool = alternative_tool
        self.replan_required = replan_required

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "can_retry": self.can_retry,
            "explanation": self.explanation,
            "modified_parameters": self.modified_parameters,
            "alternative_tool": self.alternative_tool,
            "replan_required": self.replan_required
        }


class RecoveryManager:
    # Tool fallback map
    FALLBACK_TOOLS = {
        "generate_excel_report": "excel_write_spreadsheet",
        "excel_write_spreadsheet": "csv_write_data",
        "generate_docx_report": "txt_write_file",
        "data_transform": "data_clean",
        "pdf_extract_text": "file_read"
    }

    @classmethod
    def classify_error(cls, error_msg: str, verification: Optional[VerificationResult] = None) -> ErrorCategory:
        msg = (error_msg or "").lower()
        if verification and verification.detected_errors:
            verif_errs = " ".join(verification.detected_errors).lower()
            msg += f" {verif_errs}"

        if "security" in msg or "escapes" in msg or "access denied" in msg:
            return ErrorCategory.SECURITY_VIOLATION
        if "not found" in msg or "no such file" in msg:
            return ErrorCategory.FILE_NOT_FOUND
        if "math" in msg or "calculation" in msg or "discrepancy" in msg or "mismatch" in msg:
            return ErrorCategory.CALCULATION_DISCREPANCY
        if "schema" in msg or "missing fields" in msg or "item_count" in msg:
            return ErrorCategory.SCHEMA_MISMATCH
        if "verification failed" in msg or (verification and verification.status == "FAILED"):
            return ErrorCategory.VERIFICATION_FAILED
        if "exception" in msg or "error" in msg:
            return ErrorCategory.TOOL_EXECUTION_ERROR
        return ErrorCategory.UNKNOWN

    @classmethod
    def formulate_recovery_plan(
        cls,
        task: TaskDefinition,
        error_msg: str,
        verification: Optional[VerificationResult] = None,
        execution_context: Optional[dict[str, Any]] = None
    ) -> RecoveryDecision:
        """
        Analyzes the task failure and determines the optimal recovery strategy:
        parameter mutation, alternative tool fallback, or re-planning.
        """
        category = cls.classify_error(error_msg, verification)
        current_retries = task.retry_count
        max_retries = settings.MAX_TASK_RETRIES

        # Security violations cannot be retried automatically
        if category == ErrorCategory.SECURITY_VIOLATION:
            return RecoveryDecision(
                action=RecoveryActionType.FAIL_AND_ALERT_USER,
                can_retry=False,
                explanation="Operation aborted due to security sandbox constraint violation."
            )

        # Exceeded retry budget
        if current_retries >= max_retries:
            return RecoveryDecision(
                action=RecoveryActionType.FAIL_AND_ALERT_USER,
                can_retry=False,
                explanation=f"Maximum retry limit ({max_retries}) reached for task '{task.task_id}'. User intervention required."
            )

        # 1. Calculation discrepancy recovery: Mutate parameters to compute from verified raw data
        if category == ErrorCategory.CALCULATION_DISCREPANCY:
            modified_params = dict(task.parameters)
            modified_params["recalculate_from_source"] = True
            modified_params["strict_mode"] = True
            return RecoveryDecision(
                action=RecoveryActionType.RETRY_WITH_MODIFIED_PARAMS,
                can_retry=True,
                explanation="Recalculating totals directly from raw source data to resolve numerical discrepancy.",
                modified_parameters=modified_params
            )

        # 2. Schema mismatch recovery: Relax strictness or broaden extraction fields
        if category == ErrorCategory.SCHEMA_MISMATCH:
            modified_params = dict(task.parameters)
            if "fields" in modified_params:
                # Add default values
                modified_params["allow_defaults"] = True
            return RecoveryDecision(
                action=RecoveryActionType.RETRY_WITH_MODIFIED_PARAMS,
                can_retry=True,
                explanation="Relaxing field extraction constraints to recover missing attributes.",
                modified_parameters=modified_params
            )

        # 3. Tool execution error: Attempt fallback tool if available
        if category in [ErrorCategory.TOOL_EXECUTION_ERROR, ErrorCategory.VERIFICATION_FAILED]:
            fallback_tool = cls.FALLBACK_TOOLS.get(task.tool_name)
            if fallback_tool and current_retries == 1:
                return RecoveryDecision(
                    action=RecoveryActionType.FALLBACK_TOOL,
                    can_retry=True,
                    explanation=f"Primary tool '{task.tool_name}' failed. Falling back to alternative tool '{fallback_tool}'.",
                    alternative_tool=fallback_tool,
                    modified_parameters=dict(task.parameters)
                )
            else:
                # Retry with safe defaults
                modified_params = dict(task.parameters)
                modified_params["retry_attempt"] = current_retries + 1
                return RecoveryDecision(
                    action=RecoveryActionType.RETRY_WITH_MODIFIED_PARAMS,
                    can_retry=True,
                    explanation=f"Retrying task '{task.task_id}' (attempt {current_retries + 1}/{max_retries}).",
                    modified_parameters=modified_params
                )

        # 4. File Not Found: Check if upstream task hasn't finished or path is relative
        if category == ErrorCategory.FILE_NOT_FOUND:
            # Trigger replan to ensure dependencies generated the file
            return RecoveryDecision(
                action=RecoveryActionType.REPLAN_DEPENDENTS,
                can_retry=True,
                explanation=f"Referenced file not located. Triggering re-planning to verify dependency generation.",
                replan_required=True
            )

        # Default retry
        return RecoveryDecision(
            action=RecoveryActionType.RETRY_WITH_MODIFIED_PARAMS,
            can_retry=True,
            explanation=f"Retrying task '{task.task_id}' with defensive parameter sanitization.",
            modified_parameters=dict(task.parameters)
        )

recovery_manager = RecoveryManager()
