import pytest
from pathlib import Path
from app.tools.registry import registry
from app.core.config import settings

def test_tool_registry():
    tools = registry.list_tools()
    assert len(tools) >= 20
    assert any(t.name == "pdf_extract_text" for t in tools)
    assert any(t.name == "data_calculate_statistics" for t in tools)
    assert any(t.name == "generate_excel_report" for t in tools)
    assert any(t.name == "generate_pdf_report" for t in tools)

def test_file_create_and_read():
    test_path = settings.WORKSPACE_DIR / "test_file_ops.txt"
    create_res = registry.execute("file_create", file_path=str(test_path), content="Agentic AI Test Content")
    assert create_res.success is True
    assert test_path.exists()

    read_res = registry.execute("file_read", file_path=str(test_path))
    assert read_res.success is True
    assert "Agentic AI Test Content" in read_res.data["content"]

def test_data_clean_and_transform():
    raw_data = [
        {"Quarter": " Q1 ", "Revenue": 1000, "Expenses": 600},
        {"Quarter": " Q1 ", "Revenue": 1000, "Expenses": 600}, # duplicate
        {"Quarter": " Q2 ", "Revenue": 1500, "Expenses": 900}
    ]
    clean_res = registry.execute("data_clean", records=raw_data, drop_duplicates=True, strip_strings=True)
    assert clean_res.success is True
    assert clean_res.data["final_rows"] == 2
    assert clean_res.data["records"][0]["Quarter"] == "Q1"

    trans_res = registry.execute(
        "data_transform",
        records=clean_res.data["records"],
        computed_columns={"Profit": "Revenue - Expenses"}
    )
    assert trans_res.success is True
    assert trans_res.data["records"][0]["Profit"] == 400
    assert trans_res.data["records"][1]["Profit"] == 600

def test_data_calculate_statistics():
    records = [
        {"Quarter": "Q1", "Revenue": 1000.0, "Expenses": 600.0, "Profit": 400.0},
        {"Quarter": "Q2", "Revenue": 1500.0, "Expenses": 900.0, "Profit": 600.0},
        {"Quarter": "Q3", "Revenue": 2000.0, "Expenses": 1100.0, "Profit": 900.0}
    ]
    stat_res = registry.execute("data_calculate_statistics", records=records, numeric_columns=["Revenue", "Expenses", "Profit"])
    assert stat_res.success is True
    totals = stat_res.data["totals"]
    assert totals["total_Revenue"] == 4500.0
    assert totals["total_Expenses"] == 2600.0
    assert totals["total_Profit"] == 1900.0

def test_excel_and_pdf_generation():
    xl_path = settings.WORKSPACE_DIR / "test_report.xlsx"
    pdf_path = settings.WORKSPACE_DIR / "test_report.pdf"
    records = [{"Period": "Q1", "Revenue": 120000.0, "Expenses": 70000.0, "Profit": 50000.0}]

    xl_res = registry.execute(
        "generate_excel_report",
        file_path=str(xl_path),
        title="Test Excel Report",
        records=records,
        include_totals=True
    )
    assert xl_res.success is True
    assert xl_path.exists()
    assert xl_path.stat().st_size > 1000

    pdf_res = registry.execute(
        "generate_pdf_report",
        file_path=str(pdf_path),
        title="Test PDF Executive Report",
        executive_summary="Testing automated report generation.",
        key_metrics={"total_revenue": 120000.0}
    )
    assert pdf_res.success is True
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
