import time
from typing import Any, Optional
from datetime import datetime, timezone

from .rules import (
    FileIntegrityRule,
    SchemaAndFieldRule,
    IndependentCalculationRule,
    DocumentStructureRule,
    RuleCheckResult
)
from .evaluators import SemanticEvaluator
from ..models.schemas import VerificationResult, VerificationStatus, TaskDefinition

class VerificationEngine:
    @classmethod
    def verify_task(
        cls,
        task: TaskDefinition,
        workflow_id: str,
        tool_output: Any,
        workflow_context: Optional[dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Executes exhaustive multi-layered verification on the tool's execution output.
        Combines deterministic rule verification with semantic analysis.
        """
        checks: list[RuleCheckResult] = []
        criteria = task.verification_criteria or {}
        detected_errors: list[str] = []
        suggested_recovery = None

        # 1. File Integrity Rule Check
        file_check_spec = criteria.get("file_check")
        file_path_to_check = None
        if file_check_spec:
            file_path_to_check = file_check_spec.get("path") or (tool_output.get("file_path") if isinstance(tool_output, dict) else None)
        elif isinstance(tool_output, dict) and "file_path" in tool_output:
            file_path_to_check = tool_output.get("file_path")

        if file_path_to_check:
            min_size = file_check_spec.get("min_bytes", 20) if file_check_spec else 20
            expected_ext = file_check_spec.get("expected_extension") if file_check_spec else None
            res = FileIntegrityRule.verify(file_path_to_check, min_bytes=min_size, expected_extension=expected_ext)
            checks.append(res)
            if not res.passed:
                detected_errors.append(f"File Check Failed: {res.message}")
                suggested_recovery = f"Retry task with verified write permissions or alternative path for '{file_path_to_check}'."

        # 2. Schema and Field Rule Check
        schema_spec = criteria.get("schema_check")
        if schema_spec:
            expected_fields = schema_spec.get("required_fields", [])
            min_items = schema_spec.get("min_items", 1)
            target_data = tool_output.get("records") if isinstance(tool_output, dict) and "records" in tool_output else tool_output
            res = SchemaAndFieldRule.verify(target_data, expected_fields=expected_fields, min_items=min_items)
            checks.append(res)
            if not res.passed:
                detected_errors.append(f"Schema Check Failed: {res.message}")
                if not suggested_recovery:
                    suggested_recovery = "Review document structure or retry with broader extraction regex."

        # 3. Independent Math Calculation Verification Rule
        calc_spec = criteria.get("calculation_check")
        if calc_spec and workflow_context:
            source_records = calc_spec.get("source_records") or workflow_context.get("combined_records") or workflow_context.get("records")
            claimed_totals = calc_spec.get("claimed_totals")
            if not claimed_totals and isinstance(tool_output, dict):
                claimed_totals = tool_output.get("totals") or tool_output.get("totals_calculated")

            if source_records and claimed_totals:
                tolerance = calc_spec.get("tolerance", 0.05)
                res = IndependentCalculationRule.verify(source_records, claimed_totals, tolerance=tolerance)
                checks.append(res)
                if not res.passed:
                    detected_errors.append(f"Math Calculation Failed: {res.message}")
                    if not suggested_recovery:
                        suggested_recovery = "Recalculate sums directly from raw records and rewrite dataset."

        # 4. Document Structure & Content Verification Rule
        doc_structure_spec = criteria.get("document_structure")
        if doc_structure_spec and file_path_to_check:
            doc_type = doc_structure_spec.get("type", "").lower()
            if "excel" in doc_type or file_path_to_check.endswith((".xlsx", ".xls")):
                req_sheet = doc_structure_spec.get("required_sheet", "Financial Summary")
                res = DocumentStructureRule.verify_excel_structure(file_path_to_check, required_sheet=req_sheet)
                checks.append(res)
                if not res.passed:
                    detected_errors.append(f"Excel Structure Error: {res.message}")
                    if not suggested_recovery:
                        suggested_recovery = "Regenerate Excel workbook ensuring valid sheet headers and totals row."
            elif "pdf" in doc_type or file_path_to_check.endswith(".pdf"):
                req_kw = doc_structure_spec.get("required_keywords", ["Executive Summary", "Financial"])
                res = DocumentStructureRule.verify_pdf_sections(file_path_to_check, req_kw)
                checks.append(res)
                if not res.passed:
                    detected_errors.append(f"PDF Structure Error: {res.message}")
                    if not suggested_recovery:
                        suggested_recovery = "Rebuild PDF document ensuring all required sections are rendered."

        # 5. Semantic / Qualitative Criteria Check
        semantic_criteria = criteria.get("semantic_criteria")
        if semantic_criteria:
            sem_res = SemanticEvaluator.evaluate(
                objective=workflow_context.get("objective", "") if workflow_context else "",
                task_description=task.description,
                actual_output=tool_output,
                expected_semantic_criteria=semantic_criteria
            )
            checks.append(RuleCheckResult("semantic_coherence", sem_res.passed, sem_res.reasoning))
            if not sem_res.passed:
                detected_errors.append(f"Semantic Gap: {sem_res.reasoning}")
                if not suggested_recovery:
                    suggested_recovery = "Enrich summary details to address detected semantic gaps."

        # If no specific criteria were defined, perform baseline sanity check
        if not checks:
            has_content = bool(tool_output)
            checks.append(RuleCheckResult("baseline_output_sanity", has_content, "Output is non-null" if has_content else "Output is empty"))
            if not has_content:
                detected_errors.append("Task generated an empty response.")
                suggested_recovery = "Inspect upstream task inputs and retry."

        passed_checks = sum(1 for c in checks if c.passed)
        failed_checks = sum(1 for c in checks if not c.passed)

        if failed_checks == 0:
            status = VerificationStatus.PASSED
            explanation = f"All {passed_checks} verification checks passed successfully."
        elif passed_checks > 0 and failed_checks <= 1 and not any("Math" in e or "File Check" in e for e in detected_errors):
            status = VerificationStatus.WARNING
            explanation = f"{passed_checks} checks passed, with non-critical warning on {failed_checks} check."
        else:
            status = VerificationStatus.FAILED
            explanation = f"Verification failed: {failed_checks} check(s) did not satisfy required criteria."

        expected_str = criteria.get("description") or f"Satisfy {len(checks)} specified verification criteria."
        actual_str = f"{passed_checks}/{len(checks)} checks satisfied."
        if detected_errors:
            actual_str += f" Errors: {'; '.join(detected_errors)}"

        return VerificationResult(
            id=f"v_{task.task_id}_{int(time.time()*1000)}",
            task_id=task.task_id,
            workflow_id=workflow_id,
            status=status,
            expected_result=expected_str,
            actual_result=actual_str,
            checks_passed=passed_checks,
            checks_failed=failed_checks,
            detected_errors=detected_errors,
            explanation=explanation,
            suggested_recovery=suggested_recovery,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

verifier = VerificationEngine()
