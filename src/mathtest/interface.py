from typing import Protocol, runtime_checkable
from pydantic import BaseModel

class Problem(BaseModel):
    svg: str
    data: dict[str, any]  # e.g., {"operands": [5, 3], "operator": "+", "answer": 8}

@runtime_checkable
class MathProblemPlugin(Protocol):
    """
    Note on instantiation: Plugins may optionally accept a params dict in __init__ for configuration.
    The coordinator will attempt to pass merged params during instantiation if provided; otherwise, use no-args init.
    """

    @property
    def name(self) -> str:
        """Unique name of the plugin, e.g., 'addition'."""
        ...

    @classmethod
    def get_parameters(cls) -> list[tuple[str, any, str]]:
        """
        Return list of (param_name, default_value, help_text) for this plugin.
        e.g., [('max-operand', 10, 'Maximum operand value')]
        """
        ...

    def generate_problem(self) -> Problem:
        """
        Generate the problem randomly using the initialized configuration (if any).
        """

        ...

    @classmethod
    def generate_from_data(cls, data: dict[str, any]) -> Problem:
        """
        Generate the problem deterministically from a provided data dict (e.g., from JSON input).
        """
        ...

@runtime_checkable
class OutputGenerator(Protocol):
    def generate(self, problems: list[Problem], params: dict[str, any]) -> None:
        """
        Produce output (e.g., PDF) from problems and layout params.
        """
        ...