"""Plugin registry utilities for Mathtest.

This module implements the plugin discovery workflow described in MVP Phase 3
and ``SDD §3.2.4``. Plugins are loaded from the ``mathtest.plugins`` entry
point group declared in :mod:`pyproject.toml` so new problem generators can be
added without modifying the coordinator.
"""

from __future__ import annotations

from importlib import metadata
from typing import Any, Mapping

from .interface import MathProblemPlugin


class PluginRegistryError(RuntimeError):
    """Raised when plugin discovery or instantiation fails."""


class PluginRegistry:
    """Discover and cache math problem plugins.

    The registry inspects the ``mathtest.plugins`` entry point group to produce
    a dictionary mapping plugin names (e.g., ``"addition"``) to their
    implementations. Unit tests may inject a custom mapping to bypass entry
    point loading.

    Args:
        entry_point_group: Entry point group to inspect. Defaults to
            ``"mathtest.plugins"`` as defined in :mod:`pyproject.toml`.
        plugins: Optional explicit plugin mapping primarily used by tests to
            supply fake implementations.
    """

    def __init__(
        self,
        *,
        entry_point_group: str = "mathtest.plugins",
        plugins: Mapping[str, type[MathProblemPlugin]] | None = None,
    ) -> None:
        self._entry_point_group = entry_point_group
        self._plugins: dict[str, type[MathProblemPlugin]] = (
            dict(plugins) if plugins is not None else self._load_from_entry_points()
        )

    def names(self) -> tuple[str, ...]:
        """Return the registered plugin names sorted alphabetically."""

        return tuple(sorted(self._plugins))

    def get_class(self, plugin_name: str) -> type[MathProblemPlugin]:
        """Return the plugin class associated with ``plugin_name``.

        Args:
            plugin_name: Name declared in the entry point mapping.

        Returns:
            The plugin class that implements :class:`MathProblemPlugin`.

        Raises:
            PluginRegistryError: If ``plugin_name`` is unknown.
        """

        try:
            return self._plugins[plugin_name]
        except KeyError as exc:
            msg = f"Unknown plugin '{plugin_name}'"
            raise PluginRegistryError(msg) from exc

    def create(self, plugin_name: str, params: Mapping[str, Any] | None = None) -> MathProblemPlugin:
        """Instantiate a plugin with optional configuration.

        Args:
            plugin_name: Name declared in the entry point mapping.
            params: Optional configuration dictionary forwarded to the plugin
                constructor.

        Returns:
            A plugin instance ready for problem generation.

        Raises:
            PluginRegistryError: If the plugin cannot be located or the
                resulting object fails to satisfy :class:`MathProblemPlugin`.
        """

        plugin_cls = self.get_class(plugin_name)
        try:
            instance = plugin_cls(params)
        except Exception as exc:  # pragma: no cover - defensive rewrap
            msg = f"Failed to instantiate plugin '{plugin_name}'"
            raise PluginRegistryError(msg) from exc

        if not isinstance(instance, MathProblemPlugin):
            msg = (
                f"Plugin '{plugin_name}' does not implement the MathProblemPlugin interface"
            )
            raise PluginRegistryError(msg)
        return instance

    def _load_from_entry_points(self) -> dict[str, type[MathProblemPlugin]]:
        """Load plugin classes registered under the configured entry point group."""

        discovered: dict[str, type[MathProblemPlugin]] = {}
        for entry_point in metadata.entry_points(group=self._entry_point_group):
            plugin_name = entry_point.name
            if plugin_name in discovered:
                msg = f"Duplicate plugin name '{plugin_name}' discovered in entry points"
                raise PluginRegistryError(msg)
            plugin_obj = entry_point.load()
            plugin_cls = self._validate_plugin(plugin_name, plugin_obj)
            discovered[plugin_name] = plugin_cls
        return discovered

    def _validate_plugin(
        self, plugin_name: str, plugin_obj: Any
    ) -> type[MathProblemPlugin]:
        """Ensure ``plugin_obj`` behaves like a plugin implementation."""

        if not isinstance(plugin_obj, type):
            msg = f"Entry point '{plugin_name}' does not reference a class"
            raise PluginRegistryError(msg)

        required_attributes = ("get_parameters", "generate_problem", "generate_from_data")
        for attribute in required_attributes:
            if not hasattr(plugin_obj, attribute):
                msg = f"Plugin '{plugin_name}' missing required attribute '{attribute}'"
                raise PluginRegistryError(msg)

        return plugin_obj
