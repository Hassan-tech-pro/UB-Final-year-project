from typing import Any
from ..models.schemas import EvaluationMetrics

class MetricsCalculator:
    @staticmethod
    def calculate(scenario_results: list[dict[str, Any]]) -> EvaluationMetrics:
        if not scenario_results:
            return EvaluationMetrics()

        total_scenarios = len(scenario_results)
        passed_scenarios = sum(1 for s in scenario_results if s.get("passed", False))

        total_tasks = sum(s.get("total_tasks", 1) for s in scenario_results)
        completed_tasks = sum(s.get("completed_tasks", 1) for s in scenario_results)
        tool_selections = sum(s.get("tool_selections_evaluated", 1) for s in scenario_results)
        correct_tools = sum(s.get("correct_tool_selections", 1) for s in scenario_results)
        verifications_evaluated = sum(s.get("verifications_evaluated", 1) for s in scenario_results)
        accurate_verifications = sum(s.get("accurate_verifications", 1) for s in scenario_results)
        recovery_attempts = sum(s.get("recovery_attempts", 0) for s in scenario_results)
        successful_recoveries = sum(s.get("successful_recoveries", 0) for s in scenario_results)
        total_retries = sum(s.get("retries", 0) for s in scenario_results)
        total_duration = sum(s.get("duration_seconds", 0.0) for s in scenario_results)

        return EvaluationMetrics(
            task_completion_rate=round(completed_tasks / max(1, total_tasks), 4),
            planning_accuracy=round(sum(s.get("planning_score", 1.0) for s in scenario_results) / total_scenarios, 4),
            tool_selection_accuracy=round(correct_tools / max(1, tool_selections), 4),
            execution_success_rate=round(completed_tasks / max(1, total_tasks), 4),
            verification_accuracy=round(accurate_verifications / max(1, verifications_evaluated), 4),
            error_recovery_rate=round(successful_recoveries / max(1, recovery_attempts) if recovery_attempts > 0 else 1.0, 4),
            average_execution_time_sec=round(total_duration / total_scenarios, 3),
            total_retries=total_retries,
            overall_workflow_success_rate=round(passed_scenarios / total_scenarios, 4)
        )
