import json
from pathlib import Path
from typing import Any, Optional
import pymupdf
import docx
from docx.shared import Inches, Pt, RGBColor
import pandas as pd
import openpyxl
from pydantic import BaseModel, Field

from .registry import registry
from ..core.security import SecurityManager

# Pydantic schemas for document tools
class PDFExtractInput(BaseModel):
    file_path: str = Field(description="Safe path to the PDF file")
    max_pages: Optional[int] = Field(default=None, description="Max pages to extract")

class DocxReadInput(BaseModel):
    file_path: str = Field(description="Safe path to the DOCX file")

class DocxWriteInput(BaseModel):
    file_path: str = Field(description="Target output path for the DOCX file")
    title: str = Field(description="Document title")
    paragraphs: list[str] = Field(default_factory=list, description="List of paragraph texts")
    tables: Optional[list[dict[str, Any]]] = Field(default=None, description="Optional list of table objects {headers: [], rows: [[]]}")

class TxtReadInput(BaseModel):
    file_path: str = Field(description="Path to text file")

class TxtWriteInput(BaseModel):
    file_path: str = Field(description="Output text file path")
    content: str = Field(description="Text content to write")

class CsvReadInput(BaseModel):
    file_path: str = Field(description="Path to CSV file")

class CsvWriteInput(BaseModel):
    file_path: str = Field(description="Output CSV path")
    records: list[dict[str, Any]] = Field(description="List of row dictionaries")

class ExcelReadInput(BaseModel):
    file_path: str = Field(description="Path to Excel file")
    sheet_name: Optional[str] = Field(default=None, description="Specific sheet to read")

class ExcelWriteInput(BaseModel):
    file_path: str = Field(description="Output Excel path")
    records: list[dict[str, Any]] = Field(description="List of data dictionaries to write")
    sheet_name: str = Field(default="Sheet1", description="Sheet name")


@registry.register(
    name="pdf_extract_text",
    description="Extracts plain text, metadata, page count, and structural lines from a PDF file.",
    category="Document Processing",
    param_model=PDFExtractInput
)
def pdf_extract_text(file_path: str, max_pages: Optional[int] = None) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    doc = pymupdf.open(str(safe_path))
    total_pages = len(doc)
    pages_to_read = min(total_pages, max_pages) if max_pages else total_pages

    extracted_pages = []
    full_text_chunks = []
    
    for i in range(pages_to_read):
        page = doc[i]
        text = page.get_text("text").strip()
        full_text_chunks.append(text)
        extracted_pages.append({
            "page_number": i + 1,
            "text": text,
            "word_count": len(text.split())
        })

    metadata = doc.metadata or {}
    doc.close()

    full_text = "\n\n--- Page Break ---\n\n".join(full_text_chunks)
    return {
        "file_name": safe_path.name,
        "total_pages": total_pages,
        "extracted_pages_count": pages_to_read,
        "metadata": metadata,
        "full_text": full_text,
        "pages": extracted_pages,
        "total_words": sum(p["word_count"] for p in extracted_pages)
    }


@registry.register(
    name="docx_read_text",
    description="Reads text, paragraphs, headings, and tables from a DOCX document.",
    category="Document Processing",
    param_model=DocxReadInput
)
def docx_read_text(file_path: str) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"DOCX file not found: {file_path}")

    doc = docx.Document(str(safe_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    
    tables_data = []
    for table in doc.tables:
        rows_data = []
        for row in table.rows:
            rows_data.append([cell.text.strip() for cell in row.cells])
        if rows_data:
            tables_data.append(rows_data)

    return {
        "file_name": safe_path.name,
        "paragraphs": paragraphs,
        "paragraph_count": len(paragraphs),
        "tables": tables_data,
        "full_text": "\n\n".join(paragraphs)
    }


@registry.register(
    name="docx_write_document",
    description="Creates a formatted Microsoft Word DOCX document with title, paragraphs, and tables.",
    category="Document Processing",
    param_model=DocxWriteInput
)
def docx_write_document(
    file_path: str,
    title: str,
    paragraphs: list[str],
    tables: Optional[list[dict[str, Any]]] = None
) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    doc = docx.Document()

    # Title
    heading = doc.add_heading(title, level=0)
    
    # Paragraphs
    for p_text in paragraphs:
        doc.add_paragraph(p_text)

    # Tables
    if tables:
        for t in tables:
            headers = t.get("headers", [])
            rows = t.get("rows", [])
            if headers:
                table = doc.add_table(rows=1, cols=len(headers))
                table.style = 'Table Grid'
                hdr_cells = table.rows[0].cells
                for i, h in enumerate(headers):
                    hdr_cells[i].text = str(h)
                    # Bold header
                    for r in hdr_cells[i].paragraphs[0].runs:
                        r.font.bold = True
                for row_data in rows:
                    row_cells = table.add_row().cells
                    for i, val in enumerate(row_data):
                        if i < len(row_cells):
                            row_cells[i].text = str(val)

    doc.save(str(safe_path))
    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "file_size": safe_path.stat().st_size,
        "status": "created"
    }


@registry.register(
    name="txt_read_file",
    description="Reads plain text content from a text file.",
    category="Document Processing",
    param_model=TxtReadInput
)
def txt_read_file(file_path: str) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"Text file not found: {file_path}")

    with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return {
        "file_name": safe_path.name,
        "content": content,
        "character_count": len(content),
        "line_count": len(content.splitlines())
    }


@registry.register(
    name="txt_write_file",
    description="Writes text content to a text file.",
    category="Document Processing",
    param_model=TxtWriteInput
)
def txt_write_file(file_path: str, content: str) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "file_size": safe_path.stat().st_size,
        "character_count": len(content)
    }


@registry.register(
    name="csv_read_data",
    description="Reads a CSV file into structured JSON records and column definitions.",
    category="Document Processing",
    param_model=CsvReadInput
)
def csv_read_data(file_path: str) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    df = pd.read_csv(safe_path)
    return {
        "file_name": safe_path.name,
        "columns": list(df.columns),
        "row_count": len(df),
        "records": df.to_dict(orient="records")
    }


@registry.register(
    name="csv_write_data",
    description="Writes tabular records into a CSV file.",
    category="Document Processing",
    param_model=CsvWriteInput
)
def csv_write_data(file_path: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    df = pd.DataFrame(records)
    df.to_csv(safe_path, index=False)

    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "row_count": len(df),
        "columns": list(df.columns),
        "file_size": safe_path.stat().st_size
    }


@registry.register(
    name="excel_read_spreadsheet",
    description="Reads an Excel spreadsheet (.xlsx/.xls) into structured records and sheet names.",
    category="Document Processing",
    param_model=ExcelReadInput
)
def excel_read_spreadsheet(file_path: str, sheet_name: Optional[str] = None) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    excel_file = pd.ExcelFile(safe_path)
    sheet_to_read = sheet_name or excel_file.sheet_names[0]
    df = pd.read_excel(safe_path, sheet_name=sheet_to_read)

    # Convert NaNs to None for valid JSON serialization
    cleaned_records = df.where(pd.notnull(df), None).to_dict(orient="records")

    return {
        "file_name": safe_path.name,
        "sheet_names": excel_file.sheet_names,
        "active_sheet": sheet_to_read,
        "columns": list(df.columns),
        "row_count": len(df),
        "records": cleaned_records
    }


@registry.register(
    name="excel_write_spreadsheet",
    description="Writes tabular records to an Excel (.xlsx) spreadsheet with headers.",
    category="Document Processing",
    param_model=ExcelWriteInput
)
def excel_write_spreadsheet(file_path: str, records: list[dict[str, Any]], sheet_name: str = "Sheet1") -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    df = pd.DataFrame(records)
    
    with pd.ExcelWriter(safe_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "sheet_name": sheet_name,
        "row_count": len(df),
        "columns": list(df.columns),
        "file_size": safe_path.stat().st_size
    }
