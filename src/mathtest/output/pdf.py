"""PDF output generator for MVP Phase 4.

This module implements the Phase 4 requirement outlined in ``documents/MVP.md``
by providing a simple PDF renderer that consumes
:class:`~mathtest.interface.Problem` objects. The implementation focuses on the
addition and subtraction plugins shipped in the MVP while keeping the code
extensible for future problem types.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET

from fpdf import FPDF
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..interface import OutputGenerator, Problem

MIN_HEADER_LABEL_FONT_SIZE = 10.0
HEADER_LABEL_PADDING_FACTOR = 0.5
HEADER_UNDERLINE_OFFSET_FACTOR = 0.3
NAME_FIELD_WIDTH_RATIO = 0.5
DATE_FIELD_WIDTH_RATIO = 0.35
HEADER_SPACING_MULTIPLIER = 1.6
FLOAT_TOLERANCE = 1e-9
POINTS_PER_INCH = 72.0
LETTER_PAGE_SIZE = (612.0, 792.0)
LETTER_PAGE_WIDTH, LETTER_PAGE_HEIGHT = LETTER_PAGE_SIZE


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return ``params`` with CLI-friendly keys normalized to snake_case."""

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


def _parse_svg_length(value: str | None, fallback: float | None = None) -> float:
    """Parse an SVG length expressed in pixels or plain numbers."""

    if value is None:
        if fallback is None:
            msg = "SVG dimension is missing and no fallback was provided"
            raise ValueError(msg)
        return fallback

    match = re.fullmatch(r"([0-9]*\.?[0-9]+)(px)?", value.strip())
    if match is None:
        msg = f"Unsupported SVG length '{value}'"
        raise ValueError(msg)
    return float(match.group(1))


def _split_viewbox(value: str | None) -> tuple[float, float, float, float]:
    """Convert an SVG viewBox string into its four numeric components."""

    if not value:
        msg = "SVG viewBox attribute is required when width/height are missing"
        raise ValueError(msg)
    parts = re.split(r"[ ,]+", value.strip())
    if len(parts) != 4:
        msg = f"Invalid viewBox declaration '{value}'"
        raise ValueError(msg)
    return tuple(float(part) for part in parts)  # type: ignore[return-value]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Return an RGB tuple parsed from a hex ``value``."""

    match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value.strip())
    if match is None:
        msg = f"Unsupported SVG color '{value}'"
        raise ValueError(msg)

    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return tuple(int(digits[index : index + 2], 16) for index in range(0, 6, 2))


def _to_pdf_y(value: float) -> float:
    """Convert a bottom-origin coordinate to FPDF's top-origin system."""

    return LETTER_PAGE_HEIGHT - value


@dataclass(frozen=True)
class _SvgGeometry:
    """Geometry metadata extracted from an SVG root element."""

    width: float
    height: float


@dataclass
class _PreparedProblem:
    """Pre-parsed SVG metadata used during layout planning."""

    problem: Problem
    svg_root: ET.Element
    geometry: _SvgGeometry
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


def _extract_geometry(svg_root: ET.Element) -> _SvgGeometry:
    """Return the width and height (in SVG units) for ``svg_root``."""

    viewbox = svg_root.attrib.get("viewBox")
    if viewbox:
        _, _, vb_width, vb_height = _split_viewbox(viewbox)
    else:
        vb_width = vb_height = None  # type: ignore[assignment]
    width = _parse_svg_length(svg_root.attrib.get("width"), vb_width)
    height = _parse_svg_length(svg_root.attrib.get("height"), vb_height)
    return _SvgGeometry(width=width, height=height)


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

        return self.margin_inches * POINTS_PER_INCH

    @property
    def problem_spacing(self) -> float:
        """Return the spacing between problems converted to points."""

        return self.problem_spacing_inches * POINTS_PER_INCH

    @property
    def column_spacing(self) -> float:
        """Return the spacing between columns converted to points."""

        return self.column_spacing_inches * POINTS_PER_INCH


class PdfOutputGenerator(OutputGenerator):
    """Render problems into a PDF document using FPDF (MVP Phase 4)."""

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
        pdf = FPDF(unit="pt", format=LETTER_PAGE_SIZE)
        pdf.set_auto_page_break(auto=False)
        pdf.set_compression(False)
        page_width, page_height = LETTER_PAGE_SIZE
        content_width = page_width - (2 * config.margin)
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
        page_initial_top = self._page_initial_row_top(config, page_height)

        answers: list[str] = []
        prepared_problems: list[_PreparedProblem] = []
        for problem in problems:
            svg_root = ET.fromstring(problem.svg)
            geometry = _extract_geometry(svg_root)
            if geometry.width <= 0:
                msg = "Problem SVG width must be positive"
                raise ValueError(msg)

            scale = column_width / geometry.width
            scaled_height = geometry.height * scale
            prepared_problems.append(
                _PreparedProblem(
                    problem=problem,
                    svg_root=svg_root,
                    geometry=geometry,
                    scale=scale,
                    scaled_height=scaled_height,
                    scaled_width=column_width,
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

        for page in pages:
            pdf.add_page()
            current_header_top = page_height - config.margin
            if config.title:
                current_header_top = self._draw_title(
                    pdf, config, page_width, current_header_top
                )
            for row in page.rows:
                for placement in row.placements:
                    self._draw_problem(
                        pdf,
                        placement.prepared.svg_root,
                        placement.prepared.geometry,
                        config,
                        placement.top,
                        placement.prepared.scale,
                        placement.x_offset,
                    )

        if pages and pages[-1].rows:
            last_row = pages[-1].rows[-1]
            current_y = last_row.top - last_row.height
        else:
            current_y = page_initial_top

        if config.include_answers and answers:
            self._draw_answers(pdf, config, page_height, current_y, answers)

        pdf.output(str(config.path))

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
        pdf: FPDF,
        config: PdfOutputParams,
        page_width: float,
        current_y: float,
    ) -> float:
        """Render the document title and return the updated cursor position."""

        pdf.set_font(config.body_font, size=config.title_font_size)
        title_width = pdf.get_string_width(config.title)
        title_x = max((page_width - title_width) / 2, 0.0)
        pdf.text(title_x, _to_pdf_y(current_y), config.title)
        next_y = current_y - (config.title_font_size * 1.5)

        if not config.include_student_header:
            return current_y - self._title_block_height(config)

        label_font_size = max(float(config.title_font_size), MIN_HEADER_LABEL_FONT_SIZE)
        pdf.set_font(config.body_font, size=label_font_size)
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
        # ``config.body_font``, and ``pdf``.
        def draw_field(label: str, field_x: float, field_width: float) -> None:
            pdf.text(field_x, _to_pdf_y(next_y), label)
            label_width = pdf.get_string_width(label)
            line_start = field_x + label_width + label_padding
            line_end = field_x + field_width
            line_start = min(line_start, line_end)
            if line_end > line_start:
                pdf.set_line_width(1.0)
                pdf.line(
                    line_start,
                    _to_pdf_y(line_y),
                    line_end,
                    _to_pdf_y(line_y),
                )

        draw_field("Name:", name_x, name_field_width)
        draw_field("Date:", date_x, date_field_width)

        next_y -= label_font_size * HEADER_SPACING_MULTIPLIER

        return current_y - self._title_block_height(config)

    def _draw_answers(
        self,
        pdf: FPDF,
        config: PdfOutputParams,
        page_height: float,
        current_y: float,
        answers: Iterable[str],
    ) -> None:
        """Render the answer key using the collected ``answers``."""

        if config.answers_on_new_page or current_y < config.margin + (
            config.answer_font_size * 2
        ):
            pdf.add_page()
            current_y = page_height - config.margin

        pdf.set_font(config.body_font, size=config.title_font_size)
        pdf.text(config.margin, _to_pdf_y(current_y), config.answer_title)
        current_y -= config.title_font_size * 1.2

        pdf.set_font(config.body_font, size=config.answer_font_size)
        line_height = config.answer_font_size * 1.4
        for index, answer in enumerate(answers, start=1):
            if current_y - line_height < config.margin:
                pdf.add_page()
                current_y = page_height - config.margin
                pdf.set_font(config.body_font, size=config.answer_font_size)
            pdf.text(
                config.margin,
                _to_pdf_y(current_y),
                f"{index}. {answer}",
            )
            current_y -= line_height

    def _draw_problem(
        self,
        pdf: FPDF,
        svg_root: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        current_y: float,
        scale: float,
        x_offset: float,
    ) -> None:
        """Render ``svg_root`` using primitive PDF drawing commands."""

        drawing_bottom = current_y - (geometry.height * scale)
        for element in svg_root:
            tag = element.tag.split("}")[-1]
            if tag == "text":
                self._draw_text(
                    pdf, element, geometry, config, drawing_bottom, scale, x_offset
                )
            elif tag == "line":
                self._draw_line(
                    pdf, element, geometry, config, drawing_bottom, scale, x_offset
                )
            else:  # pragma: no cover - ignored SVG elements
                continue

    def _draw_text(
        self,
        pdf: FPDF,
        element: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        drawing_bottom: float,
        scale: float,
        x_offset: float,
    ) -> None:
        """Draw an SVG ``<text>`` element using the configured PDF context."""

        text_value = "".join(element.itertext())
        if not text_value:
            return

        try:
            svg_x = float(element.attrib.get("x", "0"))
            svg_y = float(element.attrib.get("y", "0"))
        except ValueError as exc:
            raise ValueError(
                "SVG text element contains non-numeric coordinates"
            ) from exc

        font_size = _parse_svg_length(element.attrib.get("font-size"), 12.0) * scale
        anchor = element.attrib.get("text-anchor", "start")

        pdf.set_font("Courier", size=font_size)
        x_position = x_offset + (svg_x * scale)
        y_position = drawing_bottom + ((geometry.height - svg_y) * scale)

        text_width = pdf.get_string_width(text_value)
        if anchor == "middle":
            x_position -= text_width / 2
        elif anchor == "end":
            x_position -= text_width

        pdf.text(x_position, _to_pdf_y(y_position), text_value)

    def _draw_line(
        self,
        pdf: FPDF,
        element: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        drawing_bottom: float,
        scale: float,
        x_offset: float,
    ) -> None:
        """Draw an SVG ``<line>`` element with basic styling."""

        try:
            x1 = float(element.attrib.get("x1", "0"))
            y1 = float(element.attrib.get("y1", "0"))
            x2 = float(element.attrib.get("x2", "0"))
            y2 = float(element.attrib.get("y2", "0"))
        except ValueError as exc:
            raise ValueError(
                "SVG line element contains non-numeric coordinates"
            ) from exc

        stroke = element.attrib.get("stroke", "#000000")
        stroke_width = (
            _parse_svg_length(element.attrib.get("stroke-width"), 1.0) * scale
        )

        pdf.set_draw_color(*_hex_to_rgb(stroke))
        pdf.set_line_width(stroke_width)

        pdf.line(
            x_offset + (x1 * scale),
            _to_pdf_y(drawing_bottom + ((geometry.height - y1) * scale)),
            x_offset + (x2 * scale),
            _to_pdf_y(drawing_bottom + ((geometry.height - y2) * scale)),
        )

