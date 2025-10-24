"""Analog clock plugin implementation (PRD §3.1, MVP future scope)."""

from __future__ import annotations

import math
import random
from typing import Any, Iterable, Mapping

import svgwrite  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..interface import ParameterDefinition, Problem


_ALLOWED_MINUTE_INTERVALS = {5, 15, 30, 60}


def _normalize_param_keys(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convert hyphenated configuration keys to snake_case names."""

    normalized: dict[str, Any] = {}
    for key, value in (params or {}).items():
        normalized[key.replace("-", "_")] = value
    return normalized


def _format_answer(hour: int, minute: int, is_24_hour: bool) -> str:
    """Return the worksheet answer string in standard time notation."""

    if is_24_hour:
        return f"{hour:02d}:{minute:02d}"
    return f"{hour}:{minute:02d}"


def _hour_hand_angle(hour: int, minute: int, *, is_24_hour: bool, accurate: bool) -> float:
    """Compute the hour hand angle measured clockwise from 12 o'clock."""

    if is_24_hour:
        step = 360.0 / 24.0
        base_hour = hour % 24
    else:
        step = 360.0 / 12.0
        base_hour = hour % 12
    angle = base_hour * step
    if accurate:
        angle += (minute / 60.0) * step
    return angle


def _minute_hand_angle(minute: int) -> float:
    """Compute the minute hand angle measured clockwise from 12 o'clock."""

    return (minute % 60) * 6.0


class _ClockParams(BaseModel):
    """Validated configuration for randomly generated clock problems."""

    model_config = ConfigDict(extra="forbid")

    minute_interval: int = Field(
        default=15,
        description=(
            "Minute increments available for random selection."
            " Permitted values: 5, 15, 30, or 60."
        ),
    )
    accurate_hour: bool = Field(
        default=False,
        description="Move the hour hand between numbers based on the minute value.",
    )
    random_seed: int | None = Field(
        default=None,
        description="Optional seed applied to the plugin RNG for deterministic tests.",
    )
    clock_12_hour: bool = Field(
        default=True,
        description="Render the clock using a 12-hour dial (default).",
    )
    clock_24_hour: bool = Field(
        default=False,
        description="Render the clock using a 24-hour dial with hours 0–23.",
    )

    @model_validator(mode="after")
    def validate_config(self) -> "_ClockParams":
        if self.minute_interval not in _ALLOWED_MINUTE_INTERVALS:
            msg = "minute_interval must be one of {5, 15, 30, 60}"
            raise ValueError(msg)
        if self.clock_12_hour and self.clock_24_hour:
            msg = "clock_12_hour and clock_24_hour cannot both be true"
            raise ValueError(msg)
        return self

    @property
    def is_24_hour(self) -> bool:
        """Return ``True`` when the clock should display a 24-hour dial."""

        return self.clock_24_hour or not self.clock_12_hour


class _ClockData(BaseModel):
    """Serialized data describing a generated clock problem."""

    model_config = ConfigDict(extra="forbid")

    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    minute_interval: int = Field(...)
    accurate_hour: bool = Field(default=False)
    is_24_hour: bool = Field(default=False)
    answer: str | None = Field(default=None)
    hour_hand_angle: float | None = Field(default=None)
    minute_hand_angle: float | None = Field(default=None)

    @model_validator(mode="after")
    def validate_payload(self) -> "_ClockData":
        if self.minute_interval not in _ALLOWED_MINUTE_INTERVALS:
            msg = "minute_interval must be one of {5, 15, 30, 60}"
            raise ValueError(msg)
        if self.minute % self.minute_interval != 0:
            msg = "minute must align with the configured minute interval"
            raise ValueError(msg)
        if self.is_24_hour:
            if not 0 <= self.hour <= 23:
                msg = "hour must be between 0 and 23 for 24-hour clocks"
                raise ValueError(msg)
        else:
            if not 1 <= self.hour <= 12:
                msg = "hour must be between 1 and 12 for 12-hour clocks"
                raise ValueError(msg)

        expected_answer = _format_answer(self.hour, self.minute, self.is_24_hour)
        if self.answer is None:
            self.answer = expected_answer
        elif self.answer != expected_answer:
            msg = "answer does not match hour/minute values"
            raise ValueError(msg)

        expected_hour_angle = _hour_hand_angle(
            self.hour,
            self.minute,
            is_24_hour=self.is_24_hour,
            accurate=self.accurate_hour,
        )
        expected_minute_angle = _minute_hand_angle(self.minute)

        if self.hour_hand_angle is None:
            self.hour_hand_angle = expected_hour_angle
        elif not math.isclose(self.hour_hand_angle, expected_hour_angle, abs_tol=1e-6):
            msg = "hour_hand_angle does not match computed value"
            raise ValueError(msg)

        if self.minute_hand_angle is None:
            self.minute_hand_angle = expected_minute_angle
        elif not math.isclose(self.minute_hand_angle, expected_minute_angle, abs_tol=1e-6):
            msg = "minute_hand_angle does not match computed value"
            raise ValueError(msg)

        return self


def _polar_point(angle_degrees: float, radius: float, center: float) -> tuple[float, float]:
    """Convert polar coordinates to Cartesian values relative to ``center``."""

    radians = math.radians(angle_degrees - 90.0)
    x = center + radius * math.cos(radians)
    y = center + radius * math.sin(radians)
    return (round(x, 4), round(y, 4))


def _clock_labels(is_24_hour: bool) -> Iterable[str]:
    """Return the ordered labels that appear around the clock face."""

    if is_24_hour:
        return (f"{value}" for value in range(24))
    return (f"{value}" for value in range(1, 13))


def _render_clock_face(data: _ClockData) -> str:
    """Render an analog clock SVG honoring ``data``."""

    size = 220
    center = size / 2
    outer_radius = 95.0
    number_radius = 78.0
    tick_outer_radius = number_radius - 8.0
    tick_inner_radius = tick_outer_radius - 12.0
    hour_hand_length = 58.0
    minute_hand_length = 82.0

    drawing = svgwrite.Drawing(size=(f"{size}px", f"{size}px"))
    drawing.viewbox(0, 0, size, size)

    drawing.add(
        drawing.circle(
            center=(center, center),
            r=outer_radius,
            fill="#FFFFFF",
            stroke="#000000",
            stroke_width=2,
        )
    )

    labels = list(_clock_labels(data.is_24_hour))
    step = 360.0 / len(labels)
    number_font_size = 14 if data.is_24_hour else 20

    for index, label in enumerate(labels):
        angle = index * step
        text_x, text_y = _polar_point(angle, number_radius, center)
        drawing.add(
            drawing.text(
                label,
                insert=(text_x, text_y + number_font_size / 3.0),
                text_anchor="middle",
                font_size=f"{number_font_size}px",
                font_family="FiraSans, sans-serif",
            )
        )

        tick_start = _polar_point(angle, tick_inner_radius, center)
        tick_end = _polar_point(angle, tick_outer_radius, center)
        drawing.add(
            drawing.line(
                start=tick_start,
                end=tick_end,
                stroke="#000000",
                stroke_width=2,
            )
        )

    hour_end = _polar_point(data.hour_hand_angle, hour_hand_length, center)
    minute_end = _polar_point(data.minute_hand_angle, minute_hand_length, center)

    drawing.add(
        drawing.line(
            start=(center, center),
            end=hour_end,
            stroke="#000000",
            stroke_width=5,
        )
    )
    drawing.add(
        drawing.line(
            start=(center, center),
            end=minute_end,
            stroke="#000000",
            stroke_width=3,
        )
    )

    drawing.add(
        drawing.circle(
            center=(center, center),
            r=4,
            fill="#000000",
        )
    )

    return drawing.tostring()


class ClockPlugin:
    """Generate analog clock-reading problems."""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        try:
            self._config = _ClockParams.model_validate(_normalize_param_keys(params))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid clock plugin parameters") from exc

        self._random = random.Random()
        if self._config.random_seed is not None:
            self._random.seed(self._config.random_seed)

    @property
    def name(self) -> str:
        """Return the canonical registry name for the plugin."""

        return "clock"

    @classmethod
    def get_parameters(cls) -> list[ParameterDefinition]:
        """Expose parameter metadata for CLI and YAML integrations."""

        return [
            ParameterDefinition(
                name="minute-interval",
                default=15,
                description="Minute increments for random selection (5, 15, 30, or 60).",
                type=int,
            ),
            ParameterDefinition(
                name="accurate-hour",
                default=False,
                description="Move the hour hand toward the next hour based on the minutes.",
                type=bool,
            ),
            ParameterDefinition(
                name="clock-12-hour",
                default=True,
                description="Render a 12-hour dial (1–12).",
                type=bool,
            ),
            ParameterDefinition(
                name="clock-24-hour",
                default=False,
                description="Render a 24-hour dial (0–23).",
                type=bool,
            ),
            ParameterDefinition(
                name="random-seed",
                default=None,
                description="Optional seed for deterministic random generation during testing.",
                type=int,
            ),
        ]

    def _random_hour(self) -> int:
        if self._config.is_24_hour:
            return self._random.randint(0, 23)
        return self._random.randint(1, 12)

    def _random_minute(self) -> int:
        if self._config.minute_interval == 60:
            return 0
        choices = list(range(0, 60, self._config.minute_interval))
        return self._random.choice(choices)

    def generate_problem(self) -> Problem:
        """Generate a random analog clock problem."""

        hour = self._random_hour()
        minute = self._random_minute()

        hour_angle = _hour_hand_angle(
            hour,
            minute,
            is_24_hour=self._config.is_24_hour,
            accurate=self._config.accurate_hour,
        )
        minute_angle = _minute_hand_angle(minute)

        payload = _ClockData.model_validate(
            {
                "hour": hour,
                "minute": minute,
                "minute_interval": self._config.minute_interval,
                "accurate_hour": self._config.accurate_hour,
                "is_24_hour": self._config.is_24_hour,
                "hour_hand_angle": hour_angle,
                "minute_hand_angle": minute_angle,
            }
        )

        svg = _render_clock_face(payload)
        return Problem(svg=svg, data=payload.model_dump())

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a clock problem deterministically from serialized data."""

        try:
            payload = _ClockData.model_validate(dict(data))
        except ValidationError as exc:  # pragma: no cover - defensive rewrap
            raise ValueError("Invalid clock problem data") from exc

        svg = _render_clock_face(payload)
        return Problem(svg=svg, data=payload.model_dump())

