# MIT License
# Copyright (c) 2024 Maharshi Soni

"""YAML pipeline configuration loader for DataWeave."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dataweave.models import PipelineConfig


def load_pipeline(path: str | Path) -> PipelineConfig:
    """Load and validate a pipeline configuration from a YAML file.

    Args:
        path: Path to the YAML pipeline file.

    Returns:
        A validated PipelineConfig instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError: If the YAML is malformed.
        pydantic.ValidationError: If the config does not match the schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty pipeline config: {path}")

    return PipelineConfig(**raw)


def load_pipeline_from_dict(data: dict[str, Any]) -> PipelineConfig:
    """Load a pipeline configuration from a dictionary.

    Args:
        data: Dictionary matching the PipelineConfig schema.

    Returns:
        A validated PipelineConfig instance.
    """
    return PipelineConfig(**data)
