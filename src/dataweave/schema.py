# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Schema inference and type detection for DataWeave."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ColumnSchema:
    """Inferred schema for a single column."""

    name: str
    pandas_dtype: str
    inferred_type: str
    nullable: bool
    unique_count: int
    null_count: int
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class DataSchema:
    """Inferred schema for an entire dataset."""

    columns: list[ColumnSchema]
    row_count: int
    column_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize schema to a dictionary."""
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [
                {
                    "name": c.name,
                    "pandas_dtype": c.pandas_dtype,
                    "inferred_type": c.inferred_type,
                    "nullable": c.nullable,
                    "unique_count": c.unique_count,
                    "null_count": c.null_count,
                    "sample_values": c.sample_values,
                }
                for c in self.columns
            ],
        }


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_URL_RE = re.compile(r"^https?://")


def _infer_semantic_type(series: pd.Series) -> str:
    """Infer a semantic type from string column values.

    Args:
        series: A pandas Series of string values.

    Returns:
        A string label for the inferred semantic type.
    """
    sample = series.dropna().head(50)
    if sample.empty:
        return "unknown"

    str_vals = sample.astype(str)

    if str_vals.apply(lambda v: bool(_EMAIL_RE.match(v))).mean() > 0.8:
        return "email"
    if str_vals.apply(lambda v: bool(_DATE_RE.match(v))).mean() > 0.8:
        return "date_string"
    if str_vals.apply(lambda v: bool(_URL_RE.match(v))).mean() > 0.8:
        return "url"

    return "text"


def _classify_dtype(series: pd.Series) -> str:
    """Map pandas dtype to a human-readable type label.

    Args:
        series: A pandas Series.

    Returns:
        A string type label (integer, float, boolean, datetime, text, etc.).
    """
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
        return _infer_semantic_type(series)
    return "unknown"


def infer_schema(df: pd.DataFrame) -> DataSchema:
    """Infer schema from a pandas DataFrame.

    Args:
        df: The DataFrame to analyze.

    Returns:
        A DataSchema describing the structure and types of the data.
    """
    columns: list[ColumnSchema] = []
    for col in df.columns:
        series = df[col]
        sample = series.dropna().head(5).tolist()
        columns.append(
            ColumnSchema(
                name=str(col),
                pandas_dtype=str(series.dtype),
                inferred_type=_classify_dtype(series),
                nullable=bool(series.isna().any()),
                unique_count=int(series.nunique()),
                null_count=int(series.isna().sum()),
                sample_values=sample,
            )
        )

    return DataSchema(
        columns=columns,
        row_count=len(df),
        column_count=len(df.columns),
    )
