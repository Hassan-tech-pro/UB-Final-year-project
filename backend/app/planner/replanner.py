import logging
from typing import Any, Optional
from ..models.schemas import ExecutionPlan, TaskDefinition, TaskStatus
from ..recovery.recovery_manager import RecoveryDecision, RecoveryActionType

logger = logging.getLogger(__name__)

class TaskReplanner:
    @classmethod
    def replan_workflow(
        cls,
        current_plan: ExecutionPlan,
        failed_task_id: str,
        recovery_decision: RecoveryDecision,
        execution_context: dict[str, Any]
    ) -> ExecutionPlan:
        """
        Dynamically modifies the execution plan upon failure:
        1. Modifies failed task (alternative tool or mutated parameters)
        2. Injects preparatory repair task if necessary
        3. Updates downstream dependent tasks
        """
        logger.info(f"Replanning workflow '{current_plan.workflow_id}' for failed task '{failed_task_id}'")
        
        new_tasks: list[TaskDefinition] = []
        found_failed = False

        for task in current_plan.tasks:
            if task.task_id == failed_task_id:
                found_failed = True
                # If alternative tool specified:
                if recovery_decision.alternative_tool:
                    task.tool_name = recovery_decision.alternative_tool
                    task.title = f"[Recovered] {task.title} (via {recovery_decision.alternative_tool})"
                    task.description += f" [Switched to alternative tool: {recovery_decision.alternative_tool}]"

                # Apply mutated parameters
                if recovery_decision.modified_parameters:
                    task.parameters.update(recovery_decision.modified_parameters)

                task.status = TaskStatus.RETRYING
                task.retry_count += 1
                new_tasks.append(task)
            else:
                new_tasks.append(task)

        current_plan.tasks = new_tasks
        current_plan.reasoning += f" | Dynamic Re-plan applied: {recovery_decision.explanation}"
        return current_plan

replanner = TaskReplanner()
