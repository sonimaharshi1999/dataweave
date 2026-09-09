# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave pipeline engine."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from dataweave.engine import PipelineEngine, PipelineResult
from dataweave.loader import load_pipeline, load_pipeline_from_dict
from dataweave.models import (
    DataSourceConfig,
    OperatorType,
    OutputConfig,
    PipelineConfig,
    StepConfig,
)


class TestPipelineEngine:
    """Tests for the pipeline execution engine."""

    def test_run_simple_pipeline(self, sample_csv: Path, tmp_path: Path) -> None:
        """Engine runs a simple filter + sort pipeline."""
        output_path = tmp_path / "output.csv"
        config = PipelineConfig(
            name="test_pipeline",
            source=DataSourceConfig(path=str(sample_csv)),
            steps=[
                StepConfig(
                    name="filter_active",
                    operator=OperatorType.FILTER,
                    params={"column": "status", "op": "eq", "value": "active"},
                ),
                StepConfig(
                    name="sort_amount",
                    operator=OperatorType.SORT,
                    params={"by": "amount", "ascending": False},
                ),
            ],
            output=OutputConfig(path=str(output_path)),
        )

        engine = PipelineEngine(config)
        result = engine.run()

        assert result.success is True
        assert result.final_row_count == 3
        assert output_path.exists()

        output_df = pd.read_csv(output_path)
        assert len(output_df) == 3
        assert output_df.iloc[0]["amount"] == 300.0  # Dave first (highest)

    def test_run_to_dataframe(self, sample_csv: Path) -> None:
        """run_to_dataframe returns the DataFrame directly."""
        config = PipelineConfig(
            name="df_test",
            source=DataSourceConfig(path=str(sample_csv)),
            steps=[
                StepConfig(
                    name="select_cols",
                    operator=OperatorType.SELECT,
                    params={"columns": ["id", "name", "amount"]},
                ),
            ],
        )
        engine = PipelineEngine(config)
        df = engine.run_to_dataframe()
        assert list(df.columns) == ["id", "name", "amount"]
        assert len(df) == 5

    def test_pipeline_result_on_missing_source(self, tmp_path: Path) -> None:
        """Engine returns failure result when source file is missing."""
        config = PipelineConfig(
            name="bad_source",
            source=DataSourceConfig(path=str(tmp_path / "nonexistent.csv")),
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.success is False
        assert "Failed to load source" in (result.error or "")

    def test_step_timing_recorded(self, sample_csv: Path) -> None:
        """Each step result includes timing information."""
        config = PipelineConfig(
            name="timing_test",
            source=DataSourceConfig(path=str(sample_csv)),
            steps=[
                StepConfig(
                    name="sort",
                    operator=OperatorType.SORT,
                    params={"by": "id"},
                ),
            ],
        )
        engine = PipelineEngine(config)
        result = engine.run()
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.step_results[0].duration_ms >= 0


class TestLoader:
    """Tests for YAML pipeline loading."""

    def test_load_from_yaml_file(self, tmp_path: Path) -> None:
        """load_pipeline reads and validates a YAML file."""
        yaml_content = {
            "name": "yaml_test",
            "source": {"path": "data.csv"},
            "steps": [
                {
                    "name": "filter",
                    "operator": "filter",
                    "params": {"column": "x", "op": "gt", "value": 0},
                }
            ],
        }
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml.dump(yaml_content), encoding="utf-8")

        config = load_pipeline(yaml_path)
        assert config.name == "yaml_test"
        assert len(config.steps) == 1

    def test_load_from_dict(self) -> None:
        """load_pipeline_from_dict creates a config from a dictionary."""
        config = load_pipeline_from_dict({
            "name": "dict_test",
            "source": {"path": "data.csv"},
        })
        assert config.name == "dict_test"

    def test_load_nonexistent_file_raises(self) -> None:
        """load_pipeline raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_pipeline("/nonexistent/path/pipeline.yaml")

    def test_load_sample_pipeline(self, samples_dir: Path) -> None:
        """The included sample pipeline.yaml parses successfully."""
        yaml_path = samples_dir / "pipeline.yaml"
        if yaml_path.exists():
            config = load_pipeline(yaml_path)
            assert config.name == "sales_etl_pipeline"
            assert len(config.steps) == 5
