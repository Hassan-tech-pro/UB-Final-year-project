import os
import shutil
import json
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from .registry import registry
from ..core.security import SecurityManager, SecurityError

class FileCreateInput(BaseModel):
    file_path: str = Field(description="Relative or safe path to create file")
    content: str = Field(description="Content to write")

class FileReadInput(BaseModel):
    file_path: str = Field(description="Path to read")
    max_bytes: int = Field(default=1024 * 1024, description="Max bytes to read")

class FileModifyInput(BaseModel):
    file_path: str = Field(description="Path of file to modify")
    mode: str = Field(default="append", description="'append' or 'replace'")
    content: str = Field(description="Content to append or replace")

class FileRenameInput(BaseModel):
    source_path: str = Field(description="Source file path")
    target_path: str = Field(description="Target file path")

class FileOrganizeInput(BaseModel):
    file_paths: list[str] = Field(description="List of files to organize")
    target_folder: str = Field(description="Target subdirectory within workspace")

class FileConvertFormatInput(BaseModel):
    source_path: str = Field(description="Source file path")
    target_format: str = Field(description="Target extension: 'xlsx', 'csv', 'json'")


@registry.register(
    name="file_create",
    description="Creates a new file safely in the workspace.",
    category="File Operations",
    param_model=FileCreateInput
)
def file_create(file_path: str, content: str) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "size_bytes": safe_path.stat().st_size,
        "status": "created"
    }


@registry.register(
    name="file_read",
    description="Reads content from a file safely within workspace bounds.",
    category="File Operations",
    param_model=FileReadInput
)
def file_read(file_path: str, max_bytes: int = 1024 * 1024) -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size = safe_path.stat().st_size
    with open(safe_path, "rb") as f:
        data = f.read(max_bytes)

    # Attempt utf-8 decode
    try:
        text_content = data.decode("utf-8")
        is_binary = False
    except UnicodeDecodeError:
        text_content = f"<Binary file: {len(data)} bytes>"
        is_binary = True

    return {
        "file_name": safe_path.name,
        "size_bytes": size,
        "is_binary": is_binary,
        "content": text_content,
        "truncated": size > max_bytes
    }


@registry.register(
    name="file_modify",
    description="Appends or replaces content in an existing workspace file.",
    category="File Operations",
    param_model=FileModifyInput
)
def file_modify(file_path: str, content: str, mode: str = "append") -> dict[str, Any]:
    safe_path = SecurityManager.resolve_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File to modify does not exist: {file_path}")

    write_mode = "a" if mode == "append" else "w"
    with open(safe_path, write_mode, encoding="utf-8") as f:
        f.write(content)

    return {
        "file_path": str(safe_path),
        "filename": safe_path.name,
        "mode": mode,
        "new_size_bytes": safe_path.stat().st_size
    }


@registry.register(
    name="file_rename",
    description="Renames or moves a file safely within the workspace sandbox.",
    category="File Operations",
    param_model=FileRenameInput
)
def file_rename(source_path: str, target_path: str) -> dict[str, Any]:
    safe_source = SecurityManager.resolve_safe_path(source_path)
    safe_target = SecurityManager.resolve_safe_path(target_path)

    if not safe_source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    safe_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(safe_source), str(safe_target))

    return {
        "old_path": str(safe_source),
        "new_path": str(safe_target),
        "filename": safe_target.name,
        "status": "moved"
    }


@registry.register(
    name="file_organize",
    description="Organizes specified files into a named workspace subfolder.",
    category="File Operations",
    param_model=FileOrganizeInput
)
def file_organize(file_paths: list[str], target_folder: str) -> dict[str, Any]:
    safe_target_dir = SecurityManager.resolve_safe_path(target_folder)
    safe_target_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    for fp in file_paths:
        src = SecurityManager.resolve_safe_path(fp)
        if src.exists() and src.is_file():
            dst = safe_target_dir / src.name
            shutil.copy2(str(src), str(dst))
            moved.append(str(dst))

    return {
        "target_directory": str(safe_target_dir),
        "files_organized_count": len(moved),
        "moved_files": moved
    }


@registry.register(
    name="file_convert_format",
    description="Converts structured tabular files between CSV, XLSX, and JSON formats.",
    category="File Operations",
    param_model=FileConvertFormatInput
)
def file_convert_format(source_path: str, target_format: str) -> dict[str, Any]:
    safe_src = SecurityManager.resolve_safe_path(source_path)
    if not safe_src.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    target_fmt = target_format.lower().replace('.', '')
    valid_fmts = ["csv", "xlsx", "json"]
    if target_fmt not in valid_fmts:
        raise ValueError(f"Target format '{target_format}' not supported. Allowed: {valid_fmts}")

    # Read data into DataFrame
    src_ext = safe_src.suffix.lower()
    if src_ext == ".csv":
        df = pd.read_csv(safe_src)
    elif src_ext in [".xlsx", ".xls"]:
        df = pd.read_excel(safe_src)
    elif src_ext == ".json":
        df = pd.read_json(safe_src)
    else:
        raise ValueError(f"Cannot convert from format: {src_ext}")

    target_file = safe_src.with_suffix(f".{target_fmt}")
    if target_fmt == "csv":
        df.to_csv(target_file, index=False)
    elif target_fmt == "xlsx":
        df.to_excel(target_file, index=False, engine="openpyxl")
    elif target_fmt == "json":
        df.to_json(target_file, orient="records", indent=2)

    return {
        "source_file": str(safe_src),
        "converted_file": str(target_file),
        "target_format": target_fmt,
        "rows_converted": len(df),
        "file_size": target_file.stat().st_size
    }
