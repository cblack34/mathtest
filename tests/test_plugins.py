"""Smoke tests for the addition and subtraction plugins."""

from __future__ import annotations

from mathtest.plugins.addition import AdditionPlugin
from mathtest.plugins.subtraction import SubtractionPlugin


def test_addition_plugin_generates_expected_problem() -> None:
    """Addition plugin should produce deterministic output when seeded."""

    plugin = AdditionPlugin({"min-operand": 3, "max-operand": 3})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 6
    assert "<svg" in problem.svg

    recreated = AdditionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data


def test_subtraction_plugin_generates_expected_problem() -> None:
    """Subtraction plugin should respect configuration bounds and answers."""

    plugin = SubtractionPlugin({"min-operand": 4, "max-operand": 4})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 0
    assert "<svg" in problem.svg

    recreated = SubtractionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
