# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dataweave.models import (
    DataSourceConfig,
    JoinConfig,
    OperatorType,
    OutputConfig,
    PipelineConfig,
    StepConfig,
    ValidationRule,
)


class TestPipelineConfig:
    """Tests for pipeline configuration parsing."""

    def test_minimal_pipeline_config(self) -> None:
        """A pipeline needs at minimum a name and a source."""
        config = PipelineConfig(
            name="test",
            source=DataSourceConfig(path="data.csv"),
        )
        assert config.name == "test"
        assert config.source.path == "data.csv"
        assert config.source.format == "csv"
        assert config.steps == []
        assert config.output is None

    def test_full_pipeline_config(self) -> None:
        """A fully specified pipeline parses all fields."""
        config = PipelineConfig(
            name="full_test",
            description="A full test pipeline",
            source=DataSourceConfig(path="input.csv", format="csv"),
            steps=[
                StepConfig(
                    name="filter_active",
                    operator=OperatorType.FILTER,
                    params={"column": "status", "op": "eq", "value": "active"},
                ),
            ],
            output=OutputConfig(path="output.csv"),
        )
        assert len(config.steps) == 1
        assert config.steps[0].operator == OperatorType.FILTER
        assert config.output is not None

    def test_invalid_join_type_rejected(self) -> None:
        """JoinConfig rejects invalid join types."""
        with pytest.raises(ValidationError):
            JoinConfig(right_source="other.csv", on="id", how="cross")

    def test_invalid_validation_check_rejected(self) -> None:
        """ValidationRule rejects unknown check types."""
        with pytest.raises(ValidationError):
            ValidationRule(column="x", check="nonexistent")

    def test_validation_rule_severity_default(self) -> None:
        """ValidationRule defaults severity to error."""
        rule = ValidationRule(column="id", check="not_null")
        assert rule.severity == "error"
