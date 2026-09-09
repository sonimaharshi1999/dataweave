# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Pipeline execution engine for DataWeave."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from dataweave.models import PipelineConfig, StepConfig
from dataweave.operators.base import OperatorRegistry

# Ensure all operators are registered by importing the core module.
import dataweave.operators.core  # noqa: F401


@dataclass
class StepResult:
    """Result from executing a single pipeline step."""

    step_name: str
    operator: str
    rows_in: int
    rows_out: int
    columns_out: int
    duration_ms: float
    success: bool
    error: str | None = None


@dataclass
class PipelineResult:
    """Result from executing an entire pipeline."""

    pipeline_name: str
    success: bool
    total_duration_ms: float
    step_results: list[StepResult] = field(default_factory=list)
    output_path: str | None = None
    final_row_count: int = 0
    final_column_count: int = 0
    error: str | None = None


class PipelineEngine:
    """Executes a DataWeave pipeline configuration against data."""

    def __init__(self, config: PipelineConfig, base_dir: Path | None = None) -> None:
        """Initialize the engine.

        Args:
            config: Validated pipeline configuration.
            base_dir: Base directory for resolving relative file paths.
                      Defaults to the current working directory.
        """
        self.config = config
        self.base_dir = base_dir or Path.cwd()

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a file path relative to the base directory.

        Args:
            path_str: Potentially relative path string.

        Returns:
            Resolved absolute Path.
        """
        p = Path(path_str)
        if p.is_absolute():
            return p
        return self.base_dir / p

    def _load_source(self) -> pd.DataFrame:
        """Load the source data from the configured path.

        Returns:
            The loaded DataFrame.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the format is unsupported.
        """
        source = self.config.source
        path = self._resolve_path(source.path)

        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        fmt = source.format.lower()
        if fmt == "csv":
            return pd.read_csv(path, **source.options)
        elif fmt == "json":
            return pd.read_json(path, **source.options)
        elif fmt == "parquet":
            return pd.read_parquet(path, **source.options)
        else:
            raise ValueError(f"Unsupported source format: '{fmt}'")

    def _write_output(self, df: pd.DataFrame) -> str | None:
        """Write the final DataFrame to the configured output.

        Args:
            df: Final DataFrame to write.

        Returns:
            Output path string, or None if no output configured.
        """
        if self.config.output is None:
            return None

        out = self.config.output
        path = self._resolve_path(out.path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fmt = out.format.lower()
        if fmt == "csv":
            df.to_csv(path, index=False, **out.options)
        elif fmt == "json":
            df.to_json(path, orient="records", indent=2, **out.options)
        elif fmt == "parquet":
            df.to_parquet(path, index=False, **out.options)
        else:
            raise ValueError(f"Unsupported output format: '{fmt}'")

        return str(path)

    def run(self) -> PipelineResult:
        """Execute the full pipeline.

        Returns:
            PipelineResult with details of each step and the final outcome.
        """
        pipeline_start = time.perf_counter()
        step_results: list[StepResult] = []

        try:
            df = self._load_source()
        except Exception as e:
            duration = (time.perf_counter() - pipeline_start) * 1000
            return PipelineResult(
                pipeline_name=self.config.name,
                success=False,
                total_duration_ms=duration,
                error=f"Failed to load source: {e}",
            )

        for step in self.config.steps:
            step_start = time.perf_counter()
            rows_in = len(df)

            try:
                operator = OperatorRegistry.get(step.operator.value)
                df = operator.execute(df, step)
                duration = (time.perf_counter() - step_start) * 1000

                step_results.append(StepResult(
                    step_name=step.name,
                    operator=step.operator.value,
                    rows_in=rows_in,
                    rows_out=len(df),
                    columns_out=len(df.columns),
                    duration_ms=round(duration, 2),
                    success=True,
                ))
            except Exception as e:
                duration = (time.perf_counter() - step_start) * 1000
                step_results.append(StepResult(
                    step_name=step.name,
                    operator=step.operator.value,
                    rows_in=rows_in,
                    rows_out=rows_in,
                    columns_out=len(df.columns),
                    duration_ms=round(duration, 2),
                    success=False,
                    error=str(e),
                ))

                total_duration = (time.perf_counter() - pipeline_start) * 1000
                return PipelineResult(
                    pipeline_name=self.config.name,
                    success=False,
                    total_duration_ms=round(total_duration, 2),
                    step_results=step_results,
                    final_row_count=len(df),
                    final_column_count=len(df.columns),
                    error=f"Step '{step.name}' failed: {e}",
                )

        # Write output
        output_path: str | None = None
        try:
            output_path = self._write_output(df)
        except Exception as e:
            total_duration = (time.perf_counter() - pipeline_start) * 1000
            return PipelineResult(
                pipeline_name=self.config.name,
                success=False,
                total_duration_ms=round(total_duration, 2),
                step_results=step_results,
                final_row_count=len(df),
                final_column_count=len(df.columns),
                error=f"Failed to write output: {e}",
            )

        total_duration = (time.perf_counter() - pipeline_start) * 1000
        return PipelineResult(
            pipeline_name=self.config.name,
            success=True,
            total_duration_ms=round(total_duration, 2),
            step_results=step_results,
            output_path=output_path,
            final_row_count=len(df),
            final_column_count=len(df.columns),
        )

    def run_to_dataframe(self) -> pd.DataFrame:
        """Execute the pipeline and return the final DataFrame directly.

        Returns:
            The transformed DataFrame.

        Raises:
            RuntimeError: If the pipeline fails at any step.
        """
        df = self._load_source()

        for step in self.config.steps:
            operator = OperatorRegistry.get(step.operator.value)
            df = operator.execute(df, step)

        return df
