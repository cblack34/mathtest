"""Smoke tests for the division plugin."""

from mathtest.plugins.division import DivisionPlugin


def test_division_plugin_generates_expected_problem(
    assert_vertical_arithmetic_problem,
) -> None:
    """Division plugin should produce deterministic output when seeded."""

    plugin = DivisionPlugin(
        {
            "min-dividend": 10,
            "max-dividend": 10,
            "min-divisor": 2,
            "max-divisor": 2,
        }
    )
    problem = plugin.generate_problem()

    assert problem.data["quotient"] == 5
    assert problem.data["remainder"] == 0
    assert_vertical_arithmetic_problem(problem.svg)

    recreated = DivisionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
