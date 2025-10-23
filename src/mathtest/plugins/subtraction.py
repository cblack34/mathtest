"""Stub implementation for the subtraction plugin (MVP Phase 1)."""

from __future__ import annotations

from typing import Any, Mapping

from ..interface import ParameterDefinition, Problem


class SubtractionPlugin:
    """Placeholder implementation to reserve the subtraction entry point."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        """Store configuration for future random generation support."""
        self._params = dict(params or {})

    @property
    def name(self) -> str:
        """Return the canonical plugin name."""
        return "subtraction"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Describe configurable parameters (implemented in Phase 2)."""
        raise NotImplementedError("Phase 2 will implement subtraction parameters.")

    def generate_problem(self) -> Problem:
        """Generate a random subtraction problem (implemented in Phase 2)."""
        raise NotImplementedError("Phase 2 will implement random subtraction problems.")

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a subtraction problem deterministically (implemented in Phase 2)."""
        raise NotImplementedError("Phase 2 will implement deterministic subtraction problems.")
