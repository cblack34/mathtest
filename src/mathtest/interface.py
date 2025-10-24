"""Core interfaces shared by Mathtest components.

The MVP relies on these interfaces to keep plugins, the coordinator, and
output generators loosely coupled as described in the PRD/SDD documents.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, Type, runtime_checkable

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Problem(BaseModel):
    """Normalized representation of a generated math problem.

    Each plugin returns a :class:`Problem` instance so the coordinator and
    output layers can operate on a consistent schema (PRD §3.1, SDD §3.2.3).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    svg: str = Field(
        ..., description="SVG markup representing the rendered problem for layout"
    )
    data: dict[str, Any] = Field(
        ...,
        description=(
            "Structured data required to recreate the problem, including the answer"
        ),
    )


class ParameterDefinition(BaseModel):
    """Metadata describing a configurable plugin parameter.

    Typer flags and YAML/JSON schemas derive from these definitions to keep the
    CLI and coordinator dynamic (SDD §3.2.3, PRD §3.3).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., description="Parameter identifier such as 'max-operand'")
    default: Any = Field(..., description="Default value applied when unspecified")
    description: str = Field(..., description="Human friendly help text for the CLI")
    value_type: Type[Any] | str | None = Field(
        default=None,
        alias="type",
        validation_alias=AliasChoices("type", "value_type"),
        description=(
            "Optional type hint used by dynamic surfaces such as the CLI to coerce "
            "values. Accepts Python types or string aliases (e.g., 'int')."
        ),
    )

    @property
    def type(self) -> Type[Any] | str | None:
        """Expose ``value_type`` under the historic ``type`` attribute name."""

        return self.value_type


@runtime_checkable
class MathProblemPlugin(Protocol):
    """Contract for problem-generating plugins.

    Implementations may accept an optional params mapping during instantiation
    so the coordinator can supply merged configuration (SDD §3.2.3).
    """

    @property
    def name(self) -> str:
        """Unique plugin name, e.g., ``'addition'``."""

    @classmethod
    def get_parameters(cls) -> Sequence[ParameterDefinition]:
        """Return parameter metadata used to build dynamic configuration surfaces."""

    def generate_problem(self) -> Problem:
        """Create a problem using the instance configuration for random generation."""

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        """Recreate a problem deterministically from serialized data (JSON input)."""


@runtime_checkable
class OutputGenerator(Protocol):
    """Interface for output backends such as PDF writers (SDD §3.2.5)."""

    def generate(self, problems: Sequence[Problem], params: Mapping[str, Any]) -> None:
        """Produce an artifact from the supplied problems and layout parameters."""