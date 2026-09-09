# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave pipeline operators."""

from __future__ import annotations

import pytest
import pandas as pd

from dataweave.models import OperatorType, StepConfig, ValidationRule
from dataweave.operators.base import OperatorRegistry
from dataweave.operators.core import (
    FilterOperator,
    TransformOperator,
    AggregateOperator,
    SelectOperator,
    SortOperator,
    DeduplicateOperator,
    RenameOperator,
    FillNaOperator,
    ValidateOperator,
    run_validations,
)


class TestFilterOperator:
    """Tests for the filter operator."""

    def test_filter_eq(self, sample_df: pd.DataFrame) -> None:
        """Filter with eq keeps only matching rows."""
        step = StepConfig(
            name="filter_active",
            operator=OperatorType.FILTER,
            params={"column": "status", "op": "eq", "value": "active"},
        )
        result = FilterOperator().execute(sample_df, step)
        assert len(result) == 3
        assert all(result["status"] == "active")

    def test_filter_gt(self, sample_df: pd.DataFrame) -> None:
        """Filter with gt keeps rows above the threshold."""
        step = StepConfig(
            name="filter_high",
            operator=OperatorType.FILTER,
            params={"column": "amount", "op": "gt", "value": 150},
        )
        result = FilterOperator().execute(sample_df, step)
        assert len(result) == 3  # 200, 250, 300
        assert all(result["amount"] > 150)

    def test_filter_in(self, sample_df: pd.DataFrame) -> None:
        """Filter with in keeps rows in the allowed set."""
        step = StepConfig(
            name="filter_cats",
            operator=OperatorType.FILTER,
            params={"column": "category", "op": "in", "value": ["A", "C"]},
        )
        result = FilterOperator().execute(sample_df, step)
        assert len(result) == 3

    def test_filter_contains(self, sample_df: pd.DataFrame) -> None:
        """Filter with contains does substring matching."""
        step = StepConfig(
            name="filter_name",
            operator=OperatorType.FILTER,
            params={"column": "name", "op": "contains", "value": "a"},
        )
        result = FilterOperator().execute(sample_df, step)
        # "Carol", "Dave" contain lowercase 'a'
        assert len(result) == 2


class TestTransformOperator:
    """Tests for the transform operator."""

    def test_arithmetic_expression(self, sample_df: pd.DataFrame) -> None:
        """Transform with arithmetic creates a new column."""
        step = StepConfig(
            name="compute",
            operator=OperatorType.TRANSFORM,
            params={"expressions": {"total": "amount * quantity"}},
        )
        result = TransformOperator().execute(sample_df, step)
        assert "total" in result.columns
        assert result.loc[0, "total"] == 200.0  # 100 * 2

    def test_function_expression(self, sample_df: pd.DataFrame) -> None:
        """Transform with a function call modifies values."""
        step = StepConfig(
            name="upper",
            operator=OperatorType.TRANSFORM,
            params={"expressions": {"upper_name": "upper(name)"}},
        )
        result = TransformOperator().execute(sample_df, step)
        assert result.loc[0, "upper_name"] == "ALICE"

    def test_drop_columns(self, sample_df: pd.DataFrame) -> None:
        """Transform with drop removes specified columns."""
        step = StepConfig(
            name="drop",
            operator=OperatorType.TRANSFORM,
            params={"drop": ["email", "status"]},
        )
        result = TransformOperator().execute(sample_df, step)
        assert "email" not in result.columns
        assert "status" not in result.columns


class TestAggregateOperator:
    """Tests for the aggregate operator."""

    def test_aggregate_sum(self, sample_df: pd.DataFrame) -> None:
        """Aggregate sums values per group."""
        step = StepConfig(
            name="agg",
            operator=OperatorType.AGGREGATE,
            params={
                "group_by": "category",
                "aggregations": {"amount": "sum"},
            },
        )
        result = AggregateOperator().execute(sample_df, step)
        assert len(result) == 3  # A, B, C
        assert "amount_sum" in result.columns


class TestSelectOperator:
    """Tests for the select operator."""

    def test_select_columns(self, sample_df: pd.DataFrame) -> None:
        """Select keeps only the specified columns."""
        step = StepConfig(
            name="select",
            operator=OperatorType.SELECT,
            params={"columns": ["id", "name"]},
        )
        result = SelectOperator().execute(sample_df, step)
        assert list(result.columns) == ["id", "name"]

    def test_select_missing_column_raises(self, sample_df: pd.DataFrame) -> None:
        """Select raises when a column does not exist."""
        step = StepConfig(
            name="select_bad",
            operator=OperatorType.SELECT,
            params={"columns": ["id", "nonexistent"]},
        )
        with pytest.raises(ValueError, match="Columns not found"):
            SelectOperator().execute(sample_df, step)


class TestSortOperator:
    """Tests for the sort operator."""

    def test_sort_ascending(self, sample_df: pd.DataFrame) -> None:
        """Sort orders rows ascending by default."""
        step = StepConfig(
            name="sort",
            operator=OperatorType.SORT,
            params={"by": "amount", "ascending": True},
        )
        result = SortOperator().execute(sample_df, step)
        assert result.iloc[0]["amount"] == 100.0
        assert result.iloc[-1]["amount"] == 300.0


class TestDeduplicateOperator:
    """Tests for the deduplicate operator."""

    def test_deduplicate_removes_dupes(self) -> None:
        """Deduplicate removes exact duplicate rows."""
        df = pd.DataFrame({"a": [1, 1, 2, 3, 3], "b": ["x", "x", "y", "z", "z"]})
        step = StepConfig(
            name="dedup",
            operator=OperatorType.DEDUPLICATE,
            params={},
        )
        result = DeduplicateOperator().execute(df, step)
        assert len(result) == 3


class TestRenameOperator:
    """Tests for the rename operator."""

    def test_rename_columns(self, sample_df: pd.DataFrame) -> None:
        """Rename changes column names."""
        step = StepConfig(
            name="rename",
            operator=OperatorType.RENAME,
            params={"columns": {"name": "customer_name", "amount": "total_amount"}},
        )
        result = RenameOperator().execute(sample_df, step)
        assert "customer_name" in result.columns
        assert "total_amount" in result.columns
        assert "name" not in result.columns


class TestFillNaOperator:
    """Tests for the fill_na operator."""

    def test_fill_with_value(self, sample_df_with_nulls: pd.DataFrame) -> None:
        """Fill nulls with a specified value."""
        step = StepConfig(
            name="fill",
            operator=OperatorType.FILL_NA,
            params={"strategy": "value", "columns": {"name": "Unknown", "grade": "N/A"}},
        )
        result = FillNaOperator().execute(sample_df_with_nulls, step)
        assert result.loc[1, "name"] == "Unknown"
        assert result.loc[3, "grade"] == "N/A"

    def test_fill_with_mean(self, sample_df_with_nulls: pd.DataFrame) -> None:
        """Fill nulls with column mean."""
        step = StepConfig(
            name="fill_mean",
            operator=OperatorType.FILL_NA,
            params={"strategy": "mean", "columns": {"score": None}},
        )
        result = FillNaOperator().execute(sample_df_with_nulls, step)
        assert result["score"].isna().sum() == 0


class TestValidation:
    """Tests for validation rules."""

    def test_not_null_passes(self, sample_df: pd.DataFrame) -> None:
        """not_null passes when column has no nulls."""
        rules = [ValidationRule(column="id", check="not_null")]
        results = run_validations(sample_df, rules)
        assert results[0]["passed"] is True

    def test_not_null_fails(self, sample_df_with_nulls: pd.DataFrame) -> None:
        """not_null fails when column has nulls."""
        rules = [ValidationRule(column="name", check="not_null")]
        results = run_validations(sample_df_with_nulls, rules)
        assert results[0]["passed"] is False

    def test_unique_passes(self, sample_df: pd.DataFrame) -> None:
        """unique passes when all values are distinct."""
        rules = [ValidationRule(column="id", check="unique")]
        results = run_validations(sample_df, rules)
        assert results[0]["passed"] is True

    def test_min_check(self, sample_df: pd.DataFrame) -> None:
        """min check fails when a value is below the threshold."""
        rules = [ValidationRule(column="amount", check="min", value=150)]
        results = run_validations(sample_df, rules)
        assert results[0]["passed"] is False  # 100 < 150

    def test_pattern_check(self, sample_df: pd.DataFrame) -> None:
        """pattern check validates regex against string values."""
        rules = [ValidationRule(column="email", check="pattern", value=r"^.+@.+\..+$")]
        results = run_validations(sample_df, rules)
        assert results[0]["passed"] is True

    def test_in_set_check(self, sample_df: pd.DataFrame) -> None:
        """in_set check validates membership."""
        rules = [ValidationRule(column="category", check="in_set", value=["A", "B", "C"])]
        results = run_validations(sample_df, rules)
        assert results[0]["passed"] is True

    def test_validate_operator_raises_on_error(self, sample_df_with_nulls: pd.DataFrame) -> None:
        """ValidateOperator raises ValueError on error-severity failures."""
        step = StepConfig(
            name="validate",
            operator=OperatorType.VALIDATE,
            validations=[
                ValidationRule(column="name", check="not_null", severity="error"),
            ],
        )
        with pytest.raises(ValueError, match="Validation failed"):
            ValidateOperator().execute(sample_df_with_nulls, step)


class TestOperatorRegistry:
    """Tests for the operator registry."""

    def test_all_operators_registered(self) -> None:
        """All declared operator types are registered."""
        ops = OperatorRegistry.list_operators()
        expected = {
            "filter", "transform", "aggregate", "join", "validate",
            "rename", "select", "sort", "deduplicate", "fill_na",
        }
        assert expected.issubset(set(ops))

    def test_unknown_operator_raises(self) -> None:
        """Requesting an unknown operator raises KeyError."""
        with pytest.raises(KeyError, match="Unknown operator"):
            OperatorRegistry.get("nonexistent")
