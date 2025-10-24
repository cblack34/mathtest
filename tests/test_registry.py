"""Tests for the :mod:`mathtest.registry` module."""

from __future__ import annotations

import pytest

from mathtest import registry


class _DummyPlugin:
    """Minimal plugin implementation for registry validation tests."""

    name = "dummy"

    def __init__(self, params: dict[str, object] | None = None) -> None:
        self.params = params or {}

    @classmethod
    def get_parameters(cls) -> list:
        return []

    def generate_problem(self):  # pragma: no cover - not required for tests
        raise NotImplementedError

    @classmethod
    def generate_from_data(cls, data):  # pragma: no cover - not required for tests
        raise NotImplementedError


class _EntryPoint:
    """Lightweight stand-in for :class:`importlib.metadata.EntryPoint`."""

    def __init__(self, name: str, plugin: type[_DummyPlugin]) -> None:
        self.name = name
        self._plugin = plugin

    def load(self) -> type[_DummyPlugin]:
        return self._plugin


def test_registry_rejects_duplicate_entry_point_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry initialization should fail when duplicate names are discovered."""

    def fake_entry_points(*, group: str):
        assert group == "mathtest.plugins"
        return (
            _EntryPoint("duplicate", _DummyPlugin),
            _EntryPoint("duplicate", _DummyPlugin),
        )

    monkeypatch.setattr(registry.metadata, "entry_points", fake_entry_points)

    with pytest.raises(registry.PluginRegistryError) as excinfo:
        registry.PluginRegistry()

    assert "Duplicate plugin name" in str(excinfo.value)
