# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Tests for DataWeave CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from dataweave.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


class TestCLI:
    """Tests for the Click CLI commands."""

    def test_version(self, runner: CliRunner) -> None:
        """--version prints version info."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "dataweave" in result.output

    def test_run_dry_run(self, runner: CliRunner, samples_dir: Path) -> None:
        """run --dry-run validates config without executing."""
        pipeline_path = samples_dir / "pipeline.yaml"
        if not pipeline_path.exists():
            pytest.skip("Sample pipeline.yaml not found")

        result = runner.invoke(cli, ["run", str(pipeline_path), "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_profile_command(self, runner: CliRunner, sample_csv: Path, tmp_path: Path) -> None:
        """profile generates an HTML report."""
        output_path = tmp_path / "report.html"
        result = runner.invoke(cli, [
            "profile", str(sample_csv), "-o", str(output_path),
        ])
        assert result.exit_code == 0
        assert output_path.exists()
        html = output_path.read_text(encoding="utf-8")
        assert "DataWeave Profile Report" in html

    def test_profile_json(self, runner: CliRunner, sample_csv: Path, tmp_path: Path) -> None:
        """profile --json outputs JSON instead of HTML."""
        output_path = tmp_path / "profile.json"
        result = runner.invoke(cli, [
            "profile", str(sample_csv), "-o", str(output_path), "--json",
        ])
        assert result.exit_code == 0
        assert output_path.exists()

    def test_validate_command(
        self, runner: CliRunner, sample_csv: Path, tmp_path: Path
    ) -> None:
        """validate runs checks from a rules YAML."""
        rules_yaml = tmp_path / "rules.yaml"
        rules_yaml.write_text(
            "rules:\n"
            "  - column: id\n"
            "    check: not_null\n"
            "    severity: error\n"
            "  - column: id\n"
            "    check: unique\n"
            "    severity: error\n",
            encoding="utf-8",
        )
        result = runner.invoke(cli, [
            "validate", str(sample_csv), str(rules_yaml), "-v",
        ])
        assert result.exit_code == 0
        assert "2 passed" in result.output
