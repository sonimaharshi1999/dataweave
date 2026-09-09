# MIT License
# Copyright (c) 2024 Maharshi Soni

"""HTML profiling report generation for DataWeave."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, BaseLoader

from dataweave.profiler import DataProfile

REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DataWeave Profile Report</title>
<style>
  :root { --bg: #f8f9fa; --card: #fff; --border: #dee2e6; --text: #212529;
          --accent: #0d6efd; --green: #198754; --red: #dc3545; --orange: #fd7e14; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 1.8rem; margin-bottom: 0.5rem; color: var(--accent); }
  h2 { font-size: 1.3rem; margin: 1.5rem 0 0.8rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.3rem; }
  h3 { font-size: 1.1rem; margin: 1rem 0 0.5rem; }
  .subtitle { color: #6c757d; margin-bottom: 1.5rem; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
  .summary-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
                  padding: 1rem; text-align: center; }
  .summary-card .value { font-size: 1.8rem; font-weight: 700; color: var(--accent); }
  .summary-card .label { font-size: 0.85rem; color: #6c757d; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: 0.9rem; }
  th, td { padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: #e9ecef; font-weight: 600; position: sticky; top: 0; }
  tr:hover { background: #f1f3f5; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-ok { background: #d1e7dd; color: var(--green); }
  .badge-warn { background: #fff3cd; color: #856404; }
  .badge-danger { background: #f8d7da; color: var(--red); }
  .bar-container { width: 100px; height: 8px; background: #e9ecef; border-radius: 4px; display: inline-block; vertical-align: middle; }
  .bar-fill { height: 100%; border-radius: 4px; }
  .col-section { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
                 padding: 1.2rem; margin-bottom: 1rem; }
  .top-values { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .top-val { background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
  footer { text-align: center; color: #6c757d; font-size: 0.8rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); }
</style>
</head>
<body>
<div class="container">
  <h1>DataWeave Profile Report</h1>
  <p class="subtitle">Automated data quality and profiling report</p>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="value">{{ profile.row_count | number_format }}</div>
      <div class="label">Rows</div>
    </div>
    <div class="summary-card">
      <div class="value">{{ profile.column_count }}</div>
      <div class="label">Columns</div>
    </div>
    <div class="summary-card">
      <div class="value">{{ profile.duplicate_row_count | number_format }}</div>
      <div class="label">Duplicate Rows</div>
    </div>
    <div class="summary-card">
      <div class="value">{{ memory_display }}</div>
      <div class="label">Memory Usage</div>
    </div>
  </div>

  <h2>Column Overview</h2>
  <div style="overflow-x: auto;">
  <table>
    <thead>
      <tr>
        <th>Column</th>
        <th>Type</th>
        <th>Inferred</th>
        <th>Non-Null</th>
        <th>Null %</th>
        <th>Unique</th>
        <th>Outliers</th>
      </tr>
    </thead>
    <tbody>
    {% for col in profile.columns %}
      <tr>
        <td><strong>{{ col.name }}</strong></td>
        <td><code>{{ col.dtype }}</code></td>
        <td>{{ col.inferred_type }}</td>
        <td>{{ col.count | number_format }}</td>
        <td>
          <div class="bar-container">
            <div class="bar-fill" style="width: {{ col.null_pct }}%; background: {% if col.null_pct > 20 %}var(--red){% elif col.null_pct > 5 %}var(--orange){% else %}var(--green){% endif %};"></div>
          </div>
          {{ "%.1f" | format(col.null_pct) }}%
        </td>
        <td>{{ col.unique_count | number_format }}</td>
        <td>
          {% if col.outlier_count > 0 %}
            <span class="badge badge-warn">{{ col.outlier_count }}</span>
          {% else %}
            <span class="badge badge-ok">0</span>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  </div>

  <h2>Column Details</h2>
  {% for col in profile.columns %}
  <div class="col-section">
    <h3>{{ col.name }} <code style="font-size:0.8rem; color:#6c757d;">{{ col.dtype }} / {{ col.inferred_type }}</code></h3>
    <table style="max-width: 500px;">
      {% if col.mean is not none %}
      <tr><td>Mean</td><td>{{ "%.4f" | format(col.mean) }}</td></tr>
      <tr><td>Std Dev</td><td>{{ "%.4f" | format(col.std) }}</td></tr>
      <tr><td>Min</td><td>{{ col.min_val }}</td></tr>
      <tr><td>25th %ile</td><td>{{ col.q25 }}</td></tr>
      <tr><td>Median</td><td>{{ col.median }}</td></tr>
      <tr><td>75th %ile</td><td>{{ col.q75 }}</td></tr>
      <tr><td>Max</td><td>{{ col.max_val }}</td></tr>
      {% endif %}
      {% if col.min_length is not none %}
      <tr><td>Min Length</td><td>{{ col.min_length }}</td></tr>
      <tr><td>Max Length</td><td>{{ col.max_length }}</td></tr>
      <tr><td>Avg Length</td><td>{{ "%.1f" | format(col.avg_length) }}</td></tr>
      {% endif %}
    </table>
    {% if col.top_values %}
    <p style="margin-top: 0.5rem; font-size: 0.85rem; font-weight: 600;">Top Values:</p>
    <div class="top-values">
      {% for val, cnt in col.top_values %}
      <span class="top-val">{{ val }} ({{ cnt }})</span>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endfor %}

  <footer>
    Generated by DataWeave v{{ version }} &mdash; github.com/maharshisoni/dataweave
  </footer>
</div>
</body>
</html>
"""


def _format_bytes(n: int) -> str:
    """Format byte count to a human-readable string.

    Args:
        n: Number of bytes.

    Returns:
        Formatted string (e.g. '1.5 MB').
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _number_format(value: int | float) -> str:
    """Format a number with comma separators.

    Args:
        value: Numeric value.

    Returns:
        Comma-formatted string.
    """
    return f"{int(value):,}"


def generate_report(profile: DataProfile, output_path: str | Path) -> Path:
    """Generate an HTML profiling report.

    Args:
        profile: The computed DataProfile for the dataset.
        output_path: Where to write the HTML file.

    Returns:
        Path to the generated report.
    """
    from dataweave.__version__ import __version__

    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["number_format"] = _number_format
    template = env.from_string(REPORT_TEMPLATE)

    html = template.render(
        profile=profile,
        version=__version__,
        memory_display=_format_bytes(profile.memory_usage_bytes),
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    return output_path
