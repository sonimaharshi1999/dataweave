# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Data profiling and anomaly detection for DataWeave."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import numpy as np

from dataweave.schema import infer_schema, DataSchema


@dataclass
class ColumnProfile:
    """Statistical profile for a single column."""

    name: str
    dtype: str
    inferred_type: str
    count: int
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    # Numeric stats
    mean: float | None = None
    std: float | None = None
    min_val: Any = None
    q25: float | None = None
    median: float | None = None
    q75: float | None = None
    max_val: Any = None
    # String stats
    min_length: int | None = None
    max_length: int | None = None
    avg_length: float | None = None
    # Anomalies
    outlier_count: int = 0
    top_values: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class DataProfile:
    """Full profile of a dataset."""

    row_count: int
    column_count: int
    memory_usage_bytes: int
    schema: DataSchema
    columns: list[ColumnProfile] = field(default_factory=list)
    duplicate_row_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to a serializable dictionary."""
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "memory_usage_bytes": self.memory_usage_bytes,
            "duplicate_row_count": self.duplicate_row_count,
            "columns": [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "inferred_type": c.inferred_type,
                    "count": c.count,
                    "null_count": c.null_count,
                    "null_pct": round(c.null_pct, 2),
                    "unique_count": c.unique_count,
                    "unique_pct": round(c.unique_pct, 2),
                    "mean": c.mean,
                    "std": c.std,
                    "min": c.min_val,
                    "q25": c.q25,
                    "median": c.median,
                    "q75": c.q75,
                    "max": c.max_val,
                    "min_length": c.min_length,
                    "max_length": c.max_length,
                    "avg_length": c.avg_length,
                    "outlier_count": c.outlier_count,
                    "top_values": c.top_values,
                }
                for c in self.columns
            ],
        }


def _detect_outliers_iqr(series: pd.Series) -> int:
    """Count outliers using the IQR method.

    Args:
        series: Numeric pandas Series.

    Returns:
        Number of outlier values.
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = series[(series < lower) | (series > upper)]
    return int(len(outliers))


def _profile_column(series: pd.Series) -> ColumnProfile:
    """Generate a statistical profile for a single column.

    Args:
        series: A pandas Series to profile.

    Returns:
        ColumnProfile with all computed statistics.
    """
    from dataweave.schema import _classify_dtype

    count = int(series.count())
    null_count = int(series.isna().sum())
    total = len(series)
    null_pct = (null_count / total * 100) if total > 0 else 0.0
    unique_count = int(series.nunique())
    unique_pct = (unique_count / total * 100) if total > 0 else 0.0

    profile = ColumnProfile(
        name=str(series.name),
        dtype=str(series.dtype),
        inferred_type=_classify_dtype(series),
        count=count,
        null_count=null_count,
        null_pct=null_pct,
        unique_count=unique_count,
        unique_pct=unique_pct,
    )

    # Top values (for all types)
    if count > 0:
        vc = series.value_counts().head(10)
        profile.top_values = [(str(k), int(v)) for k, v in vc.items()]

    # Numeric statistics
    if pd.api.types.is_numeric_dtype(series.dtype):
        non_null = series.dropna()
        if len(non_null) > 0:
            profile.mean = round(float(non_null.mean()), 4)
            profile.std = round(float(non_null.std()), 4) if len(non_null) > 1 else 0.0
            profile.min_val = float(non_null.min())
            profile.q25 = float(non_null.quantile(0.25))
            profile.median = float(non_null.median())
            profile.q75 = float(non_null.quantile(0.75))
            profile.max_val = float(non_null.max())
            profile.outlier_count = _detect_outliers_iqr(non_null)

    # String statistics
    elif pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
        non_null = series.dropna().astype(str)
        if len(non_null) > 0:
            lengths = non_null.str.len()
            profile.min_length = int(lengths.min())
            profile.max_length = int(lengths.max())
            profile.avg_length = round(float(lengths.mean()), 2)

    return profile


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Generate a full statistical profile for a DataFrame.

    Args:
        df: The DataFrame to profile.

    Returns:
        DataProfile containing statistics for every column and the dataset.
    """
    schema = infer_schema(df)

    col_profiles: list[ColumnProfile] = []
    for col in df.columns:
        col_profiles.append(_profile_column(df[col]))

    return DataProfile(
        row_count=len(df),
        column_count=len(df.columns),
        memory_usage_bytes=int(df.memory_usage(deep=True).sum()),
        schema=schema,
        columns=col_profiles,
        duplicate_row_count=int(df.duplicated().sum()),
    )
