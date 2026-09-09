# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Click-based CLI for DataWeave."""

from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from dataweave.__version__ import __version__


@click.group()
@click.version_option(version=__version__, prog_name="dataweave")
def cli() -> None:
    """DataWeave - Declarative Data Pipeline Framework.

    Define ETL workflows in YAML. Transform, validate, profile, and load data
    with zero configuration.
    """
    pass


@cli.command()
@click.argument("pipeline", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Override output path from the pipeline config.",
)
@click.option("--dry-run", is_flag=True, help="Validate config without executing.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed step output.")
def run(pipeline: str, output: str | None, dry_run: bool, verbose: bool) -> None:
    """Run a YAML-defined data pipeline.

    PIPELINE is the path to a .yaml pipeline configuration file.
    """
    from dataweave.loader import load_pipeline
    from dataweave.engine import PipelineEngine

    config = load_pipeline(pipeline)
    click.echo(f"Pipeline: {config.name}")
    click.echo(f"Source: {config.source.path}")
    click.echo(f"Steps: {len(config.steps)}")

    if output:
        if config.output:
            config.output.path = output
        else:
            from dataweave.models import OutputConfig
            config.output = OutputConfig(path=output)

    if dry_run:
        click.echo("\n[DRY RUN] Configuration is valid. No data was processed.")
        for i, step in enumerate(config.steps, 1):
            click.echo(f"  Step {i}: {step.name} ({step.operator.value})")
        return

    base_dir = Path(pipeline).parent
    engine = PipelineEngine(config, base_dir=base_dir)
    result = engine.run()

    if result.success:
        click.secho("\nPipeline completed successfully!", fg="green", bold=True)
    else:
        click.secho(f"\nPipeline failed: {result.error}", fg="red", bold=True)

    click.echo(f"Total duration: {result.total_duration_ms:.1f}ms")
    click.echo(f"Final shape: {result.final_row_count} rows x {result.final_column_count} columns")

    if result.output_path:
        click.echo(f"Output: {result.output_path}")

    if verbose:
        click.echo("\nStep Details:")
        for sr in result.step_results:
            status = click.style("OK", fg="green") if sr.success else click.style("FAIL", fg="red")
            click.echo(
                f"  [{status}] {sr.step_name} ({sr.operator}): "
                f"{sr.rows_in} -> {sr.rows_out} rows, {sr.duration_ms}ms"
            )
            if sr.error:
                click.echo(f"       Error: {sr.error}")

    if not result.success:
        raise SystemExit(1)


@cli.command()
@click.argument("data_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output path for the HTML report (default: <data_file>_profile.html).",
)
@click.option("--json", "as_json", is_flag=True, help="Output profile as JSON instead of HTML.")
def profile(data_file: str, output: str | None, as_json: bool) -> None:
    """Generate a profiling report for a CSV data file.

    DATA_FILE is the path to a CSV file to profile.
    """
    import json as json_mod
    from dataweave.profiler import profile_dataframe
    from dataweave.report import generate_report

    click.echo(f"Profiling: {data_file}")
    df = pd.read_csv(data_file)
    click.echo(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")

    prof = profile_dataframe(df)

    if as_json:
        out_path = output or str(Path(data_file).with_suffix(".profile.json"))
        Path(out_path).write_text(
            json_mod.dumps(prof.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        click.echo(f"JSON profile written to: {out_path}")
    else:
        out_path = output or str(Path(data_file).with_suffix("")) + "_profile.html"
        generate_report(prof, out_path)
        click.secho(f"HTML report written to: {out_path}", fg="green")

    # Summary
    click.echo(f"\nDuplicate rows: {prof.duplicate_row_count}")
    for cp in prof.columns:
        if cp.null_pct > 0:
            click.echo(f"  {cp.name}: {cp.null_pct:.1f}% nulls")
        if cp.outlier_count > 0:
            click.echo(f"  {cp.name}: {cp.outlier_count} outliers detected")


@cli.command()
@click.argument("data_file", type=click.Path(exists=True))
@click.argument("rules_file", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True, help="Show all check results, not just failures.")
def validate(data_file: str, rules_file: str, verbose: bool) -> None:
    """Validate a CSV file against a YAML rules file.

    DATA_FILE is the path to a CSV file.
    RULES_FILE is a YAML file with validation rules.
    """
    import yaml
    from dataweave.models import ValidationRule
    from dataweave.operators.core import run_validations

    click.echo(f"Validating: {data_file}")
    df = pd.read_csv(data_file)

    with open(rules_file, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rules = [ValidationRule(**r) for r in raw.get("rules", raw.get("validations", []))]
    click.echo(f"Rules: {len(rules)}")

    results = run_validations(df, rules)

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    for r in results:
        if r["passed"] and not verbose:
            continue
        icon = click.style("PASS", fg="green") if r["passed"] else click.style("FAIL", fg="red")
        sev = f" [{r['severity']}]" if not r["passed"] else ""
        click.echo(f"  [{icon}] {r['column']}.{r['check']}{sev}: {r['message']}")

    click.echo(f"\n{passed} passed, {failed} failed out of {len(results)} checks")

    if failed > 0:
        errors = [r for r in results if not r["passed"] and r["severity"] == "error"]
        if errors:
            click.secho(f"{len(errors)} error-level failures", fg="red", bold=True)
            raise SystemExit(1)
        else:
            click.secho("All failures are warnings only", fg="yellow")


if __name__ == "__main__":
    cli()
