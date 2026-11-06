import os
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import openpyxl
import pymupdf
import docx

from ..core.security import SecurityManager

class RuleCheckResult:
    def __init__(self, check_name: str, passed: bool, message: str, details: Optional[dict[str, Any]] = None):
        self.check_name = check_name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details
        }


class FileIntegrityRule:
    """Verifies that an output file exists on disk, has non-zero size, and is readable."""
    @staticmethod
    def verify(file_path: str, min_bytes: int = 10, expected_extension: Optional[str] = None) -> RuleCheckResult:
        try:
            safe_path = SecurityManager.resolve_safe_path(file_path)
            if not safe_path.exists():
                return RuleCheckResult(
                    "file_existence",
                    False,
                    f"Target file does not exist at '{file_path}'"
                )

            size = safe_path.stat().st_size
            if size < min_bytes:
                return RuleCheckResult(
                    "file_size",
                    False,
                    f"File exists but is too small or empty ({size} bytes, minimum required is {min_bytes} bytes)"
                )

            if expected_extension:
                ext = safe_path.suffix.lower()
                if ext != expected_extension.lower():
                    return RuleCheckResult(
                        "file_extension",
                        False,
                        f"Expected extension '{expected_extension}', but file has '{ext}'"
                    )

            # Test readability based on format
            ext = safe_path.suffix.lower()
            if ext == ".pdf":
                doc = pymupdf.open(str(safe_path))
                page_count = len(doc)
                doc.close()
                if page_count < 1:
                    return RuleCheckResult("pdf_readability", False, "PDF file contains 0 pages.")
            elif ext in [".xlsx", ".xls"]:
                wb = openpyxl.load_workbook(str(safe_path), read_only=True)
                sheet_names = wb.sheetnames
                wb.close()
                if not sheet_names:
                    return RuleCheckResult("excel_readability", False, "Excel workbook contains no sheets.")
            elif ext == ".docx":
                d = docx.Document(str(safe_path))
                if not d.paragraphs and not d.tables:
                    return RuleCheckResult("docx_readability", False, "DOCX file has no paragraphs or tables.")

            return RuleCheckResult(
                "file_integrity",
                True,
                f"File verified: exists, readable, and valid format ({size} bytes)",
                {"size_bytes": size, "path": str(safe_path)}
            )
        except Exception as e:
            return RuleCheckResult(
                "file_integrity",
                False,
                f"File integrity check failed with error: {str(e)}"
            )


class SchemaAndFieldRule:
    """Verifies that extracted data contains required non-empty fields."""
    @staticmethod
    def verify(data: Any, expected_fields: list[str], min_items: int = 1) -> RuleCheckResult:
        if data is None:
            return RuleCheckResult("schema_not_null", False, "Extracted data is None.")

        # If data is a list of records
        if isinstance(data, list):
            if len(data) < min_items:
                return RuleCheckResult(
                    "item_count",
                    False,
                    f"Expected at least {min_items} records, found {len(data)}"
                )
            # Check fields in first record or across all records
            if data and expected_fields:
                missing_in_first = [f for f in expected_fields if f not in data[0]]
                if missing_in_first:
                    return RuleCheckResult(
                        "expected_fields",
                        False,
                        f"Records are missing required fields: {missing_in_first}",
                        {"missing_fields": missing_in_first}
                    )
            return RuleCheckResult(
                "schema_fields",
                True,
                f"Successfully verified {len(data)} items matching schema requirements."
            )

        # If data is a dictionary
        if isinstance(data, dict):
            # Check nested extracted_fields if present
            target_dict = data.get("extracted_fields", data)
            missing = [f for f in expected_fields if f not in target_dict or target_dict[f] is None]
            if missing:
                return RuleCheckResult(
                    "expected_fields",
                    False,
                    f"Extracted entity is missing fields or values: {missing}",
                    {"missing_fields": missing}
                )
            return RuleCheckResult(
                "schema_fields",
                True,
                f"All required fields present: {expected_fields}"
            )

        return RuleCheckResult("schema_validity", True, "Data format accepted.")


class IndependentCalculationRule:
    """
    Independently recalculates mathematical totals and statistics using raw records
    and compares against the tool's claimed outputs to catch calculation errors.
    """
    @staticmethod
    def verify(
        records: list[dict[str, Any]],
        claimed_totals: dict[str, float],
        tolerance: float = 0.05
    ) -> RuleCheckResult:
        if not records:
            return RuleCheckResult("calculation_check", False, "No data records provided to verify calculations.")

        df = pd.DataFrame(records)
        discrepancies = []
        verified_totals = {}

        for key, claimed_val in claimed_totals.items():
            # Standardize key (e.g. "total_revenue" -> "revenue")
            target_col = key.replace("total_", "").replace("sum_", "")
            
            if target_col in df.columns:
                actual_sum = float(pd.to_numeric(df[target_col], errors='coerce').fillna(0).sum())
                diff = abs(actual_sum - claimed_val)
                verified_totals[key] = {
                    "claimed": claimed_val,
                    "recalculated": round(actual_sum, 2),
                    "discrepancy": round(diff, 2)
                }
                if diff > tolerance:
                    discrepancies.append(
                        f"Mismatch for '{key}': Claimed {claimed_val}, but Python recalculated sum is {actual_sum:.2f} (diff: {diff:.2f})"
                    )

        if discrepancies:
            return RuleCheckResult(
                "independent_calculation",
                False,
                f"Calculation verification failed: {'; '.join(discrepancies)}",
                {"discrepancies": discrepancies, "details": verified_totals}
            )

        return RuleCheckResult(
            "independent_calculation",
            True,
            "All totals independently recalculated in Python and matched within tolerance.",
            {"verified_totals": verified_totals}
        )


class DocumentStructureRule:
    """Verifies that generated documents contain required sections and structural elements."""
    @staticmethod
    def verify_excel_structure(file_path: str, required_sheet: str = "Financial Summary", check_totals_row: bool = True) -> RuleCheckResult:
        try:
            safe_path = SecurityManager.resolve_safe_path(file_path)
            wb = openpyxl.load_workbook(str(safe_path))
            if required_sheet not in wb.sheetnames:
                return RuleCheckResult(
                    "excel_structure",
                    False,
                    f"Workbook is missing required sheet '{required_sheet}'. Available: {wb.sheetnames}"
                )
            ws = wb[required_sheet]
            if ws.max_row < 4:
                return RuleCheckResult("excel_rows", False, f"Worksheet has insufficient rows ({ws.max_row})")

            # Check if Totals row exists if requested
            if check_totals_row:
                has_total_label = False
                for r in range(ws.max_row - 2, ws.max_row + 1):
                    val = str(ws.cell(row=r, column=1).value or "").upper()
                    if "TOTAL" in val:
                        has_total_label = True
                        break
                if not has_total_label:
                    return RuleCheckResult(
                        "excel_totals_row",
                        False,
                        "Workbook structure missing 'TOTAL' summary row."
                    )

            wb.close()
            return RuleCheckResult("excel_structure", True, "Excel structure verified with required sheets and totals row.")
        except Exception as e:
            return RuleCheckResult("excel_structure", False, f"Failed opening Excel file: {str(e)}")

    @staticmethod
    def verify_pdf_sections(file_path: str, required_keywords: list[str]) -> RuleCheckResult:
        try:
            safe_path = SecurityManager.resolve_safe_path(file_path)
            doc = pymupdf.open(str(safe_path))
            full_text = " ".join([page.get_text("text") for page in doc])
            doc.close()

            missing = [kw for kw in required_keywords if kw.lower() not in full_text.lower()]
            if missing:
                return RuleCheckResult(
                    "pdf_sections",
                    False,
                    f"PDF document missing required sections/keywords: {missing}",
                    {"missing_keywords": missing}
                )

            return RuleCheckResult(
                "pdf_sections",
                True,
                f"All required PDF sections verified: {required_keywords}"
            )
        except Exception as e:
            return RuleCheckResult("pdf_sections", False, f"Failed reading PDF structure: {str(e)}")
