"""Tests for the :mod:`mathtest.registry` module."""

import pytest

from mathtest import registry
from mathtest.interface import OutputGenerator


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


class _DummyOutput(OutputGenerator):
    """Minimal output plugin for registry tests."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = dict(config or {})

    @classmethod
    def category(cls) -> OutputGenerator.Category:
        return OutputGenerator.Category.STANDARD

    @property
    def name(self) -> str:
        return "dummy-output"

    @classmethod
    def get_parameters(cls):  # type: ignore[override]
        return ()

    def generate(self, problems):  # pragma: no cover - not required for tests
        raise NotImplementedError


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


def test_output_registry_instantiates_plugins() -> None:
    """Output registries should instantiate configured plugin classes."""

    output_registry = registry.OutputPluginRegistry(
        plugins={"dummy-output": _DummyOutput}
    )

    plugin = output_registry.create("dummy-output", {"path": "unused"})

    assert isinstance(plugin, _DummyOutput)
    assert plugin.config["path"] == "unused"


def test_output_registry_rejects_unknown_names() -> None:
    """Accessing an unknown output plugin should raise an error."""

    output_registry = registry.OutputPluginRegistry(plugins={})

    with pytest.raises(registry.OutputPluginRegistryError):
        output_registry.create("missing")
