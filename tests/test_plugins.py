"""Smoke tests for the bundled math problem plugins."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from mathtest.plugins.addition import AdditionPlugin, _VERTICAL_FONT_SIZE, _VERTICAL_HEIGHT_MULTIPLIERS
from mathtest.plugins.clock import ClockPlugin
from mathtest.plugins.subtraction import SubtractionPlugin

# Layout multipliers are imported from the production code to avoid duplication.
EXPECTED_VERTICAL_PROBLEM_HEIGHT = _VERTICAL_FONT_SIZE * sum(
    _VERTICAL_HEIGHT_MULTIPLIERS
)


def test_addition_plugin_generates_expected_problem() -> None:
    """Addition plugin should produce deterministic output when seeded."""

    plugin = AdditionPlugin({"min-operand": 3, "max-operand": 3})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 6
    assert "<svg" in problem.svg
    assert 'font-size="34px"' in problem.svg

    root = ET.fromstring(problem.svg)
    height_attr = root.attrib["height"]
    assert height_attr.endswith("px")
    assert float(height_attr[:-2]) == pytest.approx(
        EXPECTED_VERTICAL_PROBLEM_HEIGHT, abs=0.1
    )

    recreated = AdditionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data


def test_subtraction_plugin_generates_expected_problem() -> None:
    """Subtraction plugin should respect configuration bounds and answers."""

    plugin = SubtractionPlugin({"min-operand": 4, "max-operand": 4})
    problem = plugin.generate_problem()

    assert problem.data["answer"] == 0
    assert "<svg" in problem.svg
    assert 'font-size="34px"' in problem.svg

    root = ET.fromstring(problem.svg)
    height_attr = root.attrib["height"]
    assert height_attr.endswith("px")
    assert float(height_attr[:-2]) == pytest.approx(
        EXPECTED_VERTICAL_PROBLEM_HEIGHT, abs=0.1
    )

    recreated = SubtractionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data


def test_clock_plugin_generates_expected_problem() -> None:
    """Clock plugin should enforce 12-hour defaults and deterministic seeding."""

    plugin = ClockPlugin({"random-seed": 7})
    problem = plugin.generate_problem()

    assert problem.data["hour"] == 6
    assert problem.data["minute"] == 15
    assert problem.data["minute_interval"] == 15
    assert problem.data["accurate_hour"] is False
    assert problem.data["is_24_hour"] is False
    assert problem.data["answer"] == "6:15"
    assert problem.data["hour_hand_angle"] == 180.0
    assert problem.data["minute_hand_angle"] == 90.0
    assert "<svg" in problem.svg

    recreated = ClockPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data


def test_clock_plugin_supports_accurate_hour_and_24_hour_modes() -> None:
    """Clock plugin should adjust the hour hand and support 24-hour dials."""

    accurate = ClockPlugin({
        "random-seed": 4,
        "minute-interval": 30,
        "accurate-hour": True,
    })
    accurate_problem = accurate.generate_problem()

    assert accurate_problem.data["hour"] == 4
    assert accurate_problem.data["minute"] == 30
    assert accurate_problem.data["hour_hand_angle"] == 135.0

    military = ClockPlugin({
        "random-seed": 11,
        "clock-24-hour": True,
        "minute-interval": 60,
    })
    military_problem = military.generate_problem()

    assert military_problem.data["is_24_hour"] is True
    assert military_problem.data["hour"] == 14
    assert military_problem.data["minute"] == 0
    assert military_problem.data["answer"] == "14:00"
