"""Subtraction plugin stub for Mathtest."""

from __future__ import annotations

from typing import Any

from ..interface import Problem


class SubtractionPlugin:
    """Placeholder implementation for subtraction problems."""

    name = "subtraction"

    def __init__(self, **_params: Any) -> None:
        self._params = _params

    @classmethod
    def get_parameters(cls) -> list[tuple[str, Any, str]]:
        """Return subtraction-specific CLI parameters."""

        return []

    def generate_problem(self) -> Problem:
        """Generate a random subtraction problem (not yet implemented)."""

        raise NotImplementedError("Subtraction problem generation will be implemented in a later phase.")

    @classmethod
    def generate_from_data(cls, data: dict[str, Any]) -> Problem:
        """Create a subtraction problem from deterministic data (not yet implemented)."""

        raise NotImplementedError("Subtraction problem generation from data will be implemented in a later phase.")
