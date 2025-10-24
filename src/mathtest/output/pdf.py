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

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]

from ..interface import OutputGenerator, Problem


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


@dataclass(frozen=True)
class _SvgGeometry:
    """Geometry metadata extracted from an SVG root element."""

    width: float
    height: float


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
        default=True,
        description="Toggle rendering of the answer key section.",
    )
    answer_title: str = Field(
        default="Answer Key",
        description="Heading rendered before the answer list.",
    )
    body_font: str = Field(
        default="Helvetica",
        description="Base font used for ancillary text such as titles and answers.",
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

    @property
    def margin(self) -> float:
        """Return the page margin converted to points."""

        return self.margin_inches * inch

    @property
    def problem_spacing(self) -> float:
        """Return the spacing between problems converted to points."""

        return self.problem_spacing_inches * inch


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
        current_y = height - config.margin

        if config.title:
            current_y = self._draw_title(canvas, config, width, current_y)

        answers: list[str] = []
        content_width = width - 2 * config.margin
        for problem in problems:
            svg_root = ET.fromstring(problem.svg)
            geometry = _extract_geometry(svg_root)
            scale = min(1.0, content_width / geometry.width)
            required_height = geometry.height * scale

            if current_y - required_height < config.margin:
                canvas.showPage()
                current_y = height - config.margin
                if config.title:
                    current_y = self._draw_title(canvas, config, width, current_y)

            self._draw_problem(canvas, svg_root, geometry, config, current_y, scale)
            current_y -= required_height + config.problem_spacing

            answer = problem.data.get("answer")
            if answer is None:
                msg = "Problem data missing 'answer' field required for the answer key"
                raise ValueError(msg)
            answers.append(str(answer))

        if config.include_answers and answers:
            self._draw_answers(canvas, config, height, current_y, answers)

        canvas.save()

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
        return current_y - (config.title_font_size * 1.5)

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

    def _draw_problem(
        self,
        canvas: Canvas,
        svg_root: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        current_y: float,
        scale: float,
    ) -> None:
        """Render ``svg_root`` using primitive PDF drawing commands."""

        drawing_bottom = current_y - (geometry.height * scale)
        for element in svg_root:
            tag = element.tag.split("}")[-1]
            if tag == "text":
                self._draw_text(
                    canvas, element, geometry, config, drawing_bottom, scale
                )
            elif tag == "line":
                self._draw_line(
                    canvas, element, geometry, config, drawing_bottom, scale
                )
            else:  # pragma: no cover - ignored SVG elements
                continue

    def _draw_text(
        self,
        canvas: Canvas,
        element: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        drawing_bottom: float,
        scale: float,
    ) -> None:
        """Draw an SVG ``<text>`` element using the configured canvas."""

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

        canvas.setFont("Courier", font_size)
        x_position = config.margin + (svg_x * scale)
        y_position = drawing_bottom + ((geometry.height - svg_y) * scale)

        text_width = canvas.stringWidth(text_value, "Courier", font_size)
        if anchor == "middle":
            x_position -= text_width / 2
        elif anchor == "end":
            x_position -= text_width

        canvas.drawString(x_position, y_position, text_value)

    def _draw_line(
        self,
        canvas: Canvas,
        element: ET.Element,
        geometry: _SvgGeometry,
        config: PdfOutputParams,
        drawing_bottom: float,
        scale: float,
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

        canvas.setStrokeColor(colors.HexColor(stroke))
        canvas.setLineWidth(stroke_width)

        canvas.line(
            config.margin + (x1 * scale),
            drawing_bottom + ((geometry.height - y1) * scale),
            config.margin + (x2 * scale),
            drawing_bottom + ((geometry.height - y2) * scale),
        )
