# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave profiler."""

from __future__ import annotations

import pandas as pd
import pytest

from dataweave.profiler import profile_dataframe, _detect_outliers_iqr


class TestProfiler:
    """Tests for the data profiler."""

    def test_profile_basic_stats(self, sample_df: pd.DataFrame) -> None:
        """Profiler computes correct row/column counts."""
        profile = profile_dataframe(sample_df)
        assert profile.row_count == 5
        assert profile.column_count == 7
        assert len(profile.columns) == 7

    def test_profile_numeric_stats(self, sample_df: pd.DataFrame) -> None:
        """Profiler computes numeric statistics for numeric columns."""
        profile = profile_dataframe(sample_df)
        amount_col = next(c for c in profile.columns if c.name == "amount")
        assert amount_col.mean is not None
        assert amount_col.min_val == 100.0
        assert amount_col.max_val == 300.0

    def test_profile_null_detection(self, sample_df_with_nulls: pd.DataFrame) -> None:
        """Profiler detects null counts and percentages."""
        profile = profile_dataframe(sample_df_with_nulls)
        name_col = next(c for c in profile.columns if c.name == "name")
        assert name_col.null_count == 2
        assert name_col.null_pct == pytest.approx(40.0)

    def test_profile_string_stats(self, sample_df: pd.DataFrame) -> None:
        """Profiler computes string length statistics."""
        profile = profile_dataframe(sample_df)
        name_col = next(c for c in profile.columns if c.name == "name")
        assert name_col.min_length is not None
        assert name_col.max_length is not None

    def test_profile_duplicate_detection(self) -> None:
        """Profiler counts duplicate rows."""
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        profile = profile_dataframe(df)
        assert profile.duplicate_row_count == 1

    def test_profile_top_values(self, sample_df: pd.DataFrame) -> None:
        """Profiler extracts top values per column."""
        profile = profile_dataframe(sample_df)
        cat_col = next(c for c in profile.columns if c.name == "category")
        assert len(cat_col.top_values) > 0

    def test_profile_to_dict(self, sample_df: pd.DataFrame) -> None:
        """Profile serializes to a dictionary."""
        profile = profile_dataframe(sample_df)
        d = profile.to_dict()
        assert "row_count" in d
        assert "columns" in d
        assert len(d["columns"]) == 7

    def test_outlier_detection_iqr(self) -> None:
        """IQR outlier detection finds extreme values."""
        # Normal values with two outliers
        series = pd.Series([10, 11, 12, 13, 14, 15, 100, -50])
        outlier_count = _detect_outliers_iqr(series)
        assert outlier_count >= 2

    def test_profile_memory_usage(self, sample_df: pd.DataFrame) -> None:
        """Profiler reports non-zero memory usage."""
        profile = profile_dataframe(sample_df)
        assert profile.memory_usage_bytes > 0
