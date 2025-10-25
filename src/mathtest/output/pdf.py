"""PDF output generator for MVP Phase 4.

This module implements the Phase 4 requirement outlined in ``documents/MVP.md``
by providing a simple PDF renderer that consumes
:class:`~mathtest.interface.Problem` objects. The implementation focuses on the
addition and subtraction plugins shipped in the MVP while keeping the code
extensible for future problem types.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from reportlab.graphics import renderPDF  # type: ignore[import-untyped]
from reportlab.graphics.shapes import Drawing  # type: ignore[import-untyped]
from svglib.svglib import svg2rlg  # type: ignore[import-untyped]

from ..interface import OutputGenerator, Problem

MIN_HEADER_LABEL_FONT_SIZE = 10.0
HEADER_LABEL_PADDING_FACTOR = 0.5
HEADER_UNDERLINE_OFFSET_FACTOR = 0.3
NAME_FIELD_WIDTH_RATIO = 0.5
DATE_FIELD_WIDTH_RATIO = 0.35
HEADER_SPACING_MULTIPLIER = 1.6
FLOAT_TOLERANCE = 1e-9


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return ``params`` with CLI-friendly keys normalized to snake_case."""

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


@dataclass
class _PreparedProblem:
    """Pre-parsed SVG metadata used during layout planning."""

    problem: Problem
    drawing: Drawing
    scale: float
    scaled_height: float
    scaled_width: float


@dataclass
class _Placement:
    """Drawing metadata for a problem positioned within a row."""

    prepared: _PreparedProblem
    column_index: int
    x_offset: float
    top: float


@dataclass
class _RowLayout:
    """Problems that share a common top coordinate on a page."""

    top: float
    height: float
    placements: list[_Placement]


@dataclass
class _PageLayout:
    """Collection of rows scheduled to render on the same page."""

    rows: list[_RowLayout]


class PdfOutputParams(BaseModel):
    """Validated configuration passed to :class:`PdfOutputGenerator`."""

    model_config = ConfigDict(extra="forbid")

    path: Path = Field(..., description="Destination PDF file path.")
    title: str = Field(
        default="Math Test",
        description="Optional document title rendered on the first page.",
    )
    margin_inches: float = Field(
        default=0.75,
        gt=0,
        description="Page margin applied to all sides in inches.",
    )
    problem_spacing_inches: float = Field(
        default=0.35,
        ge=0,
        description="Vertical spacing between problems in inches.",
    )
    answers_on_new_page: bool = Field(
        default=True,
        description="Whether the answer key should start on a new page.",
    )
    include_answers: bool = Field(
        default=False,
        description=(
            "Toggle rendering of the answer key section. Defaults to False so the "
            "CLI must opt in via the --answer-key flag."
        ),
    )
    answer_title: str = Field(
        default="Answer Key",
        description="Heading rendered before the answer list.",
    )
    body_font: str = Field(
        default="Helvetica",
        description="Base font used for ancillary text such as titles and answers.",
    )
    include_student_header: bool = Field(
        default=True,
        description=(
            "Whether the worksheet should include student metadata fields such as "
            "name and date beneath the main title."
        ),
    )
    title_font_size: int = Field(
        default=20,
        ge=8,
        description="Font size used for the main title.",
    )
    answer_font_size: int = Field(
        default=12,
        ge=6,
        description="Font size used for the answer key entries.",
    )
    columns: int = Field(
        default=4,
        ge=1,
        description="Number of problem columns to render per page.",
    )
    column_spacing_inches: float = Field(
        default=0.25,
        ge=0,
        description="Horizontal spacing between columns in inches.",
    )

    @property
    def margin(self) -> float:
        """Return the page margin converted to points."""

        return self.margin_inches * inch

    @property
    def problem_spacing(self) -> float:
        """Return the spacing between problems converted to points."""

        return self.problem_spacing_inches * inch

    @property
    def column_spacing(self) -> float:
        """Return the spacing between columns converted to points."""

        return self.column_spacing_inches * inch


class PdfOutputGenerator(OutputGenerator):
    """Render problems into a PDF document using ReportLab (MVP Phase 4)."""

    def generate(self, problems: Sequence[Problem], params: Mapping[str, Any]) -> None:
        """Generate a PDF worksheet from ``problems``.

        Args:
            problems: Ordered problems generated by the coordinator.
            params: Configuration dictionary containing at least ``path``.

        Raises:
            ValueError: If ``params`` fails validation or the SVG markup cannot be
                interpreted.
        """

        try:
            config = PdfOutputParams.model_validate(_normalize_param_keys(params))
        except ValidationError as exc:  # pragma: no cover - defensive branch
            raise ValueError("Invalid PDF output parameters") from exc

        if not problems:
            msg = "At least one problem is required to build a worksheet"
            raise ValueError(msg)

        config.path.parent.mkdir(parents=True, exist_ok=True)
        canvas = Canvas(str(config.path), pagesize=letter)
        canvas.setPageCompression(0)
        width, height = letter
        content_width = width - (2 * config.margin)
        if content_width <= 0:
            msg = "Configured margins leave no horizontal space for content"
            raise ValueError(msg)

        total_spacing = config.column_spacing * (config.columns - 1)
        available_width = content_width - total_spacing
        if available_width <= 0:
            msg = "Configured column spacing leaves no room for problem columns"
            raise ValueError(msg)

        column_width = available_width / config.columns
        column_offsets = [
            config.margin + index * (column_width + config.column_spacing)
            for index in range(config.columns)
        ]
        page_initial_top = self._page_initial_row_top(config, height)

        answers: list[str] = []
        prepared_problems: list[_PreparedProblem] = []
        for problem in problems:
            drawing = svg2rlg(io.StringIO(problem.svg))
            if drawing.width is None or drawing.height is None:
                msg = "Problem SVG must provide explicit width and height"
                raise ValueError(msg)
            if drawing.width <= 0 or drawing.height <= 0:
                msg = "Problem SVG dimensions must be positive"
                raise ValueError(msg)

            scale = column_width / float(drawing.width)
            scaled_height = float(drawing.height) * scale
            prepared_problems.append(
                _PreparedProblem(
                    problem=problem,
                    drawing=drawing,
                    scale=scale,
                    scaled_height=scaled_height,
                    scaled_width=drawing.width * scale,
                )
            )

            answer = problem.data.get("answer")
            if answer is None:
                msg = "Problem data missing 'answer' field required for the answer key"
                raise ValueError(msg)
            answers.append(str(answer))

        pages: list[_PageLayout] = []
        current_page_rows: list[_RowLayout] = []
        current_row_top = page_initial_top
        current_row = _RowLayout(
            top=current_row_top, height=0.0, placements=[]
        )
        current_row_height = 0.0
        current_column = 0

        def advance_row() -> None:
            nonlocal current_row_top, current_row_height, current_row, current_column, current_page_rows
            if current_row.placements:
                row_height = current_row_height
                current_row.height = row_height
                current_page_rows.append(current_row)
                current_row_top -= row_height + config.problem_spacing
            current_row = _RowLayout(
                top=current_row_top, height=0.0, placements=[]
            )
            current_row_height = 0.0
            current_column = 0

        def start_new_page() -> None:
            nonlocal current_row_top, current_row_height, current_row, current_column, current_page_rows, pages
            if current_row.placements:
                current_row.height = current_row_height
                current_page_rows.append(current_row)
            if current_page_rows:
                pages.append(_PageLayout(rows=current_page_rows))
            current_page_rows = []
            current_row_top = page_initial_top
            current_row = _RowLayout(
                top=current_row_top, height=0.0, placements=[]
            )
            current_row_height = 0.0
            current_column = 0

        for prepared in prepared_problems:
            scaled_height = prepared.scaled_height

            if current_column >= config.columns:
                advance_row()

            if current_row_top - scaled_height < config.margin:
                if current_row_height > 0 and current_column > 0:
                    advance_row()

            if current_row_top - scaled_height < config.margin:
                start_new_page()
                if current_row_top - scaled_height < config.margin:
                    msg = "Problem geometry exceeds available page height"
                    raise ValueError(msg)

            remaining_width = column_width - prepared.scaled_width
            if abs(remaining_width) <= FLOAT_TOLERANCE:
                remaining_width = 0.0

            x_offset = column_offsets[current_column] + max(0.0, remaining_width)
            placement = _Placement(
                prepared=prepared,
                column_index=current_column,
                x_offset=x_offset,
                top=current_row_top,
            )
            current_row.placements.append(placement)
            current_row_height = max(current_row_height, scaled_height)
            current_row.height = current_row_height
            current_column += 1

        if current_row.placements:
            current_row.height = current_row_height
            current_page_rows.append(current_row)
        if current_page_rows:
            pages.append(_PageLayout(rows=current_page_rows))

        for page in pages:
            rows = page.rows
            if not rows:
                continue
            last_row = rows[-1]
            last_bottom = last_row.top - last_row.height
            extra_space = last_bottom - config.margin
            if extra_space > FLOAT_TOLERANCE:
                if len(rows) == 1:
                    shift = extra_space
                    row = rows[0]
                    row.top -= shift
                    for placement in row.placements:
                        placement.top -= shift
                else:
                    gap_increment = extra_space / (len(rows) - 1)
                    cumulative_shift = 0.0
                    for row in rows[1:]:
                        cumulative_shift += gap_increment
                        row.top -= cumulative_shift
                        for placement in row.placements:
                            placement.top -= cumulative_shift

        for page_index, page in enumerate(pages):
            if page_index > 0:
                canvas.showPage()
            current_header_top = height - config.margin
            if config.title:
                current_header_top = self._draw_title(
                    canvas, config, width, current_header_top
                )
            for row in page.rows:
                for placement in row.placements:
                    drawing = placement.prepared.drawing
                    scale = placement.prepared.scale
                    scaled_height = placement.prepared.scaled_height
                    x_offset = placement.x_offset
                    y_offset = placement.top - scaled_height

                    canvas.saveState()
                    canvas.translate(x_offset, y_offset)
                    canvas.scale(scale, scale)
                    renderPDF.draw(drawing, canvas, 0, 0)
                    canvas.restoreState()

        if pages and pages[-1].rows:
            last_row = pages[-1].rows[-1]
            current_y = last_row.top - last_row.height
        else:
            current_y = page_initial_top

        if config.include_answers and answers:
            self._draw_answers(canvas, config, height, current_y, answers)

        canvas.save()

    def _page_initial_row_top(
        self, config: PdfOutputParams, page_height: float
    ) -> float:
        """Return the top coordinate for the first row on a page."""

        top = page_height - config.margin
        if config.title:
            top -= self._title_block_height(config)
        return top

    def _title_block_height(self, config: PdfOutputParams) -> float:
        """Compute the vertical space consumed by the title and header."""

        height = config.title_font_size * 1.5
        if not config.include_student_header:
            return height
        label_font_size = max(float(config.title_font_size), MIN_HEADER_LABEL_FONT_SIZE)
        return height + (label_font_size * HEADER_SPACING_MULTIPLIER)

    def _draw_title(
        self,
        canvas: Canvas,
        config: PdfOutputParams,
        page_width: float,
        current_y: float,
    ) -> float:
        """Render the document title and return the updated cursor position."""

        canvas.setFont(config.body_font, config.title_font_size)
        canvas.drawCentredString(page_width / 2, current_y, config.title)
        next_y = current_y - (config.title_font_size * 1.5)

        if not config.include_student_header:
            return current_y - self._title_block_height(config)

        label_font_size = max(float(config.title_font_size), MIN_HEADER_LABEL_FONT_SIZE)
        canvas.setFont(config.body_font, label_font_size)
        label_padding = label_font_size * HEADER_LABEL_PADDING_FACTOR
        underline_offset = label_font_size * HEADER_UNDERLINE_OFFSET_FACTOR

        content_width = max(page_width - (2 * config.margin), 0.0)
        name_field_width = content_width * NAME_FIELD_WIDTH_RATIO
        date_field_width = content_width * DATE_FIELD_WIDTH_RATIO
        gap_width = max(content_width - name_field_width - date_field_width, 0.0)

        name_x = config.margin
        date_x = name_x + name_field_width + gap_width
        line_y = next_y - underline_offset

        # ``draw_field`` relies on variables from the outer scope for layout and font
        # configuration: ``next_y``, ``line_y``, ``label_font_size``,
        # ``config.body_font``, and ``canvas``.
        def draw_field(label: str, field_x: float, field_width: float) -> None:
            canvas.drawString(field_x, next_y, label)
            label_width = canvas.stringWidth(label, config.body_font, label_font_size)
            line_start = field_x + label_width + label_padding
            line_end = field_x + field_width
            line_start = min(line_start, line_end)
            if line_end > line_start:
                canvas.line(line_start, line_y, line_end, line_y)

        draw_field("Name:", name_x, name_field_width)
        draw_field("Date:", date_x, date_field_width)

        next_y -= label_font_size * HEADER_SPACING_MULTIPLIER

        return current_y - self._title_block_height(config)

    def _draw_answers(
        self,
        canvas: Canvas,
        config: PdfOutputParams,
        page_height: float,
        current_y: float,
        answers: Iterable[str],
    ) -> None:
        """Render the answer key using the collected ``answers``."""

        if config.answers_on_new_page or current_y < config.margin + (
            config.answer_font_size * 2
        ):
            canvas.showPage()
            current_y = page_height - config.margin

        canvas.setFont(config.body_font, config.title_font_size)
        canvas.drawString(config.margin, current_y, config.answer_title)
        current_y -= config.title_font_size * 1.2

        canvas.setFont(config.body_font, config.answer_font_size)
        line_height = config.answer_font_size * 1.4
        for index, answer in enumerate(answers, start=1):
            if current_y - line_height < config.margin:
                canvas.showPage()
                current_y = page_height - config.margin
                canvas.setFont(config.body_font, config.answer_font_size)
            canvas.drawString(config.margin, current_y, f"{index}. {answer}")
            current_y -= line_height

