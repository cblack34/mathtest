"""Coordinator smoke tests validating Phase 3/5 behaviors."""

from __future__ import annotations

from mathtest.coordinator import (
    Coordinator,
    GenerationRequest,
    ParameterSet,
    PluginRequest,
)
from mathtest.plugins.addition import AdditionPlugin
from mathtest.plugins.subtraction import SubtractionPlugin
from mathtest.plugins.multiplication import MultiplicationPlugin
from mathtest.registry import PluginRegistry


def _registry_with_core_plugins() -> PluginRegistry:
    """Return a registry preloaded with the core MVP plugins."""

    return PluginRegistry(
        plugins={
            "addition": AdditionPlugin,
            "subtraction": SubtractionPlugin,
            "multiplication": MultiplicationPlugin,
        }
    )


def test_coordinator_generates_and_serializes_problems() -> None:
    """Coordinator should generate problems and produce JSON serialization."""

    registry = _registry_with_core_plugins()
    coordinator = Coordinator(registry=registry)
    request = GenerationRequest(
        plugin_requests=[
            PluginRequest(name="addition", quantity=1),
            PluginRequest(name="subtraction", quantity=1),
        ],
        yaml_parameters=ParameterSet(common={"min-operand": 3, "max-operand": 3}),
        cli_parameters=ParameterSet(
            plugins={
                "addition": {"random-seed": 1},
                "subtraction": {"random-seed": 1},
            }
        ),
    )

    result = coordinator.generate(request)

    assert len(result.problems) == 2
    assert all(problem.data["answer"] is not None for problem in result.problems)
    assert all(
        entry.problem_type in {"addition", "subtraction"} for entry in result.serialized
    )

    json_ready = result.json_ready()
    assert len(json_ready) == 2
    assert {item["type"] for item in json_ready} == {"addition", "subtraction"}


def test_coordinator_recreates_from_serialized_input() -> None:
    """Coordinator should recreate problems deterministically from JSON input."""

    registry = _registry_with_core_plugins()
    coordinator = Coordinator(registry=registry)

    initial_request = GenerationRequest(
        plugin_requests=[PluginRequest(name="addition", quantity=1)],
        yaml_parameters=ParameterSet(common={"min-operand": 4, "max-operand": 4}),
        cli_parameters=ParameterSet(common={"random-seed": 5}),
    )
    initial_result = coordinator.generate(initial_request)

    reproduction_request = GenerationRequest(
        plugin_requests=[],
        json_input=initial_result.serialized,
    )
    reproduced = coordinator.generate(reproduction_request)

    assert [problem.data for problem in reproduced.problems] == [
        problem.data for problem in initial_result.problems
    ]
