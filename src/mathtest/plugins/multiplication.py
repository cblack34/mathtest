"""Multiplication plugin implementation for MVP Phase 2 (PRD §3.1, MVP Phase 2)."""

from __future__ import annotations

import random
from typing import Any, Mapping

import svgwrite  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..interface import ParameterDefinition, Problem


_VERTICAL_FONT_SIZE = 34
_VERTICAL_HEIGHT_MULTIPLIERS = [0.4, 1.0, 1.25, 0.35, 1.125]


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map external configuration keys to Pydantic field names.

    Args:
        params: Raw configuration dictionary that may contain hyphenated keys
            from CLI flags or YAML settings.

    Returns:
        A dictionary with hyphenated keys converted to snake_case so they align
        with the ``_MultiplicationParams`` model definition.
    """

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


def _format_operand(value: int) -> str:
    """Format an operand for vertical rendering.

    Args:
        value: The integer operand to render.

    Returns:
        The operand rendered as a string with negatives wrapped in parentheses
        to match grade-school formatting expectations.
    """

    return f"({value})" if value < 0 else str(value)


def _render_vertical_problem(
    top: int,
    bottom: int,
    operator: str,
    minimum_digit_chars: int | None = None,
) -> str:
    """Create a vertically stacked arithmetic SVG illustration.

    Args:
        top: The top operand shown in the vertical layout.
        bottom: The bottom operand shown beneath the operator.
        operator: The arithmetic operator symbol to display between operands.
        minimum_digit_chars: Optional lower bound for the operand character
            count when measuring layout width. This keeps rendered problems
            consistent across varying operand lengths so downstream scaling
            does not change font sizes.

    Returns:
        An SVG string matching the dimensions and typography outlined in
        ``SDD §3.2.3`` so that multiplication and other plugins remain visually
        consistent.
    """

    char_width = _VERTICAL_FONT_SIZE * 0.6
    margin = _VERTICAL_FONT_SIZE * 0.45
    top_padding = _VERTICAL_FONT_SIZE * 0.4
    baseline_gap = _VERTICAL_FONT_SIZE * 1.25
    underline_offset = _VERTICAL_FONT_SIZE * 0.35
    # Provide extra writing room beneath the underline for student answers.
    bottom_padding = _VERTICAL_FONT_SIZE * 1.125

    top_y = top_padding + _VERTICAL_FONT_SIZE
    bottom_y = top_y + baseline_gap
    line_y = bottom_y + underline_offset
    height = line_y + bottom_padding

    top_text = _format_operand(top)
    bottom_operand = _format_operand(bottom)
    operator_prefix_chars = len(f"{operator} ")

    min_char_target = minimum_digit_chars or 0
    max_operand_chars = max(len(top_text), len(bottom_operand), min_char_target)
    digit_span = max_operand_chars * char_width
    left_padding = margin + operator_prefix_chars * char_width
    digit_anchor_x = left_padding + digit_span
    underline_start_x = digit_anchor_x - (
        (len(bottom_operand) + operator_prefix_chars) * char_width
    )
    underline_end_x = digit_anchor_x
    width = digit_anchor_x + margin

    def _round(value: float) -> float:
        return round(value, 4)

    drawing = svgwrite.Drawing(
        size=(f"{_round(width):.2f}px", f"{_round(height):.2f}px"),
    )
    drawing.viewbox(0, 0, _round(width), _round(height))

    text_style = {
        "font_size": f"{_VERTICAL_FONT_SIZE}px",
        "font_family": "FiraMono, monospace",
        "text_anchor": "end",
    }

    drawing.add(
        drawing.text(
            top_text,
            insert=(_round(digit_anchor_x), _round(top_y)),
            **text_style,
        )
    )
    drawing.add(
        drawing.text(
            f"{operator} {bottom_operand}",
            insert=(_round(digit_anchor_x), _round(bottom_y)),
            **text_style,
        )
    )
    drawing.add(
        drawing.line(
            start=(_round(underline_start_x), _round(line_y)),
            end=(_round(underline_end_x), _round(line_y)),
            stroke="#000000",
            stroke_width=2,
        )
    )

    return drawing.tostring()


class _MultiplicationParams(BaseModel):
    """Validated configuration for randomly generated multiplication problems."""

    model_config = ConfigDict(extra="forbid")

    min_operand: int = Field(
        default=0,
        description="Minimum operand value (inclusive) used for random generation.",
    )
    max_operand: int = Field(
        default=10,
        description="Maximum operand value (inclusive) used for random generation.",
    )
    random_seed: int | None = Field(
        default=None,
        description=(
            "Optional seed applied to the plugin's RNG for deterministic outputs during tests."
        ),
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "_MultiplicationParams":
        if self.min_operand > self.max_operand:
            msg = "min_operand must be less than or equal to max_operand"
            raise ValueError(msg)
        return self


class _MultiplicationData(BaseModel):
    """Schema for deterministic problem recreation (PRD §3.2)."""

    model_config = ConfigDict(extra="forbid")

    operands: list[int] = Field(
        ..., min_length=2, max_length=2, description="Pair of operands (top, bottom)."
    )
    operator: str = Field(
        default="X",
        description="Operator token saved in JSON output (always 'X').",
    )
    answer: int | None = Field(
        default=None,
        description="Expected solution; calculated when omitted to keep JSON concise.",
    )
    min_digit_chars: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional minimum character width used to render the original SVG."
        ),
    )

    @model_validator(mode="after")
    def validate_answer(self) -> "_MultiplicationData":
        if self.operator != "X":
            msg = "operator must be 'X' for multiplication problems"
            raise ValueError(msg)

        computed = self.operands[0] * self.operands[1]
        if self.answer is None:
            self.answer = computed
        elif self.answer != computed:
            msg = "answer does not match the product of operands"
            raise ValueError(msg)
        return self


class MultiplicationPlugin:
    """Generate vertically stacked multiplication problems (SDD §3.2.3, MVP Phase 2)."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        """Validate optional configuration and prepare the RNG.

        Args:
            params: Optional dictionary of CLI/YAML parameters supplied by the
                coordinator. Keys may be hyphenated and are normalized before
                validation.

        Raises:
            ValueError: If ``params`` fails validation against
                ``_MultiplicationParams``.
        """

        try:
            self._config = _MultiplicationParams.model_validate(_normalize_param_keys(params))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid multiplication plugin parameters") from exc

        self._random = random.Random()
        if self._config.random_seed is not None:
            self._random.seed(self._config.random_seed)
        self._min_digit_chars = max(
            len(_format_operand(self._config.min_operand)),
            len(_format_operand(self._config.max_operand)),
        )

    @property
    def name(self) -> str:
        """Return the canonical plugin name used by the registry."""

        return "multiplication"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Describe parameters exposed through the CLI and YAML integrations.

        Returns:
            Metadata describing each supported configuration option so that the
            coordinator can surface helpful descriptions to end users.
        """

        return [
            ParameterDefinition(
                name="min-operand",
                default=0,
                description="Minimum operand value (inclusive) for random multiplication problems.",
                type=int,
            ),
            ParameterDefinition(
                name="max-operand",
                default=10,
                description="Maximum operand value (inclusive) for random multiplication problems.",
                type=int,
            ),
            ParameterDefinition(
                name="random-seed",
                default=None,
                description="Optional seed for deterministic random generation during testing.",
                type=int,
            ),
        ]

    def generate_problem(self) -> Problem:
        """Create a random multiplication problem honoring the configured bounds.

        Returns:
            A :class:`Problem` containing the SVG representation and the JSON
            payload required for deterministic regeneration.
        """

        multiplicand = self._random.randint(
            self._config.min_operand, self._config.max_operand
        )
        multiplier = self._random.randint(
            self._config.min_operand, self._config.max_operand
        )
        answer = multiplicand * multiplier

        svg = _render_vertical_problem(
            multiplicand,
            multiplier,
            "X",
            minimum_digit_chars=self._min_digit_chars,
        )
        data = {
            "operands": [multiplicand, multiplier],
            "operator": "X",
            "answer": answer,
            "min_digit_chars": self._min_digit_chars,
        }
        return Problem(svg=svg, data=data)

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a multiplication problem deterministically from serialized data.

        Args:
            data: The JSON payload previously emitted by :meth:`generate_problem`
                or stored within the worksheet export.

        Returns:
            A :class:`Problem` with SVG markup and validated payload suitable for
            downstream rendering.

        Raises:
            ValueError: If ``data`` cannot be validated by ``_MultiplicationData``.
        """

        try:
            validated = _MultiplicationData.model_validate(dict(data))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid multiplication problem data") from exc

        top, bottom = validated.operands
        min_digit_chars = validated.min_digit_chars
        if min_digit_chars is None:
            min_digit_chars = max(
                len(_format_operand(value)) for value in validated.operands
            )

        svg = _render_vertical_problem(
            top,
            bottom,
            "X",
            minimum_digit_chars=min_digit_chars,
        )
        payload = validated.model_dump()
        return Problem(svg=svg, data=payload)
