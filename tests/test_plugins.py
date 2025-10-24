"""Smoke tests for the addition and subtraction plugins."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from mathtest.plugins.addition import AdditionPlugin
from mathtest.plugins.subtraction import SubtractionPlugin


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
    assert float(height_attr[:-2]) == pytest.approx(117.3, abs=0.1)

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
    assert float(height_attr[:-2]) == pytest.approx(117.3, abs=0.1)

    recreated = SubtractionPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data
