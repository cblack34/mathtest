"""Addition plugin stub for Mathtest."""

from __future__ import annotations

from typing import Any

from ..interface import Problem


class AdditionPlugin:
    """Placeholder implementation for addition problems."""

    name = "addition"

    def __init__(self, **_params: Any) -> None:
        self._params = _params

    @classmethod
    def get_parameters(cls) -> list[tuple[str, Any, str]]:
        """Return addition-specific CLI parameters."""

        return []

    def generate_problem(self) -> Problem:
        """Generate a random addition problem (not yet implemented)."""

        raise NotImplementedError("Addition problem generation will be implemented in a later phase.")

    @classmethod
    def generate_from_data(cls, data: dict[str, Any]) -> Problem:
        """Create an addition problem from deterministic data (not yet implemented)."""

        raise NotImplementedError("Addition problem generation from data will be implemented in a later phase.")
