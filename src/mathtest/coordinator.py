"""Coordinator module orchestrating plugin execution for Mathtest.

Phase 3 of the MVP introduces the registry and coordinator layers described in
SDD section 3.2.2. The coordinator mediates between plugin discovery, parameter
merging, and JSON reproduction so future interfaces (e.g., CLI, API) can rely on
a consistent orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
import random
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .interface import MathProblemPlugin, Problem
from .registry import PluginRegistry, PluginRegistryError


class CoordinatorError(RuntimeError):
    """Raised when the coordinator cannot fulfill a generation request."""


class ParameterSet(BaseModel):
    """Container for common and per-plugin configuration values.

    Attributes:
        common: Parameters applied to every plugin instance.
        plugins: Dictionary of per-plugin overrides keyed by plugin name.
    """

    model_config = ConfigDict(extra="forbid")

    common: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters applied to all plugins before per-plugin overrides.",
    )
    plugins: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping of plugin names to configuration overrides.",
    )


class PluginRequest(BaseModel):
    """Describe how many random problems to generate for a plugin.

    Attributes:
        name: Plugin identifier such as ``"addition"``.
        quantity: Number of problems to generate with the configured plugin.
        overrides: CLI-level overrides applied after defaults and configuration
            files are merged.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Plugin identifier registered in the registry.")
    quantity: int = Field(
        default=0,
        ge=0,
        description="Number of random problems generated for the plugin.",
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Final override mapping supplied alongside CLI flags.",
    )


class SerializedProblem(BaseModel):
    """JSON-friendly representation of a generated problem.

    Attributes:
        problem_type: Plugin identifier used to recreate the problem.
        data: Validated payload returned by the plugin's :class:`Problem`.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    problem_type: str = Field(
        ..., alias="type", description="Plugin identifier used for reproduction."
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized problem payload excluding SVG markup.",
    )

    @property
    def plugin_name(self) -> str:
        """Return the plugin identifier associated with the serialized entry."""

        return self.problem_type

    @classmethod
    def from_problem(cls, plugin_name: str, problem: Problem) -> "SerializedProblem":
        """Create a serialized representation from a plugin :class:`Problem`.

        Args:
            plugin_name: Identifier corresponding to the problem's plugin.
            problem: Generated problem instance.

        Returns:
            Serialized payload ready to be dumped as JSON.
        """

        if "problem_type" not in cls.model_fields:
            msg = "SerializedProblem must define a 'problem_type' field"
            raise ValueError(msg)

        payload = {"problem_type": plugin_name, "data": dict(problem.data)}
        return cls.model_validate(payload)


class GenerationRequest(BaseModel):
    """High-level instructions for building a worksheet."""

    model_config = ConfigDict(extra="forbid")

    plugin_requests: list[PluginRequest] = Field(
        default_factory=list,
        description="Random generation plan grouped by plugin.",
    )
    yaml_parameters: ParameterSet = Field(
        default_factory=ParameterSet,
        description="Parameters sourced from optional YAML configuration files.",
    )
    cli_parameters: ParameterSet = Field(
        default_factory=ParameterSet,
        description="Parameters supplied through CLI flags (after YAML).",
    )
    json_input: list[SerializedProblem] | None = Field(
        default=None,
        description="Serialized problems used for deterministic reproduction.",
    )


@dataclass(frozen=True)
class GenerationResult:
    """Bundle of generated problems and their serialized representation.

    Attributes:
        problems: Ordered list of generated :class:`Problem` instances.
        serialized: JSON-ready descriptions aligned with ``problems``.
    """

    problems: list[Problem]
    serialized: list[SerializedProblem]

    def json_ready(self) -> list[dict[str, Any]]:
        """Return a JSON-serializable structure for ``serialized`` entries."""

        return [item.model_dump(by_alias=True) for item in self.serialized]


class Coordinator:
    """Mediator responsible for loading plugins and generating problems."""

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        """Initialize the coordinator with a plugin registry.

        Args:
            registry: Optional pre-configured registry. When omitted a new
                :class:`PluginRegistry` instance is created using default entry
                points.
        """

        self._registry = registry or PluginRegistry()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate problems according to ``request``.

        JSON input takes precedence over random generation requests, matching the
        behavior outlined in MVP Phase 3.

        Args:
            request: Fully validated generation instructions.

        Returns:
            Generated problems alongside their serialized payloads.
        """

        if request.json_input is not None:
            return self._generate_from_json(request.json_input)
        return self._generate_from_plugins(request)

    def _generate_from_json(self, entries: list[SerializedProblem]) -> GenerationResult:
        """Recreate problems from serialized JSON input."""

        problems: list[Problem] = []
        serialized: list[SerializedProblem] = []
        for entry in entries:
            try:
                plugin_cls = self._registry.get_class(entry.plugin_name)
            except PluginRegistryError as exc:  # pragma: no cover - defensive rewrap
                msg = f"Unknown plugin '{entry.plugin_name}' in JSON input"
                raise CoordinatorError(msg) from exc

            try:
                problem = plugin_cls.generate_from_data(entry.data)
            except Exception as exc:  # pragma: no cover - plugin-level validation
                msg = f"Plugin '{entry.plugin_name}' failed to recreate a problem"
                raise CoordinatorError(msg) from exc

            problems.append(problem)
            serialized.append(
                SerializedProblem.from_problem(entry.plugin_name, problem)
            )
        return GenerationResult(problems=problems, serialized=serialized)

    def _generate_from_plugins(self, request: GenerationRequest) -> GenerationResult:
        """Generate problems by invoking plugin instances."""

        problems: list[Problem] = []
        serialized: list[SerializedProblem] = []
        plugin_instances: dict[str, MathProblemPlugin] = {}
        generation_plan: list[str] = []
        shuffle_components: list[str] = []
        deterministic_shuffle = True

        for plugin_request in request.plugin_requests:
            if plugin_request.quantity <= 0:
                continue

            params = self._build_parameters(
                plugin_request.name, request, plugin_request.overrides
            )
            try:
                plugin = self._registry.create(plugin_request.name, params)
            except PluginRegistryError as exc:  # pragma: no cover - rewrap
                msg = f"Failed to instantiate plugin '{plugin_request.name}'"
                raise CoordinatorError(msg) from exc

            plugin_instances[plugin_request.name] = plugin
            generation_plan.extend([plugin_request.name] * plugin_request.quantity)
            seed_value = self._extract_random_seed(params)
            if seed_value is None:
                deterministic_shuffle = False
            else:
                shuffle_components.append(
                    f"{plugin_request.name}:{seed_value}"
                )

        if not generation_plan:
            return GenerationResult(problems=problems, serialized=serialized)

        if deterministic_shuffle and shuffle_components:
            shuffle_seed = self._derive_shuffle_seed(
                shuffle_components, generation_plan.copy()
            )
            random.Random(shuffle_seed).shuffle(generation_plan)
        else:
            random.shuffle(generation_plan)

        for plugin_name in generation_plan:
            plugin = plugin_instances[plugin_name]
            try:
                problem = plugin.generate_problem()
            except Exception as exc:  # pragma: no cover - plugin runtime error
                msg = f"Plugin '{plugin_name}' failed during generation"
                raise CoordinatorError(msg) from exc

            problems.append(problem)
            serialized.append(SerializedProblem.from_problem(plugin_name, problem))
        return GenerationResult(problems=problems, serialized=serialized)

    def _build_parameters(
        self,
        plugin_name: str,
        request: GenerationRequest,
        overrides: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Merge defaults, YAML, CLI, and plugin overrides for ``plugin_name``."""

        try:
            plugin_cls = self._registry.get_class(plugin_name)
        except PluginRegistryError as exc:  # pragma: no cover - rewrap
            msg = f"Unknown plugin '{plugin_name}' in generation plan"
            raise CoordinatorError(msg) from exc

        try:
            definitions = plugin_cls.get_parameters()
        except Exception as exc:  # pragma: no cover - plugin error
            msg = f"Failed to obtain parameter definitions for '{plugin_name}'"
            raise CoordinatorError(msg) from exc

        merged: dict[str, Any] = {
            definition.name: definition.default for definition in definitions
        }
        self._apply_parameter_set(merged, request.yaml_parameters, plugin_name)
        self._apply_parameter_set(merged, request.cli_parameters, plugin_name)
        if overrides:
            merged.update(overrides)
        return merged

    @staticmethod
    def _apply_parameter_set(
        target: dict[str, Any], parameter_set: ParameterSet, plugin_name: str
    ) -> None:
        """Apply values from ``parameter_set`` to ``target`` in-place."""

        if parameter_set.common:
            target.update(parameter_set.common)
        plugin_specific = parameter_set.plugins.get(plugin_name)
        if plugin_specific:
            target.update(plugin_specific)

    @staticmethod
    def _extract_random_seed(params: Mapping[str, Any]) -> int | None:
        """Return a normalized random seed from ``params`` when present."""

        for key in ("random_seed", "random-seed"):
            value = params.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _derive_shuffle_seed(
        components: list[str], plan: list[str]
    ) -> int:
        """Create a deterministic shuffle seed from plugin seeds and plan."""

        payload = {"components": components, "plan": plan}
        material = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(material.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")
