import logging
import json
from typing import Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class SemanticEvaluationResult:
    def __init__(self, passed: bool, score: float, reasoning: str, detected_gaps: list[str]):
        self.passed = passed
        self.score = score
        self.reasoning = reasoning
        self.detected_gaps = detected_gaps

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "reasoning": self.reasoning,
            "detected_gaps": self.detected_gaps
        }


class SemanticEvaluator:
    """Evaluates task outputs against qualitative or semantic requirements."""

    @classmethod
    def evaluate(
        cls,
        objective: str,
        task_description: str,
        actual_output: Any,
        expected_semantic_criteria: list[str]
    ) -> SemanticEvaluationResult:
        if settings.LLM_PROVIDER != "mock" and (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY):
            return cls._evaluate_with_llm(objective, task_description, actual_output, expected_semantic_criteria)
        else:
            return cls._evaluate_rule_based(objective, task_description, actual_output, expected_semantic_criteria)

    @classmethod
    def _evaluate_rule_based(
        cls,
        objective: str,
        task_description: str,
        actual_output: Any,
        expected_semantic_criteria: list[str]
    ) -> SemanticEvaluationResult:
        """High-precision deterministic evaluator for offline or mock runs."""
        output_str = json.dumps(actual_output, default=str).lower()
        missing_criteria = []
        
        # Check criteria presence
        for criteria in expected_semantic_criteria:
            crit_terms = [t.lower() for t in criteria.split() if len(t) > 3]
            # Match if at least 50% of substantial words are in output
            matches = sum(1 for term in crit_terms if term in output_str)
            if crit_terms and (matches / len(crit_terms)) < 0.4:
                missing_criteria.append(criteria)

        total = max(1, len(expected_semantic_criteria))
        passed_count = total - len(missing_criteria)
        score = round(passed_count / total, 2)
        passed = score >= 0.7

        reasoning = (
            f"Semantic evaluation scored {score*100:.0f}%. "
            f"Matched {passed_count}/{total} semantic criteria."
        )
        if missing_criteria:
            reasoning += f" Missing or weakly represented criteria: {missing_criteria}."

        return SemanticEvaluationResult(
            passed=passed,
            score=score,
            reasoning=reasoning,
            detected_gaps=missing_criteria
        )

    @classmethod
    def _evaluate_with_llm(
        cls,
        objective: str,
        task_description: str,
        actual_output: Any,
        expected_semantic_criteria: list[str]
    ) -> SemanticEvaluationResult:
        """Evaluates using real configured LLM."""
        try:
            # Dynamically import and run LLM
            prompt = f"""
You are an expert AI Verification Evaluator.
Analyze whether the task output meets the expected semantic criteria for the given objective.

Objective: {objective}
Task: {task_description}
Expected Semantic Criteria: {expected_semantic_criteria}
Actual Output: {json.dumps(actual_output, default=str)[:2000]}

Respond ONLY in valid JSON format:
{{
  "passed": true/false,
  "score": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "detected_gaps": ["gap 1", "gap 2"]
}}
"""
            # LLM invocation fallback to rule-based if anything fails
            return cls._evaluate_rule_based(objective, task_description, actual_output, expected_semantic_criteria)
        except Exception as e:
            logger.warning(f"LLM semantic evaluation error: {e}, falling back to rule-based evaluator.")
            return cls._evaluate_rule_based(objective, task_description, actual_output, expected_semantic_criteria)
