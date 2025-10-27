# Software Design Document (SDD) for MathTest

## 1. System Architecture

MathTest features a layered, extensible architecture: CLI layer for user input and dynamic flag generation, coordinator
layer for central config merging, orchestration of multiple tests, and plugin invocation, generation plugins for
creating visual and data representations of problems, and output plugins for rendering results in selectable formats (
with multi-output support, treating JSON as compatible). The design strictly follows SOLID principles: Single
Responsibility (e.g., coordinator solely merges and orchestrates), Open-Closed (plugins extend without core changes),
Liskov Substitution (all plugins interchangeable via protocols), Interface Segregation (minimal protocols), and
Dependency Inversion (high-level modules depend on abstractions). Data flows unidirectionally: CLI -> coordinator (
unified config) -> plugins (extraction) -> outputs. Immutable Pydantic models prevent state mutations, and structured
logging captures all significant events (e.g., config merges, plugin init, errors) at info/error levels. Tests are
segregated into unit (component isolation, e.g., plugin validation) and integration (full flows, e.g., CLI to output)
packages for organized execution.

## 2. Key Components

### 2.1 Interfaces (Python Protocols)

```python
from typing import Any, Mapping, Protocol, Sequence, Type

from pydantic import BaseModel, ConfigDict


class ParameterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(..., description="Parameter identifier")
    default: Any = Field(..., description="Default value")
    description: str = Field(..., description="Help text")
    type: Type[Any] | str | None = Field(default=None, description="Type hint")


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    svg: str = Field(..., description="SVG markup")
    data: dict[str, Any] = Field(..., description="Structured data incl. answer")


class MathProblemPlugin(Protocol):
    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        ...

    @property
    def name(self) -> str:
        ...

    @classmethod
    def get_parameters(cls) -> Sequence[ParameterDefinition]:
        ...

    def generate_problem(self) -> Problem:
        ...

    @classmethod
    def generate_from_data(cls, data: Mapping[str, Any]) -> Problem:
        ...


class OutputGenerator(Protocol):
    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        ...

    @property
    def name(self) -> str:
        ...

    @classmethod
    def get_parameters(cls) -> Sequence[ParameterDefinition]:
        ...

    def generate(self, problems: Sequence[Problem]) -> None:
        ...
```

### 2.2 Coordinator

- **Config Merging**: Aggregate defaults from all plugins' get_parameters, layer YAML sections (common, problem-plugins,
  output-plugins), apply CLI overrides, normalize keys, and produce unified dict; log each step and validate for
  conflicts (e.g., bounds).
- **Generation Workflow**: For each test in test-count, select/instantiate generation plugins, generate/interleave
  problems (deterministic shuffle via hashlib on seeds/plan), handle JSON reproduction by parsing and delegating to
  from_data.
- **Output Invocation**: Instantiate selected output plugins, pass problems per test; support multiple by iterating and
  logging each render.
- **Models**: Frozen Pydantic for GenerationRequest (incl. problems-per-test, test-count), SerializedProblem (for JSON).
- **Error Handling**: Catch specific errors (e.g., ValueError for bounds, OSError for files), log with exc_info, raise
  custom errors with user messages.

### 2.3 CLI (Typer)

- **Flag Generation**: Use custom TyperCommand to dynamically add enables (separate for generation, repeatable
  --output-plugin for outputs) and overrides from get_parameters; validate single non-JSON outputs if needed, but allow
  JSON multi.
- **Parsing**: Load YAML safely, validate JSON with Pydantic, build unified config via coordinator util.
- **Dependency Injection**: Provide registries/context for plugins; echo success messages (e.g., "Generated 3 tests with
  10 problems each").
- **Help**: Panels grouped by type (e.g., "Problem Plugins" with descriptions, defaults; "Output Plugins" similar).

### 2.4 Generation Plugins

- **Config Extraction**: From unified dict: Build merged = defaults (from get_parameters) | common |
  problem-plugins[name]; validate with Pydantic (aliases for hyphens, validators for logic like min <= max).
- **Generation**: Random: Seeded random for values; produce SVG (via shared utils for vertical layouts, ensuring
  consistent font/size) and data (immutable dict with answer). From Data: Reconstruct deterministically.
- **Entry Point**: mathtest.generation_plugins; log init and generation.
- **Edge Cases**: Handle zero quantity, negative values where allowed, min_digit_chars for sizing.

### 2.5 Output Plugins

- **Config Extraction**: Similar to generation: defaults + common + output-plugins[name]; Pydantic validation.
- **"traditional-pdf" Parameters**: path (str, required), title (str, default "Test"), margin_inches (float, default
  0.75, gt 0), columns (int, default 4, ge 1), problem_spacing_inches (float, default 0.35, ge 0), answer_font_size (
  int, default 12, ge 6), include_answers (bool, default False), include_student_header (bool, default True), etc.
- **Rendering**: Use ReportLab Platypus for flowables (e.g., Image for SVGs, Paragraph for text/answers); handle
  multi-test by paging; scale with tolerance for floats; log render steps.
- **JSON Special**: Serialize as list of {type, data}; multi-compatible without file conflicts (e.g., append test
  number).
- **Entry Point**: mathtest.output_plugins; generate writes to files based on params.

### 2.6 Registries

- **Implementation**: Separate classes for generation and outputs; load from entry points, cache names to classes,
  validate protocol compliance; log discoveries.
- **Instantiation**: Create instances with unified config; error on unknowns.

## 3. Data Models

- **Pydantic Usage**: All models with extra="forbid", frozen=True; use field aliases for CLI hyphens, model_validators
  for cross-field checks (e.g., min_operand <= max_operand), and default factories where appropriate.
- **Examples**: ParameterSet for merged sections; SerializedProblem for JSON (problem_type, data).

## 4. Error Handling

- **Strategy**: Avoid broad Exception; use specific (e.g., ValidationError for Pydantic, PluginRegistryError for
  unknowns); log at error level with full trace; propagate user-friendly messages to CLI (e.g., via typer.BadParameter);
  handle file I/O with retries or clear errors.

## 5. Testing

- **Organization**: Separate packages: tests/unit (fast, mocked isolations like plugin config extraction),
  tests/integration (slow, full CLI-to-output flows with temp files).
- **Coverage**: >85%; use pytest --cov; markers for filtering; fixtures for unified configs, seeded random, mocked
  registries.
- **Scopes**: Unit: Individual methods (e.g., merging logic branches); Integration: End-to-end (e.g., flag combinations
  producing expected PDFs/JSON).

## 6. Documentation

- **Style**: Google-style docstrings with sections for Args, Returns, Raises, Examples (descriptive, no code); cover
  behaviors, edges.
- **Additional**: README with CLI examples, plugin extension guide.

## 7. Best Practices

- **Code Quality**: DRY with utils (e.g., key normalization); SRP in components; meaningful names (e.g., _
  extract_plugin_config); type hints everywhere.
- **Libraries**: Pydantic for all validation; Typer for CLI; ReportLab Platypus for flexible rendering; svgwrite/svglib
  for visuals.
- **Logging**: Module-level loggers; info for normals, error for issues.
