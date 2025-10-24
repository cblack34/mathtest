"""Tests for the PDF output implementation introduced in MVP Phase 4."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from reportlab.lib.pagesizes import letter

from mathtest.output import PdfOutputGenerator
from mathtest.plugins.addition import AdditionPlugin


@pytest.fixture()
def sample_problems() -> list:
    """Return a deterministic set of problems for PDF rendering tests."""

    plugin = AdditionPlugin({"random_seed": 123})
    return [plugin.generate_problem() for _ in range(3)]


def test_pdf_output_creates_file_with_answer_key(
    tmp_path: Path, sample_problems: list
) -> None:
    """PDF generator should produce a non-empty file when the key is enabled."""

    output_path = tmp_path / "worksheet.pdf"
    generator = PdfOutputGenerator()

    generator.generate(
        sample_problems, {"path": output_path, "include_answers": True}
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    pdf_bytes = output_path.read_bytes()
    assert b"Answer Key" in pdf_bytes
    assert b"1. " in pdf_bytes  # Basic confirmation that answers are listed


def test_pdf_output_omits_answer_key_when_disabled(
    tmp_path: Path, sample_problems: list
) -> None:
    """Answer key content should be absent unless explicitly requested."""

    output_path = tmp_path / "worksheet.pdf"
    generator = PdfOutputGenerator()

    generator.generate(sample_problems, {"path": output_path})

    assert output_path.exists()
    pdf_bytes = output_path.read_bytes()
    assert b"Answer Key" not in pdf_bytes


def test_pdf_output_requires_path(sample_problems: list) -> None:
    """Missing required parameters should raise a ``ValueError``."""

    generator = PdfOutputGenerator()
    with pytest.raises(ValueError):
        generator.generate(sample_problems, {})


def test_pdf_output_columns_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Problems should render in distinct columns without overlapping bounds."""

    plugin = AdditionPlugin({"random_seed": 987})
    problems = [plugin.generate_problem() for _ in range(8)]

    generator = PdfOutputGenerator()
    output_path = tmp_path / "columns.pdf"

    placements: list[dict[str, float]] = []
    observed_config: list[Any] = []
    original_draw_problem = PdfOutputGenerator._draw_problem

    def capture_draw(
        self: PdfOutputGenerator,
        canvas: Any,
        svg_root: Any,
        geometry: Any,
        config: Any,
        current_y: float,
        scale: float,
        x_offset: float,
    ) -> None:
        if not observed_config:
            observed_config.append(config)
        scaled_height = geometry.height * scale
        placements.append(
            {
                "x": x_offset,
                "top": current_y,
                "bottom": current_y - scaled_height,
                "width": geometry.width * scale,
                "height": scaled_height,
            }
        )
        original_draw_problem(
            self, canvas, svg_root, geometry, config, current_y, scale, x_offset
        )

    monkeypatch.setattr(PdfOutputGenerator, "_draw_problem", capture_draw)

    generator.generate(problems, {"path": output_path})

    assert output_path.exists()
    assert placements
    config = observed_config[0]

    page_width, _ = letter
    column_spacing = config.column_spacing
    content_width = page_width - (2 * config.margin)
    available_width = content_width - column_spacing * (config.columns - 1)
    column_width = available_width / config.columns
    expected_offsets = [
        config.margin + index * (column_width + column_spacing)
        for index in range(config.columns)
    ]

    tolerance = 1e-3
    columns_used: set[int] = set()
    row_tops: list[float] = []
    rows: dict[int, list[int]] = {}
    column_groups: dict[int, list[dict[str, float]]] = {
        index: [] for index in range(config.columns)
    }

    def assign_row(top: float) -> int:
        for idx, existing in enumerate(row_tops):
            if abs(existing - top) < tolerance:
                return idx
        row_tops.append(top)
        return len(row_tops) - 1

    for placement in placements:
        column_index = min(
            range(config.columns),
            key=lambda idx: abs(placement["x"] - expected_offsets[idx]),
        )
        assert abs(placement["x"] - expected_offsets[column_index]) < tolerance
        columns_used.add(column_index)
        column_groups[column_index].append(placement)
        assert placement["width"] <= column_width + tolerance

        row_index = assign_row(placement["top"])
        rows.setdefault(row_index, []).append(column_index)

    assert len(columns_used) == config.columns
    assert rows[0] == list(range(config.columns))

    for column_index, column_placements in column_groups.items():
        if not column_placements:
            continue
        column_placements.sort(key=lambda item: item["top"], reverse=True)
        for first, second in zip(column_placements, column_placements[1:]):
            previous_bottom = first["bottom"]
            gap = previous_bottom - second["top"]
            # ``gap`` is positive when the problems are separated. Negative values
            # indicate overlap because PDF coordinates decrease as we move down the
            # page.
            assert gap >= -tolerance
            assert gap + tolerance >= config.problem_spacing

    for row_columns in rows.values():
        assert len(row_columns) == len(set(row_columns))
