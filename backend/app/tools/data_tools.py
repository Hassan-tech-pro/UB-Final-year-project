import re
from typing import Any, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from .registry import registry

class DataCleanInput(BaseModel):
    records: list[dict[str, Any]] = Field(description="Data records to clean")
    drop_duplicates: bool = Field(default=True, description="Whether to drop duplicate rows")
    fill_nulls: Optional[Any] = Field(default=None, description="Replacement for null/empty values")
    strip_strings: bool = Field(default=True, description="Whether to strip whitespace from strings")

class DataExtractEntitiesInput(BaseModel):
    text: str = Field(description="Raw text to extract entities and financial fields from")
    fields: Optional[list[str]] = Field(default=None, description="Optional target fields to extract (e.g. ['revenue', 'expenses', 'quarter'])")

class DataTransformInput(BaseModel):
    records: list[dict[str, Any]] = Field(description="List of records")
    rename_columns: Optional[dict[str, str]] = Field(default=None, description="Mapping of old column names to new ones")
    computed_columns: Optional[dict[str, str]] = Field(default=None, description="Formula dictionary, e.g. {'profit': 'revenue - expenses'}")
    filter_query: Optional[str] = Field(default=None, description="Pandas query string to filter rows")

class DataMergeInput(BaseModel):
    datasets: list[list[dict[str, Any]]] = Field(description="List of datasets to merge")
    merge_type: str = Field(default="concat", description="'concat' (union rows) or 'merge' (join on key)")
    on_key: Optional[str] = Field(default=None, description="Join key if merge_type is 'merge'")

class DataCalculateStatisticsInput(BaseModel):
    records: list[dict[str, Any]] = Field(description="Records to analyze")
    numeric_columns: Optional[list[str]] = Field(default=None, description="Columns to calculate stats for")
    group_by: Optional[str] = Field(default=None, description="Column to group by")


@registry.register(
    name="data_clean",
    description="Cleans tabular records by removing duplicates, filling missing values, and trimming whitespace.",
    category="Data Processing",
    param_model=DataCleanInput
)
def data_clean(
    records: list[dict[str, Any]],
    drop_duplicates: bool = True,
    fill_nulls: Optional[Any] = None,
    strip_strings: bool = True
) -> dict[str, Any]:
    if not records:
        return {"records": [], "row_count": 0, "cleaned_count": 0}

    df = pd.DataFrame(records)
    initial_count = len(df)

    if strip_strings:
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip()

    if drop_duplicates:
        df = df.drop_duplicates()

    if fill_nulls is not None:
        df = df.fillna(fill_nulls)

    cleaned_records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {
        "records": cleaned_records,
        "initial_rows": initial_count,
        "final_rows": len(df),
        "removed_rows": initial_count - len(df)
    }


@registry.register(
    name="data_extract_entities",
    description="Extracts financial figures, dates, percentages, and metrics from unstructured document text.",
    category="Data Processing",
    param_model=DataExtractEntitiesInput
)
def data_extract_entities(text: str, fields: Optional[list[str]] = None) -> dict[str, Any]:
    extracted = {}

    # Extract Quarter / Period
    quarter_match = re.search(r'\b(Q[1-4]|Quarter\s*[1-4])\b(?:\s*(?:FY|20\d\d))?', text, re.IGNORECASE)
    if quarter_match:
        extracted["quarter"] = quarter_match.group(0).upper()

    # Extract Year
    year_match = re.search(r'\b(20\d\d)\b', text)
    if year_match:
        extracted["year"] = int(year_match.group(1))

    # Pattern for currency figures: $12,345.67 or $12.3M or $12,345
    def parse_currency(val_str: str) -> float:
        cleaned = val_str.replace('$', '').replace(',', '').strip()
        multiplier = 1.0
        if cleaned.upper().endswith('M'):
            multiplier = 1000000.0
            cleaned = cleaned[:-1]
        elif cleaned.upper().endswith('B'):
            multiplier = 1000000000.0
            cleaned = cleaned[:-1]
        elif cleaned.upper().endswith('K'):
            multiplier = 1000.0
            cleaned = cleaned[:-1]
        try:
            return round(float(cleaned) * multiplier, 2)
        except ValueError:
            return 0.0

    # Extract Revenue
    rev_match = re.search(r'(?:total\s+)?revenue(?:\s*[:=-]|\s+is|\s+of)?\s*\$?([\d,]+(?:\.\d+)?(?:\s*[KkMmBb])?)', text, re.IGNORECASE)
    if rev_match:
        extracted["revenue"] = parse_currency(rev_match.group(1))

    # Extract Expenses / Cost
    exp_match = re.search(r'(?:total\s+)?(?:expenses|costs|operating expenses)(?:\s*[:=-]|\s+is|\s+of)?\s*\$?([\d,]+(?:\.\d+)?(?:\s*[KkMmBb])?)', text, re.IGNORECASE)
    if exp_match:
        extracted["expenses"] = parse_currency(exp_match.group(1))

    # Extract Net Income / Profit
    profit_match = re.search(r'(?:net\s+)?(?:income|profit)(?:\s*[:=-]|\s+is|\s+of)?\s*\$?([\d,]+(?:\.\d+)?(?:\s*[KkMmBb])?)', text, re.IGNORECASE)
    if profit_match:
        extracted["profit"] = parse_currency(profit_match.group(1))
    elif "revenue" in extracted and "expenses" in extracted:
        # Fallback calculate profit
        extracted["profit"] = round(extracted["revenue"] - extracted["expenses"], 2)

    # Extract Units or Customers
    units_match = re.search(r'(?:units|customers|subscribers)(?:\s+sold|\s+served|\s*[:=-])?\s*([\d,]+)', text, re.IGNORECASE)
    if units_match:
        extracted["units"] = int(units_match.group(1).replace(',', ''))

    # If specific fields were requested, ensure they are present or defaulted
    if fields:
        for f in fields:
            if f not in extracted:
                # Try generic key: value search in text
                pattern = rf'{re.escape(f)}(?:\s*[:=-]|\s+is)?\s*([^\n\r,]+)'
                custom_match = re.search(pattern, text, re.IGNORECASE)
                if custom_match:
                    raw_val = custom_match.group(1).strip()
                    # Check if numeric
                    try:
                        extracted[f] = float(raw_val.replace('$', '').replace(',', ''))
                    except ValueError:
                        extracted[f] = raw_val
                else:
                    extracted[f] = None

    return {
        "extracted_fields": extracted,
        "fields_found_count": len([k for k, v in extracted.items() if v is not None])
    }


@registry.register(
    name="data_transform",
    description="Transforms tabular records: rename columns, apply computed formulas, or filter rows.",
    category="Data Processing",
    param_model=DataTransformInput
)
def data_transform(
    records: list[dict[str, Any]],
    rename_columns: Optional[dict[str, str]] = None,
    computed_columns: Optional[dict[str, str]] = None,
    filter_query: Optional[str] = None
) -> dict[str, Any]:
    if not records:
        return {"records": [], "row_count": 0}

    df = pd.DataFrame(records)

    # 1. Rename columns
    if rename_columns:
        df = df.rename(columns=rename_columns)

    # 2. Computed columns (safe evaluation of basic math: +, -, *, /)
    if computed_columns:
        for col_name, formula in computed_columns.items():
            try:
                # evaluate using pandas eval for speed and safety
                df[col_name] = df.eval(formula)
            except Exception as e:
                # Basic fallback row-by-row
                pass

    # 3. Filter rows
    if filter_query:
        try:
            df = df.query(filter_query)
        except Exception:
            pass

    res_records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {
        "records": res_records,
        "row_count": len(res_records),
        "columns": list(df.columns)
    }


@registry.register(
    name="data_merge",
    description="Merges or concatenates multiple datasets into a single consolidated dataset.",
    category="Data Processing",
    param_model=DataMergeInput
)
def data_merge(
    datasets: list[Any],
    merge_type: str = "concat",
    on_key: Optional[str] = None
) -> dict[str, Any]:
    if not datasets:
        return {"records": [], "total_rows": 0, "columns": []}

    dfs = []
    for d in datasets:
        if d:
            if isinstance(d, dict):
                dfs.append(pd.DataFrame([d]))
            elif isinstance(d, list):
                if d and isinstance(d[0], dict):
                    dfs.append(pd.DataFrame(d))
                elif d:
                    dfs.append(pd.DataFrame([d]))

    if not dfs:
        return {"records": [], "total_rows": 0, "columns": []}

    if merge_type == "merge" and on_key:
        merged_df = dfs[0]
        for next_df in dfs[1:]:
            merged_df = pd.merge(merged_df, next_df, on=on_key, how="outer")
    else:
        # Default vertical concat (row-wise union)
        merged_df = pd.concat(dfs, ignore_index=True)

    records = merged_df.where(pd.notnull(merged_df), None).to_dict(orient="records")
    return {
        "records": records,
        "total_rows": len(records),
        "columns": list(merged_df.columns)
    }


@registry.register(
    name="data_calculate_statistics",
    description="Calculates comprehensive totals and statistics (sum, mean, median, min, max, std) on tabular records.",
    category="Data Processing",
    param_model=DataCalculateStatisticsInput
)
def data_calculate_statistics(
    records: list[dict[str, Any]],
    numeric_columns: Optional[list[str]] = None,
    group_by: Optional[str] = None
) -> dict[str, Any]:
    if not records:
        return {"statistics": {}, "totals": {}}

    df = pd.DataFrame(records)
    
    # Auto-detect numeric columns or convert columns to numeric where possible
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors='coerce')
        if converted.notnull().sum() > 0:
            df[col] = converted

    if not numeric_columns:
        numeric_columns = list(df.select_dtypes(include=[np.number]).columns)

    stats = {}
    totals = {}

    for col in numeric_columns:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                col_sum = float(round(s.sum(), 2))
                col_mean = float(round(s.mean(), 2))
                col_median = float(round(s.median(), 2))
                col_min = float(round(s.min(), 2))
                col_max = float(round(s.max(), 2))
                col_std = float(round(s.std(), 2)) if len(s) > 1 else 0.0

                stats[col] = {
                    "count": int(s.count()),
                    "sum": col_sum,
                    "mean": col_mean,
                    "median": col_median,
                    "min": col_min,
                    "max": col_max,
                    "std": col_std
                }
                totals[f"total_{col}"] = col_sum

    group_stats = {}
    if group_by and group_by in df.columns:
        grouped = df.groupby(group_by)[numeric_columns].agg(['sum', 'mean']).round(2)
        group_stats = grouped.to_dict()

    return {
        "numeric_columns": numeric_columns,
        "statistics": stats,
        "totals": totals,
        "group_statistics": group_stats,
        "row_count": len(df)
    }
