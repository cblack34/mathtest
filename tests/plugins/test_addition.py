"""Smoke tests for the addition plugin."""

from mathtest.plugins.addition import AdditionPlugin


def test_addition_plugin_generates_expected_problem(
    assert_vertical_arithmetic_problem,
) -> None:
    """Addition plugin should produce deterministic output when seeded."""

    plugin = AdditionPlugin({"min-operand": 3, "max-operand": 3})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 6
    assert_vertical_arithmetic_problem(problem.svg)

    recreated = AdditionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
