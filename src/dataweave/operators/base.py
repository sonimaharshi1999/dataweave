# MIT License
# Copyright (c) 2024 Maharshi Soni

"""Base operator interface and registry for DataWeave."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from dataweave.models import StepConfig


class Operator(ABC):
    """Abstract base class for all pipeline operators."""

    @abstractmethod
    def execute(self, df: pd.DataFrame, step: StepConfig) -> pd.DataFrame:
        """Execute the operator on a DataFrame.

        Args:
            df: Input DataFrame.
            step: Step configuration from the pipeline YAML.

        Returns:
            Transformed DataFrame.
        """
        ...


class OperatorRegistry:
    """Registry mapping operator names to their implementations."""

    _operators: dict[str, type[Operator]] = {}

    @classmethod
    def register(cls, name: str, operator_cls: type[Operator]) -> None:
        """Register an operator class under a given name.

        Args:
            name: The operator name (matches OperatorType values).
            operator_cls: The Operator subclass to register.
        """
        cls._operators[name] = operator_cls

    @classmethod
    def get(cls, name: str) -> Operator:
        """Retrieve an operator instance by name.

        Args:
            name: The operator name.

        Returns:
            An instance of the corresponding Operator.

        Raises:
            KeyError: If no operator is registered under that name.
        """
        if name not in cls._operators:
            available = ", ".join(sorted(cls._operators.keys()))
            raise KeyError(
                f"Unknown operator '{name}'. Available: {available}"
            )
        return cls._operators[name]()

    @classmethod
    def list_operators(cls) -> list[str]:
        """List all registered operator names.

        Returns:
            Sorted list of operator names.
        """
        return sorted(cls._operators.keys())
