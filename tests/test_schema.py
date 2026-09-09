# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave schema inference."""

from __future__ import annotations

import pandas as pd

from dataweave.schema import infer_schema


class TestSchemaInference:
    """Tests for automatic schema inference."""

    def test_infer_integer_column(self) -> None:
        """Integer columns are detected correctly."""
        df = pd.DataFrame({"count": [1, 2, 3, 4, 5]})
        schema = infer_schema(df)
        assert schema.columns[0].inferred_type == "integer"

    def test_infer_float_column(self) -> None:
        """Float columns are detected correctly."""
        df = pd.DataFrame({"price": [1.5, 2.0, 3.7]})
        schema = infer_schema(df)
        assert schema.columns[0].inferred_type == "float"

    def test_infer_email_column(self) -> None:
        """Email-like string columns are detected as email."""
        df = pd.DataFrame({"email": ["a@b.com", "c@d.org", "e@f.net"]})
        schema = infer_schema(df)
        assert schema.columns[0].inferred_type == "email"

    def test_nullable_detection(self) -> None:
        """Columns with nulls are flagged as nullable."""
        df = pd.DataFrame({"val": [1.0, None, 3.0]})
        schema = infer_schema(df)
        assert schema.columns[0].nullable is True

    def test_schema_row_and_column_counts(self, sample_df: pd.DataFrame) -> None:
        """Schema reports correct row and column counts."""
        schema = infer_schema(sample_df)
        assert schema.row_count == 5
        assert schema.column_count == 7

    def test_schema_to_dict(self) -> None:
        """Schema serializes to a dictionary."""
        df = pd.DataFrame({"x": [1, 2]})
        schema = infer_schema(df)
        d = schema.to_dict()
        assert "columns" in d
        assert d["row_count"] == 2
