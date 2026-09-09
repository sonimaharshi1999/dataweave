# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Pydantic models for DataWeave pipeline configuration."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class OperatorType(str, Enum):
    """Supported pipeline operator types."""

    FILTER = "filter"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"
    JOIN = "join"
    VALIDATE = "validate"
    RENAME = "rename"
    SELECT = "select"
    SORT = "sort"
    DEDUPLICATE = "deduplicate"
    FILL_NA = "fill_na"


class DataSourceConfig(BaseModel):
    """Configuration for a data source."""

    path: str = Field(..., description="File path to the data source (CSV)")
    format: str = Field(default="csv", description="File format")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Extra read options"
    )


class JoinConfig(BaseModel):
    """Configuration for a join operation."""

    right_source: str = Field(..., description="Path to the right dataset")
    on: str | list[str] = Field(..., description="Column(s) to join on")
    how: str = Field(default="inner", description="Join type: inner, left, right, outer")

    @field_validator("how")
    @classmethod
    def validate_how(cls, v: str) -> str:
        allowed = {"inner", "left", "right", "outer"}
        if v not in allowed:
            raise ValueError(f"Join type must be one of {allowed}, got '{v}'")
        return v


class ValidationRule(BaseModel):
    """A single data validation rule."""

    column: str = Field(..., description="Column to validate")
    check: str = Field(..., description="Check type: not_null, unique, min, max, pattern, in_set")
    value: Any = Field(default=None, description="Expected value for the check")
    severity: str = Field(default="error", description="error or warning")

    @field_validator("check")
    @classmethod
    def validate_check(cls, v: str) -> str:
        allowed = {"not_null", "unique", "min", "max", "pattern", "in_set", "dtype"}
        if v not in allowed:
            raise ValueError(f"Check must be one of {allowed}, got '{v}'")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in {"error", "warning"}:
            raise ValueError(f"Severity must be 'error' or 'warning', got '{v}'")
        return v


class StepConfig(BaseModel):
    """Configuration for a single pipeline step."""

    name: str = Field(..., description="Step name")
    operator: OperatorType = Field(..., description="Operator type")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Operator-specific parameters"
    )
    join: Optional[JoinConfig] = Field(default=None, description="Join config (if operator is join)")
    validations: list[ValidationRule] = Field(
        default_factory=list, description="Validation rules (if operator is validate)"
    )


class OutputConfig(BaseModel):
    """Configuration for pipeline output."""

    path: str = Field(..., description="Output file path")
    format: str = Field(default="csv", description="Output format")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Extra write options"
    )


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration parsed from YAML."""

    name: str = Field(..., description="Pipeline name")
    description: str = Field(default="", description="Pipeline description")
    source: DataSourceConfig = Field(..., description="Input data source")
    steps: list[StepConfig] = Field(default_factory=list, description="Pipeline steps")
    output: Optional[OutputConfig] = Field(default=None, description="Output config")
