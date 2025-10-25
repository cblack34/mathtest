"""Smoke tests for the subtraction plugin."""

from mathtest.plugins.subtraction import SubtractionPlugin


def test_subtraction_plugin_generates_expected_problem(
    assert_vertical_arithmetic_problem,
) -> None:
    """Subtraction plugin should respect configuration bounds and answers."""

    plugin = SubtractionPlugin({"min-operand": 4, "max-operand": 4})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 0
    assert_vertical_arithmetic_problem(problem.svg)

    recreated = SubtractionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
