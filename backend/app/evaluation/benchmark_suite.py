import time
import json
import logging
import asyncio
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from ..core.config import settings
from ..core.database import db
from ..tools.registry import registry
from ..verification.engine import verifier
from ..verification.rules import IndependentCalculationRule, FileIntegrityRule
from ..recovery.recovery_manager import recovery_manager, RecoveryActionType
from ..planner.planner import planner
from ..orchestrator.engine import engine
from .metrics import MetricsCalculator
from ..models.schemas import BenchmarkResult, TaskDefinition, TaskStatus

logger = logging.getLogger(__name__)

class BenchmarkSuite:
    def __init__(self):
        self.workspace = settings.WORKSPACE_DIR
        self.sample_dir = settings.SAMPLE_DATA_DIR

    def ensure_sample_files(self):
        """Generates realistic sample PDF, CSV, and DOCX files if not already present."""
        self.sample_dir.mkdir(parents=True, exist_ok=True)

        # 1. Sample Q1 PDF
        q1_pdf = self.sample_dir / "Q1_Financial_Report.pdf"
        if not q1_pdf.exists():
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(str(q1_pdf), pagesize=letter)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("<b>Acme Corp - Q1 FY2026 Financial Report</b>", styles['Title']),
                Spacer(1, 15),
                Paragraph("Quarter: Q1 FY2026", styles['Normal']),
                Paragraph("Total Revenue: $1,250,000.00", styles['Normal']),
                Paragraph("Operating Expenses: $820,000.00", styles['Normal']),
                Paragraph("Net Profit: $430,000.00", styles['Normal']),
                Paragraph("Units Sold: 15,200", styles['Normal']),
            ]
            doc.build(story)

        # 2. Sample Q2 PDF
        q2_pdf = self.sample_dir / "Q2_Financial_Report.pdf"
        if not q2_pdf.exists():
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(str(q2_pdf), pagesize=letter)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("<b>Acme Corp - Q2 FY2026 Financial Report</b>", styles['Title']),
                Spacer(1, 15),
                Paragraph("Quarter: Q2 FY2026", styles['Normal']),
                Paragraph("Total Revenue: $1,480,000.00", styles['Normal']),
                Paragraph("Operating Expenses: $910,000.00", styles['Normal']),
                Paragraph("Net Profit: $570,000.00", styles['Normal']),
                Paragraph("Units Sold: 18,400", styles['Normal']),
            ]
            doc.build(story)

        # 3. Sample Q3 PDF
        q3_pdf = self.sample_dir / "Q3_Financial_Report.pdf"
        if not q3_pdf.exists():
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(str(q3_pdf), pagesize=letter)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("<b>Acme Corp - Q3 FY2026 Financial Report</b>", styles['Title']),
                Spacer(1, 15),
                Paragraph("Quarter: Q3 FY2026", styles['Normal']),
                Paragraph("Total Revenue: $1,650,000.00", styles['Normal']),
                Paragraph("Operating Expenses: $980,000.00", styles['Normal']),
                Paragraph("Net Profit: $670,000.00", styles['Normal']),
                Paragraph("Units Sold: 21,000", styles['Normal']),
            ]
            doc.build(story)

        # 4. Sample CSV
        sample_csv = self.sample_dir / "Sample_Sales.csv"
        if not sample_csv.exists():
            import pandas as pd
            df = pd.DataFrame([
                {"Region": "North", "Revenue": 450000, "Expenses": 290000, "Profit": 160000},
                {"Region": "South", "Revenue": 520000, "Expenses": 340000, "Profit": 180000},
                {"Region": "East", "Revenue": 610000, "Expenses": 390000, "Profit": 220000},
                {"Region": "West", "Revenue": 580000, "Expenses": 360000, "Profit": 220000},
            ])
            df.to_csv(sample_csv, index=False)

    async def run_all(self) -> BenchmarkResult:
        """Executes all 10 scenario benchmarks and compiles metrics."""
        self.ensure_sample_files()
        suite_id = f"bench_{int(time.time())}"
        scenario_results = []

        scenarios = [
            ("Scenario 1: Simple Document Extraction", self.scenario_1_simple_extraction),
            ("Scenario 2: Multiple PDF Processing", self.scenario_2_multi_pdf),
            ("Scenario 3: Excel Creation and Calculations", self.scenario_3_excel_calculations),
            ("Scenario 4: Data Cleaning and Transformation", self.scenario_4_data_cleaning),
            ("Scenario 5: Report Generation", self.scenario_5_report_generation),
            ("Scenario 6: Invalid/Corrupted File Handling", self.scenario_6_invalid_file),
            ("Scenario 7: Tool Execution Failure Catching", self.scenario_7_tool_failure),
            ("Scenario 8: Incorrect Calculation Detection", self.scenario_8_incorrect_calc_detection),
            ("Scenario 9: Failed Task Recovery & Tool Fallback", self.scenario_9_task_recovery),
            ("Scenario 10: Multi-Step Dependent Workflow", self.scenario_10_end_to_end_pipeline)
        ]

        for name, fn in scenarios:
            start_t = time.perf_counter()
            try:
                res = await fn() if asyncio.iscoroutinefunction(fn) else fn()
                duration = round(time.perf_counter() - start_t, 3)
                res["scenario_name"] = name
                res["duration_seconds"] = duration
                scenario_results.append(res)
            except Exception as e:
                duration = round(time.perf_counter() - start_t, 3)
                logger.error(f"Error in benchmark scenario '{name}': {e}", exc_info=True)
                scenario_results.append({
                    "scenario_name": name,
                    "passed": False,
                    "duration_seconds": duration,
                    "error": str(e),
                    "total_tasks": 1,
                    "completed_tasks": 0,
                    "tool_selections_evaluated": 1,
                    "correct_tool_selections": 0,
                    "verifications_evaluated": 1,
                    "accurate_verifications": 0
                })

        metrics = MetricsCalculator.calculate(scenario_results)
        passed_count = sum(1 for s in scenario_results if s.get("passed", False))

        benchmark_record = {
            "id": suite_id,
            "suite_name": "Agentic AI Comprehensive 10-Scenario Benchmark Suite",
            "total_scenarios": len(scenarios),
            "passed_scenarios": passed_count,
            "failed_scenarios": len(scenarios) - passed_count,
            "metrics": metrics.model_dump(),
            "scenario_results": scenario_results,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        db.save_evaluation(benchmark_record)
        return BenchmarkResult(**benchmark_record)

    # 1. Simple document extraction
    def scenario_1_simple_extraction(self) -> dict[str, Any]:
        test_file = self.workspace / "bench_test_simple.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Line 1: Operational metrics.\nLine 2: Target achieved.")

        read_res = registry.execute("txt_read_file", file_path=str(test_file))
        passed = read_res.success and "Operational metrics" in read_res.data.get("content", "")

        return {
            "passed": passed,
            "total_tasks": 1,
            "completed_tasks": 1 if passed else 0,
            "tool_selections_evaluated": 1,
            "correct_tool_selections": 1 if passed else 0,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0
        }

    # 2. Multiple PDF processing
    def scenario_2_multi_pdf(self) -> dict[str, Any]:
        pdfs = [
            self.sample_dir / "Q1_Financial_Report.pdf",
            self.sample_dir / "Q2_Financial_Report.pdf",
            self.sample_dir / "Q3_Financial_Report.pdf"
        ]
        extracted_entities = []
        for p in pdfs:
            t_res = registry.execute("pdf_extract_text", file_path=str(p))
            if t_res.success:
                e_res = registry.execute("data_extract_entities", text=t_res.data["full_text"])
                if e_res.success:
                    extracted_entities.append(e_res.data["extracted_fields"])

        passed = len(extracted_entities) == 3 and all("revenue" in e and e["revenue"] > 0 for e in extracted_entities)
        return {
            "passed": passed,
            "total_tasks": 3,
            "completed_tasks": len(extracted_entities),
            "tool_selections_evaluated": 3,
            "correct_tool_selections": 3,
            "verifications_evaluated": 3,
            "accurate_verifications": 3 if passed else 0
        }

    # 3. Excel creation and calculations
    def scenario_3_excel_calculations(self) -> dict[str, Any]:
        excel_path = self.workspace / "bench_calc.xlsx"
        records = [
            {"Item": "A", "Cost": 150.0, "Tax": 15.0},
            {"Item": "B", "Cost": 250.0, "Tax": 25.0}
        ]
        w_res = registry.execute("excel_write_spreadsheet", file_path=str(excel_path), records=records)
        r_res = registry.execute("excel_read_spreadsheet", file_path=str(excel_path))
        s_res = registry.execute("data_calculate_statistics", records=records, numeric_columns=["Cost", "Tax"])

        passed = (
            w_res.success and r_res.success and s_res.success
            and s_res.data["totals"]["total_Cost"] == 400.0
            and s_res.data["totals"]["total_Tax"] == 40.0
        )
        return {
            "passed": passed,
            "total_tasks": 3,
            "completed_tasks": 3 if passed else 0,
            "tool_selections_evaluated": 3,
            "correct_tool_selections": 3,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0
        }

    # 4. Data cleaning and transformation
    def scenario_4_data_cleaning(self) -> dict[str, Any]:
        dirty_records = [
            {"Name": " Alice ", "Sales": 100, "Expenses": 40},
            {"Name": " Alice ", "Sales": 100, "Expenses": 40}, # duplicate
            {"Name": "Bob", "Sales": 200, "Expenses": 80}
        ]
        clean_res = registry.execute("data_clean", records=dirty_records, drop_duplicates=True, strip_strings=True)
        trans_res = registry.execute(
            "data_transform",
            records=clean_res.data["records"],
            computed_columns={"Margin": "Sales - Expenses"}
        )

        passed = (
            clean_res.success and clean_res.data["final_rows"] == 2
            and trans_res.success
            and trans_res.data["records"][0]["Margin"] == 60
        )
        return {
            "passed": passed,
            "total_tasks": 2,
            "completed_tasks": 2 if passed else 0,
            "tool_selections_evaluated": 2,
            "correct_tool_selections": 2,
            "verifications_evaluated": 2,
            "accurate_verifications": 2 if passed else 0
        }

    # 5. Report generation
    def scenario_5_report_generation(self) -> dict[str, Any]:
        pdf_path = self.workspace / "bench_rep.pdf"
        excel_path = self.workspace / "bench_rep.xlsx"
        records = [{"Quarter": "Q1", "Revenue": 1000.0, "Expenses": 600.0, "Profit": 400.0}]

        pdf_res = registry.execute(
            "generate_pdf_report",
            file_path=str(pdf_path),
            title="Benchmark Executive Report",
            executive_summary="Executive report test.",
            key_metrics={"total_revenue": 1000.0}
        )
        xl_res = registry.execute(
            "generate_excel_report",
            file_path=str(excel_path),
            title="Benchmark Report",
            records=records
        )

        passed = pdf_res.success and xl_res.success and pdf_path.exists() and excel_path.exists()
        return {
            "passed": passed,
            "total_tasks": 2,
            "completed_tasks": 2 if passed else 0,
            "tool_selections_evaluated": 2,
            "correct_tool_selections": 2,
            "verifications_evaluated": 2,
            "accurate_verifications": 2 if passed else 0
        }

    # 6. Invalid or corrupted file handling
    def scenario_6_invalid_file(self) -> dict[str, Any]:
        non_existent = str(self.workspace / "definitely_does_not_exist_99.pdf")
        res = registry.execute("pdf_extract_text", file_path=non_existent)
        # Should cleanly return success=False with FileNotFoundError without crashing
        passed = (not res.success) and ("not found" in (res.error or "").lower())
        return {
            "passed": passed,
            "total_tasks": 1,
            "completed_tasks": 1 if passed else 0,
            "tool_selections_evaluated": 1,
            "correct_tool_selections": 1,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0
        }

    # 7. Tool execution failure
    def scenario_7_tool_failure(self) -> dict[str, Any]:
        # Call tool with intentionally illegal format parameter
        res = registry.execute("file_convert_format", source_path="some_file.csv", target_format="unsupported_format_xyz")
        passed = (not res.success) and ("not supported" in (res.error or "").lower() or "not found" in (res.error or "").lower())
        return {
            "passed": passed,
            "total_tasks": 1,
            "completed_tasks": 1 if passed else 0,
            "tool_selections_evaluated": 1,
            "correct_tool_selections": 1,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0
        }

    # 8. Incorrect calculation detection (independent verifier flags error!)
    def scenario_8_incorrect_calc_detection(self) -> dict[str, Any]:
        records = [
            {"revenue": 100.0, "expenses": 40.0},
            {"revenue": 200.0, "expenses": 60.0}
        ]
        # True sum of revenue is 300.0, but fake claimed total is 999.0
        claimed_totals = {"total_revenue": 999.0}
        check_res = IndependentCalculationRule.verify(records, claimed_totals)
        # The verification rule MUST catch the discrepancy and return passed=False
        passed = (check_res.passed is False) and ("Mismatch" in check_res.message)
        return {
            "passed": passed,
            "total_tasks": 1,
            "completed_tasks": 1 if passed else 0,
            "tool_selections_evaluated": 1,
            "correct_tool_selections": 1,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0
        }

    # 9. Failed task recovery
    def scenario_9_task_recovery(self) -> dict[str, Any]:
        task = TaskDefinition(
            task_id="task_fail",
            title="Generate Excel",
            tool_name="generate_excel_report",
            parameters={"file_path": str(self.workspace / "recovery_test.xlsx"), "title": "Recovery"},
            retry_count=1
        )
        decision = recovery_manager.formulate_recovery_plan(
            task,
            error_msg="openpyxl crashed unexpectedly"
        )
        passed = (
            decision.can_retry is True
            and decision.action in [RecoveryActionType.FALLBACK_TOOL, RecoveryActionType.RETRY_WITH_MODIFIED_PARAMS]
        )
        return {
            "passed": passed,
            "total_tasks": 1,
            "completed_tasks": 1 if passed else 0,
            "tool_selections_evaluated": 1,
            "correct_tool_selections": 1,
            "verifications_evaluated": 1,
            "accurate_verifications": 1 if passed else 0,
            "recovery_attempts": 1,
            "successful_recoveries": 1 if passed else 0
        }

    # 10. Multi-step end-to-end pipeline
    async def scenario_10_end_to_end_pipeline(self) -> dict[str, Any]:
        wf_id = f"bench_e2e_{int(time.time())}"
        objective = "Extract data from three PDF reports, organize it into Excel, calculate totals, and generate a summary report."
        uploaded = [
            str(self.sample_dir / "Q1_Financial_Report.pdf"),
            str(self.sample_dir / "Q2_Financial_Report.pdf"),
            str(self.sample_dir / "Q3_Financial_Report.pdf")
        ]

        task = await engine.start_workflow(wf_id, objective, uploaded)
        await task

        wf = db.get_workflow(wf_id)
        passed = wf is not None and wf["status"] == "COMPLETED" and wf["completed_tasks"] >= 6
        return {
            "passed": passed,
            "total_tasks": wf["total_tasks"] if wf else 6,
            "completed_tasks": wf["completed_tasks"] if wf else 0,
            "tool_selections_evaluated": 6,
            "correct_tool_selections": 6 if passed else 0,
            "verifications_evaluated": 6,
            "accurate_verifications": 6 if passed else 0
        }

benchmark_suite = BenchmarkSuite()
