"""Tests for the PDF output implementation introduced in MVP Phase 4."""

from __future__ import annotations

import io
from pathlib import Path


def _build_text_svg(
    width: int,
    height: int,
    text: str,
    *,
    font_size: int = 12,
    x: int = 2,
    y: int | None = None,
) -> str:
    """Create a minimal SVG with a single text element for layout tests."""

    baseline_y = y if y is not None else height - 6
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' "
        f"width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<text x='{x}' y='{baseline_y}' font-size='{font_size}'>{text}</text>"
        "</svg>"
    )

import pytest

from reportlab.lib.pagesizes import letter

from mathtest.interface import Problem
from mathtest.output import PdfOutputGenerator
from mathtest.output.pdf import PdfOutputParams
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
    assert b"Name:" in pdf_bytes
    assert b"Date:" in pdf_bytes


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


def test_pdf_output_can_disable_student_header(
    tmp_path: Path, sample_problems: list
) -> None:
    """Student metadata fields should be optional via configuration."""

    output_path = tmp_path / "worksheet.pdf"
    generator = PdfOutputGenerator()

    generator.generate(
        sample_problems,
        {"path": output_path, "include_student_header": False},
    )

    pdf_bytes = output_path.read_bytes()
    assert b"Name:" not in pdf_bytes
    assert b"Date:" not in pdf_bytes


def test_pdf_output_requires_path(sample_problems: list) -> None:
    """Missing required parameters should raise a ``ValueError``."""

    generator = PdfOutputGenerator()
    with pytest.raises(ValueError):
        generator.generate(sample_problems, {})


def test_pdf_output_uses_svg2rlg_drawings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generator should convert SVG markup to ReportLab drawings."""

    output_path = tmp_path / "worksheet.pdf"
    problem = Problem(svg=_build_text_svg(80, 40, "1 + 1"), data={"answer": 2})
    generator = PdfOutputGenerator()

    class MockDrawing:
        def __init__(self) -> None:
            self.width = 80.0
            self.height = 40.0

    mock_drawing = MockDrawing()
    svg_inputs: list[str] = []
    matrices: list[tuple[float, float, float, float, float, float]] = []

    def fake_svg2rlg(stream: io.StringIO) -> MockDrawing:
        assert isinstance(stream, io.StringIO)
        svg_inputs.append(stream.getvalue())
        return mock_drawing

    def fake_render(drawing: MockDrawing, canvas, x: float, y: float) -> None:
        assert drawing is mock_drawing
        assert x == 0 and y == 0
        matrices.append(canvas._currentMatrix)

    monkeypatch.setattr("mathtest.output.pdf.svg2rlg", fake_svg2rlg)
    monkeypatch.setattr("mathtest.output.pdf.renderPDF.draw", fake_render)

    generator.generate([problem], {"path": output_path})

    assert output_path.exists()
    assert svg_inputs == [problem.svg]
    assert matrices

    matrix = matrices[0]
    scale = matrix[0]
    x_offset = matrix[4]
    y_offset = matrix[5]

    config = PdfOutputParams(path=output_path)
    page_width, page_height = letter
    total_spacing = config.column_spacing * (config.columns - 1)
    content_width = page_width - (2 * config.margin)
    column_width = (content_width - total_spacing) / config.columns
    expected_scale = column_width / mock_drawing.width
    assert scale == pytest.approx(expected_scale, rel=1e-6)
    assert x_offset == pytest.approx(config.margin, rel=1e-6)

    expected_bottom = config.margin
    assert y_offset == pytest.approx(expected_bottom, rel=1e-6)

    top_position = y_offset + (mock_drawing.height * expected_scale)
    assert top_position > expected_bottom


def test_pdf_output_columns_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Problems should render in distinct columns without overlapping bounds."""

    plugin = AdditionPlugin({"random_seed": 987})
    problems = [plugin.generate_problem() for _ in range(8)]
    narrow_problem = Problem(
        svg=_build_text_svg(40, 24, "1 + 1"),
        data={"answer": 2},
    )
    problems.append(narrow_problem)

    generator = PdfOutputGenerator()
    output_path = tmp_path / "columns.pdf"

    class MockDrawing:
        def __init__(self, width: float, height: float) -> None:
            self.width = float(width)
            self.height = float(height)

    draw_specs = [(120.0, 48.0) for _ in range(len(problems) - 1)] + [(40.0, 24.0)]
    drawings: list[MockDrawing] = []
    matrices: list[tuple[float, float, float, float, float, float]] = []

    def fake_svg2rlg(stream: io.StringIO) -> MockDrawing:
        assert isinstance(stream, io.StringIO)
        width, height = draw_specs[len(drawings)]
        drawing = MockDrawing(width, height)
        drawings.append(drawing)
        return drawing

    def fake_render(drawing: MockDrawing, canvas, x: float, y: float) -> None:
        assert x == 0 and y == 0
        matrices.append(canvas._currentMatrix)

    monkeypatch.setattr("mathtest.output.pdf.svg2rlg", fake_svg2rlg)
    monkeypatch.setattr("mathtest.output.pdf.renderPDF.draw", fake_render)

    generator.generate(problems, {"path": output_path})

    assert output_path.exists()
    assert matrices
    assert len(drawings) == len(problems)
    config = PdfOutputParams(path=output_path)

    page_width, _ = letter
    column_spacing = config.column_spacing
    content_width = page_width - (2 * config.margin)
    available_width = content_width - column_spacing * (config.columns - 1)
    column_width = available_width / config.columns
    column_left_offsets = [
        config.margin + index * (column_width + column_spacing)
        for index in range(config.columns)
    ]
    expected_right_edges = [offset + column_width for offset in column_left_offsets]

    tolerance = 1e-3
    columns_used: set[int] = set()
    row_tops: list[float] = []
    rows: dict[int, list[tuple[int, float]]] = {}
    column_groups: dict[int, list[dict[str, float]]] = {
        index: [] for index in range(config.columns)
    }

    placements: list[dict[str, float]] = []
    for index, (matrix, drawing) in enumerate(zip(matrices, drawings)):
        scale_x, _, _, scale_y, tx, ty = matrix
        width = drawing.width * scale_x
        height = drawing.height * scale_y
        placements.append(
            {
                "x": tx,
                "top": ty + height,
                "bottom": ty,
                "width": width,
                "height": height,
                "original_width": drawing.width,
                "problem_index": index,
            }
        )

    def assign_row(top: float) -> int:
        for idx, existing in enumerate(row_tops):
            if abs(existing - top) < tolerance:
                return idx
        row_tops.append(top)
        return len(row_tops) - 1

    for placement in placements:
        right_edge = placement["x"] + placement["width"]
        column_index = min(
            range(config.columns),
            key=lambda idx: abs(right_edge - expected_right_edges[idx]),
        )
        assert abs(right_edge - expected_right_edges[column_index]) < tolerance
        assert placement["x"] + tolerance >= column_left_offsets[column_index]
        columns_used.add(column_index)
        column_groups[column_index].append(placement)
        assert placement["width"] <= column_width + tolerance

        row_index = assign_row(placement["top"])
        rows.setdefault(row_index, []).append((column_index, right_edge))
        placement["column_index"] = column_index

    assert len(columns_used) == config.columns
    assert [column for column, _ in rows[0]] == list(range(config.columns))

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
        column_indices = [column for column, _ in row_columns]
        assert len(column_indices) == len(set(column_indices))
        for column_index, edge in row_columns:
            assert abs(edge - expected_right_edges[column_index]) < tolerance

    highest_top = max(placement["top"] for placement in placements)
    lowest_bottom = min(placement["bottom"] for placement in placements)
    assert abs(lowest_bottom - config.margin) < tolerance
    available_vertical = highest_top - config.margin
    used_vertical = highest_top - lowest_bottom
    assert abs(available_vertical - used_vertical) < tolerance

    narrow_index = len(problems) - 1
    plugin_scales = [
        placement["width"] / placement["original_width"]
        for placement in placements
        if placement["problem_index"] != narrow_index
    ]
    assert plugin_scales, "Expected plugin placements for scale comparison"
    reference_scale = plugin_scales[0]
    for scale in plugin_scales[1:]:
        assert abs(scale - reference_scale) < tolerance

    narrow_placements = [
        placement
        for placement in placements
        if placement["original_width"] < column_width - tolerance
    ]
    assert narrow_placements, "Expected at least one narrow problem for scaling test"
    for placement in narrow_placements:
        assert abs(placement["width"] - column_width) < tolerance
        column_index = placement["column_index"]
        assert (
            abs(
                placement["x"]
                + placement["width"]
                - expected_right_edges[column_index]
            )
            < tolerance
        )
