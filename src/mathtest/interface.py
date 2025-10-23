"""Core interfaces for Mathtest plugins and output generators."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class Problem(BaseModel):
    """Representation of a single math problem."""

    svg: str
    data: dict[str, Any]


@runtime_checkable
class MathProblemPlugin(Protocol):
    """Protocol describing math problem plugins."""

    name: str

    @classmethod
    def get_parameters(cls) -> list[tuple[str, Any, str]]:
        """Return parameter definitions for CLI/YAML generation."""

    def generate_problem(self) -> Problem:
        """Produce a problem using the plugin's configuration."""

    @classmethod
    def generate_from_data(cls, data: dict[str, Any]) -> Problem:
        """Construct a problem from deterministic input data."""


@runtime_checkable
class OutputGenerator(Protocol):
    """Protocol describing output generators such as PDF writers."""

    def generate(self, problems: list[Problem], params: dict[str, Any]) -> None:
        """Create an artifact from problems using provided parameters."""
