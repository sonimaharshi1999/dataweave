# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Core built-in operators for DataWeave pipelines."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from dataweave.models import StepConfig, ValidationRule
from dataweave.operators.base import Operator, OperatorRegistry


class FilterOperator(Operator):
    """Filter rows based on a column condition.

    Params:
        column: Column name to filter on.
        op: Comparison operator (eq, ne, gt, ge, lt, le, in, not_in, contains).
        value: Value to compare against.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Apply filter to the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with filter params.

        Returns:
            Filtered DataFrame.
        """
        params = step.params
        column: str = params["column"]
        op: str = params.get("op", "eq")
        value: Any = params["value"]

        ops = {
            "eq": lambda s, v: s == v,
            "ne": lambda s, v: s != v,
            "gt": lambda s, v: s > v,
            "ge": lambda s, v: s >= v,
            "lt": lambda s, v: s < v,
            "le": lambda s, v: s <= v,
            "in": lambda s, v: s.isin(v),
            "not_in": lambda s, v: ~s.isin(v),
            "contains": lambda s, v: s.astype(str).str.contains(str(v), na=False),
        }

        if op not in ops:
            raise ValueError(f"Unknown filter op '{op}'. Supported: {list(ops.keys())}")

        mask = ops[op](df[column], value)
        return df[mask].reset_index(drop=True)


class TransformOperator(Operator):
    """Apply column transformations.

    Params:
        expressions: dict mapping new_column -> expression string.
            Expressions can reference existing columns with {col_name} syntax.
            Supported functions: upper, lower, strip, abs, round.
        drop: list of columns to drop after transform.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Apply transformations to the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with transform params.

        Returns:
            Transformed DataFrame.
        """
        params = step.params
        result = df.copy()

        expressions: dict[str, str] = params.get("expressions", {})
        for col_name, expr in expressions.items():
            result[col_name] = self._evaluate_expression(result, expr)

        drop_cols: list[str] = params.get("drop", [])
        if drop_cols:
            result = result.drop(columns=[c for c in drop_cols if c in result.columns])

        return result

    @staticmethod
    def _evaluate_expression(df: pd.DataFrame, expr: str) -> pd.Series:
        """Evaluate a simple transform expression.

        Args:
            df: Current DataFrame.
            expr: Expression string.

        Returns:
            Resulting Series.
        """
        expr = expr.strip()

        # Handle function-style: upper(column_name)
        func_match = re.match(r"^(\w+)\((.+)\)$", expr)
        if func_match:
            func_name = func_match.group(1).lower()
            col_name = func_match.group(2).strip()
            if col_name not in df.columns:
                raise ValueError(f"Column '{col_name}' not found in DataFrame")
            series = df[col_name]
            funcs = {
                "upper": lambda s: s.astype(str).str.upper(),
                "lower": lambda s: s.astype(str).str.lower(),
                "strip": lambda s: s.astype(str).str.strip(),
                "abs": lambda s: s.abs(),
                "round": lambda s: s.round(),
                "len": lambda s: s.astype(str).str.len(),
            }
            if func_name not in funcs:
                raise ValueError(f"Unknown function '{func_name}'")
            return funcs[func_name](series)

        # Handle arithmetic: col1 + col2, col1 * 2, etc.
        for op_char in [" + ", " - ", " * ", " / "]:
            if op_char in expr:
                left, right = expr.split(op_char, 1)
                left = left.strip()
                right = right.strip()
                left_val = df[left] if left in df.columns else pd.to_numeric(pd.Series([left] * len(df)), errors="coerce")
                right_val = df[right] if right in df.columns else pd.to_numeric(pd.Series([right] * len(df)), errors="coerce")
                op_map = {" + ": lambda a, b: a + b, " - ": lambda a, b: a - b, " * ": lambda a, b: a * b, " / ": lambda a, b: a / b}
                return op_map[op_char](left_val, right_val)

        # Fallback: treat as column reference
        if expr in df.columns:
            return df[expr].copy()

        raise ValueError(f"Cannot evaluate expression: '{expr}'")


class AggregateOperator(Operator):
    """Aggregate data by grouping columns.

    Params:
        group_by: Column(s) to group by.
        aggregations: dict mapping column -> agg_function (sum, mean, count, min, max, std).
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Apply aggregation to the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with aggregation params.

        Returns:
            Aggregated DataFrame.
        """
        params = step.params
        group_by = params["group_by"]
        if isinstance(group_by, str):
            group_by = [group_by]

        aggregations: dict[str, str] = params.get("aggregations", {})
        if not aggregations:
            raise ValueError("Aggregate operator requires 'aggregations' param")

        grouped = df.groupby(group_by, as_index=False)
        result = grouped.agg(**{
            f"{col}_{func}": pd.NamedAgg(column=col, aggfunc=func)
            for col, func in aggregations.items()
        })
        return result


class JoinOperator(Operator):
    """Join two DataFrames together.

    Params: uses step.join config (JoinConfig).
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Join a second dataset to the DataFrame.

        Args:
            df: Left DataFrame.
            step: Step configuration with join config.

        Returns:
            Joined DataFrame.
        """
        if step.join is None:
            raise ValueError("Join operator requires a 'join' configuration block")

        right_df = pd.read_csv(step.join.right_source)
        on = step.join.on
        if isinstance(on, str):
            on = [on]

        return df.merge(right_df, on=on, how=step.join.how)


class ValidateOperator(Operator):
    """Run data quality validation rules.

    Params: uses step.validations list of ValidationRule.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Validate the DataFrame and attach a __validation_results attribute.

        Args:
            df: Input DataFrame.
            step: Step configuration with validation rules.

        Returns:
            The same DataFrame (unmodified). Validation results are stored
            in df.attrs["validation_results"].

        Raises:
            ValueError: If any rule with severity='error' fails.
        """
        results = run_validations(df, step.validations)
        df = df.copy()
        df.attrs["validation_results"] = results

        errors = [r for r in results if not r["passed"] and r["severity"] == "error"]
        if errors:
            messages = "; ".join(
                f"[{r['column']}] {r['check']}: {r['message']}" for r in errors
            )
            raise ValueError(f"Validation failed: {messages}")

        return df


def run_validations(
    df: pd.DataFrame, rules: list[ValidationRule]
) -> list[dict[str, Any]]:
    """Execute validation rules against a DataFrame.

    Args:
        df: DataFrame to validate.
        rules: List of validation rules.

    Returns:
        List of result dicts with keys: column, check, passed, message, severity.
    """
    results: list[dict[str, Any]] = []

    for rule in rules:
        col = rule.column
        if col not in df.columns:
            results.append({
                "column": col,
                "check": rule.check,
                "passed": False,
                "message": f"Column '{col}' not found",
                "severity": rule.severity,
            })
            continue

        series = df[col]
        passed = True
        message = "OK"

        if rule.check == "not_null":
            null_count = int(series.isna().sum())
            if null_count > 0:
                passed = False
                message = f"{null_count} null values found"

        elif rule.check == "unique":
            dup_count = int(series.duplicated().sum())
            if dup_count > 0:
                passed = False
                message = f"{dup_count} duplicate values found"

        elif rule.check == "min":
            min_val = series.min()
            if min_val < rule.value:
                passed = False
                message = f"Minimum value {min_val} is below threshold {rule.value}"

        elif rule.check == "max":
            max_val = series.max()
            if max_val > rule.value:
                passed = False
                message = f"Maximum value {max_val} exceeds threshold {rule.value}"

        elif rule.check == "pattern":
            non_null = series.dropna().astype(str)
            pattern = re.compile(str(rule.value))
            mismatches = non_null[~non_null.apply(lambda v: bool(pattern.match(v)))]
            if len(mismatches) > 0:
                passed = False
                message = f"{len(mismatches)} values do not match pattern '{rule.value}'"

        elif rule.check == "in_set":
            allowed = set(rule.value) if isinstance(rule.value, list) else {rule.value}
            invalid = series.dropna()[~series.dropna().isin(allowed)]
            if len(invalid) > 0:
                passed = False
                message = f"{len(invalid)} values not in allowed set"

        elif rule.check == "dtype":
            actual = str(series.dtype)
            if rule.value not in actual:
                passed = False
                message = f"Expected dtype containing '{rule.value}', got '{actual}'"

        results.append({
            "column": col,
            "check": rule.check,
            "passed": passed,
            "message": message,
            "severity": rule.severity,
        })

    return results


class RenameOperator(Operator):
    """Rename columns.

    Params:
        columns: dict mapping old_name -> new_name.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Rename columns in the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with rename params.

        Returns:
            DataFrame with renamed columns.
        """
        mapping: dict[str, str] = step.params.get("columns", {})
        return df.rename(columns=mapping)


class SelectOperator(Operator):
    """Select a subset of columns.

    Params:
        columns: list of column names to keep.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Select columns from the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with select params.

        Returns:
            DataFrame with only the selected columns.
        """
        columns: list[str] = step.params.get("columns", [])
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(f"Columns not found: {missing}")
        return df[columns].copy()


class SortOperator(Operator):
    """Sort by one or more columns.

    Params:
        by: Column name or list of column names.
        ascending: bool or list of bools (default True).
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Sort the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with sort params.

        Returns:
            Sorted DataFrame.
        """
        by = step.params["by"]
        ascending = step.params.get("ascending", True)
        return df.sort_values(by=by, ascending=ascending).reset_index(drop=True)


class DeduplicateOperator(Operator):
    """Remove duplicate rows.

    Params:
        subset: Column(s) to consider for dedup (optional, all columns if omitted).
        keep: 'first', 'last', or False (default 'first').
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Remove duplicate rows from the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with dedup params.

        Returns:
            Deduplicated DataFrame.
        """
        subset = step.params.get("subset", None)
        keep = step.params.get("keep", "first")
        return df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)


class FillNaOperator(Operator):
    """Fill missing values.

    Params:
        columns: dict mapping column -> fill_value.
        strategy: 'value' (default), 'mean', 'median', 'mode', 'ffill', 'bfill'.
    """

    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Fill null values in the DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration with fill_na params.

        Returns:
            DataFrame with nulls filled.
        """
        result = df.copy()
        strategy: str = step.params.get("strategy", "value")
        columns: dict[str, Any] = step.params.get("columns", {})

        if strategy == "value":
            for col, val in columns.items():
                if col in result.columns:
                    result[col] = result[col].fillna(val)
        elif strategy == "mean":
            for col in columns:
                if col in result.columns:
                    result[col] = result[col].fillna(result[col].mean())
        elif strategy == "median":
            for col in columns:
                if col in result.columns:
                    result[col] = result[col].fillna(result[col].median())
        elif strategy == "mode":
            for col in columns:
                if col in result.columns:
                    mode_val = result[col].mode()
                    if not mode_val.empty:
                        result[col] = result[col].fillna(mode_val.iloc[0])
        elif strategy in ("ffill", "bfill"):
            for col in columns:
                if col in result.columns:
                    result[col] = result[col].fillna(method=strategy)
        else:
            raise ValueError(f"Unknown fill_na strategy: '{strategy}'")

        return result


# Register all operators
OperatorRegistry.register("filter", FilterOperator)
OperatorRegistry.register("transform", TransformOperator)
OperatorRegistry.register("aggregate", AggregateOperator)
OperatorRegistry.register("join", JoinOperator)
OperatorRegistry.register("validate", ValidateOperator)
OperatorRegistry.register("rename", RenameOperator)
OperatorRegistry.register("select", SelectOperator)
OperatorRegistry.register("sort", SortOperator)
OperatorRegistry.register("deduplicate", DeduplicateOperator)
OperatorRegistry.register("fill_na", FillNaOperator)
