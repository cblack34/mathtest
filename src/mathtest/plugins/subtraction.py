"""Subtraction plugin implementation for MVP Phase 2 (PRD §3.1, MVP Phase 2)."""

from __future__ import annotations

import random
from typing import Any, Mapping

import svgwrite
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..interface import ParameterDefinition, Problem


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map external configuration keys to Pydantic field names.

    Args:
        params: Raw configuration dictionary that may contain hyphenated keys
            sourced from CLI flags or YAML configuration files.

    Returns:
        A dictionary containing only snake_case keys so that
        ``_SubtractionParams`` can validate the input.
    """

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


def _format_operand(value: int) -> str:
    """Render operands with parentheses when negative for readability.

    Args:
        value: The operand to render in the vertical layout.

    Returns:
        The operand converted to a string with negative values wrapped in
        parentheses to preserve alignment and clarity.
    """

    return f"({value})" if value < 0 else str(value)


def _render_vertical_problem(top: int, bottom: int, operator: str) -> str:
    """Create a vertically stacked subtraction SVG (SDD §3.2.3).

    Args:
        top: The top operand shown in the rendered SVG.
        bottom: The bottom operand displayed beneath the operator.
        operator: The arithmetic symbol used to label the operation.

    Returns:
        An SVG string that follows the shared layout specifications so worksheets
        have consistent typography and spacing across plugins.
    """

    width = 140
    height = 90
    margin = 12
    top_y = 32
    bottom_y = 64
    line_y = bottom_y + 6

    drawing = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
    drawing.viewbox(0, 0, width, height)

    text_style = {
        "font_size": "28px",
        "font_family": "FiraMono, monospace",
        "text_anchor": "end",
    }

    drawing.add(
        drawing.text(
            _format_operand(top),
            insert=(width - margin, top_y),
            **text_style,
        )
    )
    drawing.add(
        drawing.text(
            f"{operator} {_format_operand(bottom)}",
            insert=(width - margin, bottom_y),
            **text_style,
        )
    )
    drawing.add(
        drawing.line(
            start=(margin, line_y),
            end=(width - margin, line_y),
            stroke="#000000",
            stroke_width=2,
        )
    )

    return drawing.tostring()


class _SubtractionParams(BaseModel):
    """Validated configuration for randomly generated subtraction problems."""

    model_config = ConfigDict(extra="forbid")

    min_operand: int = Field(
        default=0,
        description="Minimum operand value (inclusive) when selecting random numbers.",
    )
    max_operand: int = Field(
        default=10,
        description="Maximum operand value (inclusive) when selecting random numbers.",
    )
    allow_negative_result: bool = Field(
        default=False,
        description="If true, random problems may produce negative answers.",
    )
    random_seed: int | None = Field(
        default=None,
        description="Optional RNG seed for deterministic test scenarios.",
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "_SubtractionParams":
        if self.min_operand > self.max_operand:
            msg = "min_operand must be less than or equal to max_operand"
            raise ValueError(msg)
        return self


class _SubtractionData(BaseModel):
    """Schema for deterministic subtraction recreation (PRD §3.2)."""

    model_config = ConfigDict(extra="forbid")

    operands: list[int] = Field(
        ..., min_length=2, max_length=2, description="Pair of operands (minuend, subtrahend)."
    )
    operator: str = Field(
        default="-",
        description="Operator token stored in JSON output (always '-').",
    )
    answer: int | None = Field(
        default=None,
        description="Expected difference; filled automatically when omitted.",
    )

    @model_validator(mode="after")
    def validate_answer(self) -> "_SubtractionData":
        if self.operator != "-":
            msg = "operator must be '-' for subtraction problems"
            raise ValueError(msg)

        minuend, subtrahend = self.operands
        computed = minuend - subtrahend
        if self.answer is None:
            self.answer = computed
        elif self.answer != computed:
            msg = "answer does not match the difference of operands"
            raise ValueError(msg)
        return self


class SubtractionPlugin:
    """Generate vertically stacked subtraction problems (SDD §3.2.3, MVP Phase 2)."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        """Validate optional configuration and set up deterministic random support.

        Args:
            params: Optional dictionary of CLI/YAML parameters supplied by the
                coordinator. Hyphenated keys are normalized before validation.

        Raises:
            ValueError: If ``params`` fails validation against
                ``_SubtractionParams``.
        """

        try:
            self._config = _SubtractionParams.model_validate(
                _normalize_param_keys(params)
            )
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid subtraction plugin parameters") from exc

        self._random = random.Random()
        if self._config.random_seed is not None:
            self._random.seed(self._config.random_seed)

    @property
    def name(self) -> str:
        """Return the canonical plugin name used by the registry."""

        return "subtraction"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Describe parameters exposed through the CLI and YAML integrations.

        Returns:
            Metadata describing each subtraction-specific option so the
            coordinator can render informative help text.
        """

        return [
            ParameterDefinition(
                name="min-operand",
                default=0,
                description="Minimum operand value (inclusive) for random subtraction problems.",
            ),
            ParameterDefinition(
                name="max-operand",
                default=10,
                description="Maximum operand value (inclusive) for random subtraction problems.",
            ),
            ParameterDefinition(
                name="allow-negative-result",
                default=False,
                description="Allow randomly generated problems to have negative answers.",
            ),
            ParameterDefinition(
                name="random-seed",
                default=None,
                description="Optional seed for deterministic random generation during testing.",
            ),
        ]

    def generate_problem(self) -> Problem:
        """Create a random subtraction problem according to configured bounds.

        Returns:
            A :class:`Problem` containing the rendered SVG and JSON payload for
            deterministic regeneration.
        """

        minuend = self._random.randint(self._config.min_operand, self._config.max_operand)
        subtrahend = self._random.randint(
            self._config.min_operand, self._config.max_operand
        )

        if not self._config.allow_negative_result and minuend < subtrahend:
            minuend, subtrahend = subtrahend, minuend

        answer = minuend - subtrahend

        svg = _render_vertical_problem(minuend, subtrahend, "-")
        data = {
            "operands": [minuend, subtrahend],
            "operator": "-",
            "answer": answer,
        }
        return Problem(svg=svg, data=data)

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a subtraction problem deterministically from serialized data.

        Args:
            data: The JSON payload previously emitted by :meth:`generate_problem`
                or stored alongside worksheet exports.

        Returns:
            A :class:`Problem` containing SVG markup and the validated payload.

        Raises:
            ValueError: If ``data`` cannot be validated by ``_SubtractionData``.
        """

        try:
            validated = _SubtractionData.model_validate(dict(data))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid subtraction problem data") from exc

        minuend, subtrahend = validated.operands
        svg = _render_vertical_problem(minuend, subtrahend, "-")
        payload = validated.model_dump()
        return Problem(svg=svg, data=payload)
