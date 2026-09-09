# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Shared test fixtures for DataWeave tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "email": [
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
            "dave@example.com",
            "eve@example.com",
        ],
        "amount": [100.0, 200.0, 150.0, 300.0, 250.0],
        "quantity": [2, 1, 3, 1, 4],
        "category": ["A", "B", "A", "C", "B"],
        "status": ["active", "active", "inactive", "active", "inactive"],
    })


@pytest.fixture
def sample_csv(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    """Write sample DataFrame to a CSV file and return the path."""
    csv_path = tmp_path / "test_data.csv"
    sample_df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_df_with_nulls() -> pd.DataFrame:
    """Create a DataFrame with some null values."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", None, "Carol", "Dave", None],
        "score": [85.0, 92.0, None, 78.0, 95.0],
        "grade": ["A", "A", "B", None, "A"],
    })


@pytest.fixture
def samples_dir() -> Path:
    """Return the path to the samples directory."""
    return Path(__file__).parent.parent / "samples"
