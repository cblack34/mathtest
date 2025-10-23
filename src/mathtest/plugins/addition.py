"""Addition plugin implementation for MVP Phase 2 (PRD §3.1, MVP Phase 2)."""

from __future__ import annotations

import random
from typing import Any, Mapping

import svgwrite
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..interface import ParameterDefinition, Problem


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convert CLI/YAML style keys (``max-operand``) to model field names."""

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


def _format_operand(value: int) -> str:
    """Format an operand for display, wrapping negatives in parentheses."""

    return f"({value})" if value < 0 else str(value)


def _render_vertical_problem(top: int, bottom: int, operator: str) -> str:
    """Create a vertically stacked arithmetic SVG using ``svgwrite`` (SDD §3.2.3)."""

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


class _AdditionParams(BaseModel):
    """Pydantic validation for random generation parameters."""

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
    def validate_bounds(self) -> "_AdditionParams":
        if self.min_operand > self.max_operand:
            msg = "min_operand must be less than or equal to max_operand"
            raise ValueError(msg)
        return self


class _AdditionData(BaseModel):
    """Schema for deterministic problem recreation (PRD §3.2)."""

    model_config = ConfigDict(extra="forbid")

    operands: list[int] = Field(
        ..., min_length=2, max_length=2, description="Pair of operands (top, bottom)."
    )
    operator: str = Field(
        default="+",
        description="Operator token saved in JSON output (always '+').",
    )
    answer: int | None = Field(
        default=None,
        description="Expected solution; calculated when omitted to keep JSON concise.",
    )

    @model_validator(mode="after")
    def validate_answer(self) -> "_AdditionData":
        if self.operator != "+":
            msg = "operator must be '+' for addition problems"
            raise ValueError(msg)

        computed = sum(self.operands)
        if self.answer is None:
            self.answer = computed
        elif self.answer != computed:
            msg = "answer does not match the sum of operands"
            raise ValueError(msg)
        return self


class AdditionPlugin:
    """Generate vertically stacked addition problems (SDD §3.2.3, MVP Phase 2)."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        """Validate optional configuration and prepare the RNG (MVP Phase 2 task)."""

        try:
            self._config = _AdditionParams.model_validate(_normalize_param_keys(params))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid addition plugin parameters") from exc

        self._random = random.Random()
        if self._config.random_seed is not None:
            self._random.seed(self._config.random_seed)

    @property
    def name(self) -> str:
        """Return the canonical plugin name used by the registry."""

        return "addition"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Expose CLI/YAML parameter metadata (PRD §3.3)."""

        return [
            ParameterDefinition(
                name="min-operand",
                default=0,
                description="Minimum operand value (inclusive) for random addition problems.",
            ),
            ParameterDefinition(
                name="max-operand",
                default=10,
                description="Maximum operand value (inclusive) for random addition problems.",
            ),
            ParameterDefinition(
                name="random-seed",
                default=None,
                description="Optional seed for deterministic random generation during testing.",
            ),
        ]

    def generate_problem(self) -> Problem:
        """Create a random addition problem honoring the configured bounds."""

        augend = self._random.randint(self._config.min_operand, self._config.max_operand)
        addend = self._random.randint(self._config.min_operand, self._config.max_operand)
        answer = augend + addend

        svg = _render_vertical_problem(augend, addend, "+")
        data = {
            "operands": [augend, addend],
            "operator": "+",
            "answer": answer,
        }
        return Problem(svg=svg, data=data)

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate an addition problem deterministically from serialized data."""

        try:
            validated = _AdditionData.model_validate(dict(data))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid addition problem data") from exc

        top, bottom = validated.operands
        svg = _render_vertical_problem(top, bottom, "+")
        payload = validated.model_dump()
        return Problem(svg=svg, data=payload)
