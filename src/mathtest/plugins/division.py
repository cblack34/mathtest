"""Division plugin implementation for MVP Phase 2 (PRD §3.1, MVP Phase 2)."""

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
        with the ``_DivisionParams`` model definition.
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
    dividend: int,
    divisor: int,
    operator: str,
    minimum_digit_chars: int | None = None,
) -> str:
    """Create a vertically stacked arithmetic SVG illustration for division.

    Args:
        dividend: The number being divided.
        divisor: The number by which we divide.
        operator: The arithmetic operator symbol to display (÷).
        minimum_digit_chars: Optional lower bound for the operand character
            count when measuring layout width. This keeps rendered problems
            consistent across varying operand lengths so downstream scaling
            does not change font sizes.

    Returns:
        An SVG string matching the dimensions and typography outlined in
        ``SDD §3.2.3`` so that division plugins remain visually
        consistent with other arithmetic plugins.
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

    dividend_text = _format_operand(dividend)
    divisor_text = _format_operand(divisor)
    operator_prefix_chars = len(f"{operator} ")

    min_char_target = minimum_digit_chars or 0
    max_operand_chars = max(len(dividend_text), len(divisor_text), min_char_target)
    digit_span = max_operand_chars * char_width
    left_padding = margin + operator_prefix_chars * char_width
    digit_anchor_x = left_padding + digit_span
    underline_start_x = digit_anchor_x - (
        (len(divisor_text) + operator_prefix_chars) * char_width
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
            dividend_text,
            insert=(_round(digit_anchor_x), _round(top_y)),
            **text_style,
        )
    )
    drawing.add(
        drawing.text(
            f"{operator} {divisor_text}",
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


class _DivisionParams(BaseModel):
    """Validated configuration for randomly generated division problems."""

    model_config = ConfigDict(extra="forbid")

    min_dividend: int = Field(
        default=1,
        description="Minimum dividend value (inclusive) used for random generation.",
    )
    max_dividend: int = Field(
        default=100,
        description="Maximum dividend value (inclusive) used for random generation.",
    )
    min_divisor: int = Field(
        default=1,
        description="Minimum divisor value (inclusive) used for random generation.",
    )
    max_divisor: int = Field(
        default=10,
        description="Maximum divisor value (inclusive) used for random generation.",
    )
    allow_remainders: bool = Field(
        default=False,
        description="Whether to allow division problems that result in remainders.",
    )
    random_seed: int | None = Field(
        default=None,
        description=(
            "Optional seed applied to the plugin's RNG for deterministic outputs during tests."
        ),
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "_DivisionParams":
        if self.min_dividend > self.max_dividend:
            msg = "min_dividend must be less than or equal to max_dividend"
            raise ValueError(msg)
        if self.min_divisor > self.max_divisor:
            msg = "min_divisor must be less than or equal to max_divisor"
            raise ValueError(msg)
        if self.min_divisor <= 0:
            msg = "min_divisor must be greater than 0"
            raise ValueError(msg)
        return self


class _DivisionData(BaseModel):
    """Schema for deterministic problem recreation (PRD §3.2)."""

    model_config = ConfigDict(extra="forbid")

    dividend: int = Field(..., description="The number being divided.")
    divisor: int = Field(..., description="The number by which we divide.")
    operator: str = Field(
        default="÷",
        description="Operator token saved in JSON output (always '÷').",
    )
    quotient: int | None = Field(
        default=None,
        description="The result of the division (integer part).",
    )
    remainder: int | None = Field(
        default=None,
        description="The remainder of the division (if any).",
    )
    # The main app expects an 'answer' key for the answer key in the PDF.
    # For division, we express this as either just the quotient (no remainder)
    # or "<quotient> r <remainder>" when a remainder exists.
    answer: str | None = Field(
        default=None,
        description="Display answer used by the worksheet answer key.",
    )
    min_digit_chars: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional minimum character width used to render the original SVG."
        ),
    )

    @model_validator(mode="after")
    def validate_division(self) -> "_DivisionData":
        if self.operator != "÷":
            msg = "operator must be '÷' for division problems"
            raise ValueError(msg)

        if self.divisor == 0:
            msg = "divisor cannot be zero"
            raise ValueError(msg)

        computed_quotient = self.dividend // self.divisor
        computed_remainder = self.dividend % self.divisor

        if self.quotient is None:
            self.quotient = computed_quotient
        elif self.quotient != computed_quotient:
            msg = "quotient does not match the result of dividend // divisor"
            raise ValueError(msg)

        if self.remainder is None:
            self.remainder = computed_remainder
        elif self.remainder != computed_remainder:
            msg = "remainder does not match the result of dividend % divisor"
            raise ValueError(msg)

        expected_answer = (
            str(computed_quotient)
            if computed_remainder == 0
            else f"{computed_quotient} r {computed_remainder}"
        )
        if self.answer is None:
            self.answer = expected_answer
        elif self.answer != expected_answer:
            msg = "answer does not match quotient/remainder values"
            raise ValueError(msg)

        return self


class DivisionPlugin:
    """Generate vertically stacked division problems (SDD §3.2.3, MVP Phase 2)."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        """Validate optional configuration and prepare the RNG.

        Args:
            params: Optional dictionary of CLI/YAML parameters supplied by the
                coordinator. Keys may be hyphenated and are normalized before
                validation.

        Raises:
            ValueError: If ``params`` fails validation against
                ``_DivisionParams``.
        """

        try:
            self._config = _DivisionParams.model_validate(_normalize_param_keys(params))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid division plugin parameters") from exc

        self._random = random.Random()
        if self._config.random_seed is not None:
            self._random.seed(self._config.random_seed)

        # Calculate minimum digit characters for consistent rendering
        self._min_digit_chars = max(
            len(_format_operand(self._config.min_dividend)),
            len(_format_operand(self._config.max_dividend)),
            len(_format_operand(self._config.min_divisor)),
            len(_format_operand(self._config.max_divisor)),
        )

    @property
    def name(self) -> str:
        """Return the canonical plugin name used by the registry."""

        return "division"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Describe parameters exposed through the CLI and YAML integrations.

        Returns:
            Metadata describing each supported configuration option so that the
            coordinator can surface helpful descriptions to end users.
        """

        return [
            ParameterDefinition(
                name="min-dividend",
                default=0,
                description="Minimum dividend value (inclusive) for random division problems.",
                type=int,
            ),
            ParameterDefinition(
                name="max-dividend",
                default=10,
                description="Maximum dividend value (inclusive) for random division problems.",
                type=int,
            ),
            ParameterDefinition(
                name="min-divisor",
                default=1,
                description="Minimum divisor value (inclusive) for random division problems.",
                type=int,
            ),
            ParameterDefinition(
                name="max-divisor",
                default=10,
                description="Maximum divisor value (inclusive) for random division problems.",
                type=int,
            ),
            ParameterDefinition(
                name="allow-remainders",
                default=False,
                description="Whether to allow division problems that result in remainders.",
                type=bool,
            ),
            ParameterDefinition(
                name="random-seed",
                default=None,
                description="Optional seed for deterministic random generation during testing.",
                type=int,
            ),
        ]

    def generate_problem(self) -> Problem:
        """Create a random division problem honoring the configured bounds.

        Returns:
            A :class:`Problem` containing the SVG representation and the JSON
            payload required for deterministic regeneration.
        """

        def _sample_valid_division() -> tuple[int, int, int, int]:
            while True:
                dv = self._random.randint(
                    self._config.min_dividend, self._config.max_dividend
                )
                dr = self._random.randint(
                    self._config.min_divisor, self._config.max_divisor
                )
                rem = dv % dr
                if not self._config.allow_remainders and rem != 0:
                    continue
                quo = dv // dr
                return dv, dr, quo, rem

        dividend, divisor, quotient, remainder = _sample_valid_division()

        svg = _render_vertical_problem(
            dividend,
            divisor,
            "÷",
            minimum_digit_chars=self._min_digit_chars,
        )
        answer_str = str(quotient) if remainder == 0 else f"{quotient} r {remainder}"
        data = {
            "dividend": dividend,
            "divisor": divisor,
            "operator": "÷",
            "quotient": quotient,
            "remainder": remainder,
            "answer": answer_str,
            "min_digit_chars": self._min_digit_chars,
        }
        return Problem(svg=svg, data=data)

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a division problem deterministically from serialized data.

        Args:
            data: The JSON payload previously emitted by :meth:`generate_problem`
                or stored within the worksheet export.

        Returns:
            A :class:`Problem` with SVG markup and validated payload suitable for
            downstream rendering.

        Raises:
            ValueError: If ``data`` cannot be validated by ``_DivisionData``.
        """

        try:
            validated = _DivisionData.model_validate(dict(data))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid division problem data") from exc

        dividend = validated.dividend
        divisor = validated.divisor
        min_digit_chars = validated.min_digit_chars
        if min_digit_chars is None:
            min_digit_chars = max(
                len(_format_operand(dividend)),
                len(_format_operand(divisor)),
            )

        svg = _render_vertical_problem(
            dividend,
            divisor,
            "÷",
            minimum_digit_chars=min_digit_chars,
        )
        payload = validated.model_dump()
        return Problem(svg=svg, data=payload)
