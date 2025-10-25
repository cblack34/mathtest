"""Smoke tests for the multiplication plugin."""

from mathtest.plugins.multiplication import MultiplicationPlugin


def test_multiplication_plugin_generates_expected_problem(
    assert_vertical_arithmetic_problem,
) -> None:
    """Multiplication plugin should produce deterministic output when seeded."""

    plugin = MultiplicationPlugin({"min-operand": 2, "max-operand": 2})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 4
    assert_vertical_arithmetic_problem(problem.svg)

    recreated = MultiplicationPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
