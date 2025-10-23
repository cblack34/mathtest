"""Plugin registry for Mathtest."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Iterator

from .interface import MathProblemPlugin


class PluginRegistry(MutableMapping[str, MathProblemPlugin]):
    """Basic registry implementation backed by a dictionary."""

    def __init__(self) -> None:
        self._registry: dict[str, MathProblemPlugin] = {}

    def __getitem__(self, key: str) -> MathProblemPlugin:
        return self._registry[key]

    def __setitem__(self, key: str, value: MathProblemPlugin) -> None:
        self._registry[key] = value

    def __delitem__(self, key: str) -> None:
        del self._registry[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._registry)

    def __len__(self) -> int:
        return len(self._registry)
