"""Core coordination logic for Mathtest."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .interface import OutputGenerator, Problem


class TestCoordinator:
    """Orchestrates plugin loading and output generation."""

    def __init__(self, output: OutputGenerator) -> None:
        """Initialize the coordinator with an output generator."""

        self._output = output

    def generate_test(self, problems: Iterable[Problem], params: dict[str, Any]) -> None:
        """Send the provided problems to the configured output generator."""

        self._output.generate(list(problems), params)
