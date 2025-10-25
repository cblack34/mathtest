"""Shared fixtures for plugin smoke tests."""

from __future__ import annotations

from collections.abc import Callable
import xml.etree.ElementTree as ET

import pytest

from mathtest.plugins.addition import (
    _VERTICAL_FONT_SIZE,
    _VERTICAL_HEIGHT_MULTIPLIERS,
)

EXPECTED_VERTICAL_PROBLEM_HEIGHT = _VERTICAL_FONT_SIZE * sum(
    _VERTICAL_HEIGHT_MULTIPLIERS
)


@pytest.fixture
def assert_vertical_arithmetic_problem() -> Callable[[str], None]:
    """Assert that a vertical arithmetic SVG matches shared layout expectations."""

    def _assert(svg: str) -> None:
        assert "<svg" in svg
        assert 'font-size="34px"' in svg

        root = ET.fromstring(svg)
        height_attr = root.attrib["height"]
        assert height_attr.endswith("px")
        assert float(height_attr[:-2]) == pytest.approx(
            EXPECTED_VERTICAL_PROBLEM_HEIGHT, abs=0.1
        )

    return _assert
