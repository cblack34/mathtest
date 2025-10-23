### System Design Document (SDD) for Mathtest

#### 1. Introduction

**Purpose**: This SDD outlines the technical design for Mathtest, a Python-based application for generating customizable
math tests with a plugin architecture. It translates the PRD (dated October 23, 2025) into a detailed architecture,
focusing on CLI implementation, plugin extensibility, and PDF/JSON output, with a structure that supports future UI
replacement and output format changes.
**Scope**: Covers the `mathtest` package, including CLI, coordination, plugins, and supporting modules, implemented anew
using the POC as a reference.
**Date**: October 23, 2025

#### 2. System Overview

**Architecture Style**: Modular, plugin-based design with a clear separation between the CLI interface, coordination
logic, plugin implementations, and output generation. This follows the **Mediator Pattern** for plugin coordination (
with the coordinator as the central mediator), the **Facade Pattern** for plugin interfaces, and an **Interface Pattern
** for output handling, ensuring loose coupling, reusability, and flexibility.
**Key Components**:

- **CLI Module**: Handles user input via Typer, passing parameters to the coordinator.
- **Coordinator Module**: Manages plugin loading, parameter merging, problem collection, and delegates output to an
  interface.
- **Plugin System**: Dynamic loading via entry points, with each plugin generating `Problem` objects.
- **Output Interface**: Defines an abstract interface for output generation (e.g., PDF), implemented separately.
- **Supporting Modules**: Registry for plugin management, interface definition.

#### 3. Detailed Design

##### 3.1 Directory Structure

```
root/
|-- mathtest/
|   |-- __init__.py
|   |-- main.py         # CLI module
|   |-- coordinator.py  # Test building coordination
|   |-- interface.py    # Plugin and output interfaces
|   |-- registry.py     # Plugin registry
|   |-- output/
|   |   |-- __init__.py
|   |   |-- pdf.py      # Initial PDF implementation
|   |-- plugins/
|   |   |-- __init__.py
|   |   |-- addition.py
|   |   |-- subtraction.py
|   |   |-- multiplication.py
|   |   |-- division.py
|   |   |-- clock_reading.py
|-- tests/
|   |-- __init__.py
|   |-- test_plugins.py
|   |-- test_main.py
|   |-- test_coordinator.py
|   |-- test_output.py
|-- pyproject.toml      # UV configuration and entry points
|-- README.md
|-- .gitignore
```

- **Rationale**: Root-level `mathtest/` package simplifies access, with `output/` housing the interface-driven output
  logic and `tests/` separated for pytest. `pyproject.toml` manages dependencies and entry points with UV.

##### 3.2 Component Specifications

###### 3.2.1 CLI Module (`main.py`)

- **Responsibility**: Provides the Typer-based command-line interface, parsing flags and invoking the coordinator.
- **Inputs**: CLI flags (e.g., `--addition`, `--total-problems`, `--json-output`, `--json-input`).
- **Outputs**: Calls `coordinator.generate_test()` with parsed parameters, ignoring type flags if `--json-input` is
  provided.
- **Design Decisions**:
    - Uses Typer for dynamic flag generation based on plugin parameters.
    - Treats `--config` (YAML) as optional, defaulting to empty if omitted.
    - Passes all flags to the coordinator as a structured input object, validated with Pydantic models.
- **Extensibility**: Thin wrapper, replaceable with a UI module without altering coordination.

###### 3.2.2 Coordinator Module (`coordinator.py`)

- **Responsibility**: Core logic for test generation, including plugin loading, parameter merging, problem collection,
  and delegating output to an interface.
- **Inputs**: Parameters from CLI (or future UI), optional YAML config, optional JSON input.
- **Outputs**: List of `Problem` objects, handed to the output interface or saved as JSON.
- **Design Decisions**:
    - Uses Mediator pattern to coordinate between plugins, inputs, and outputs, reducing direct dependencies.
    - Merges parameters in order: plugin defaults < optional YAML `common` < optional YAML plugin-specific < CLI flags,
      unless overridden by JSON input.
    - If `--json-input` is provided, ignores type flags (e.g., `--addition`) and uses JSON `data` dicts to drive plugin
      generation.
    - Delegates output (e.g., PDF, JSON) to an interface implementation.
    - Validates parameters and JSON `data` using Pydantic models for type safety and schema enforcement.
- **Extensibility**: Standalone module, callable by any UI, with output flexibility via the interface.

###### 3.2.3 Plugin System

- **Responsibility**: Implements specific problem types (addition, subtraction, etc.), returning `Problem` objects.
- **Interface (`interface.py`)**:
    - Defines `MathProblemPlugin` with:
        - `generate_problem() -> Problem`: Generates a `Problem` (svg, data) using initialized params for random
          generation.
        - `get_parameters() -> list[tuple[str, any, str]]`: Lists param names, defaults, and help text (classmethod).
    - `Problem` class: Uses Pydantic for validation, containing `svg` (string) and `data` (dict with `answer`).
- **Implementation (`plugins/*.py`)**:
    - Each plugin supports dual modes: random generation (via initialized params) or deterministic generation (via
      `data` from JSON, classmethod).
    - Example: `addition.py` uses initialized params for random operands or `data['operands']` for deterministic.
    - For addition, subtraction, and multiplication, SVG rendering uses vertical stacking (top operand above bottom,
      operator left of bottom, line under bottom).
- **Loading**: Uses `pkg_resources.iter_entry_points('mathtest.plugins')` from `pyproject.toml`.
- **Design Decisions**:
    - Plugins ignore unused params, ensuring flexibility; Pydantic validates `data` for deterministic mode.
    - SVG generation uses `svgwrite` for vector output with stacking for arithmetic problems.
- **Extensibility**: New plugins added via `pyproject.toml` entry points.

###### 3.2.4 Registry Module (`registry.py`)

- **Responsibility**: Manages plugin instances for lookup by name.
- **Design**: Dictionary-based registry, populated during plugin loading.
- **Extensibility**: Scales with plugin count, no changes needed for new types.

###### 3.2.5 Output Interface (`interface.py` and `output/pdf.py`)

- **Responsibility**: Defines an abstract interface for output generation, with `pdf.py` as the initial implementation.
- **Interface (`interface.py`)**:
    - Defines `OutputGenerator` with:
        - `generate(problems: list[Problem], params: dict[str, any]) -> None`: Produces output (e.g., PDF) from
          `Problem` objects and layout params (e.g., `--grid-cols`).
- **Implementation (`output/pdf.py`)**:
    - Uses `reportlab` to create PDFs with grid layouts, multi-page support, and answer keys based on
      `--questions-per-page`, `--num-tests`, etc.
- **Design Decisions**:
    - Interface-driven to allow future output types (e.g., HTML, DOCX) without changing the coordinator.
    - Pydantic validates layout params for consistency.
- **Extensibility**: New output types implemented by adding classes adhering to `OutputGenerator`.

##### 3.3 Data Flow

1. **CLI Parsing**: `main.py` collects flags and optional `--config`/`--json-input`, passing to
   `coordinator.generate_test()`.
2. **Coordination**:

- `load_plugins()` discovers and registers plugins.
- `merge_params()` combines inputs, skipping type flags if `--json-input` is set.
- `generate_problems()` calls `generate_problem()` using params or JSON `data`.
- `process_output()` delegates to the `OutputGenerator` interface (e.g., `pdf.py`) or saves JSON.

3. **Output**: PDF via interface, JSON with `data` only.

##### 3.4 Technology Stack

- **Language**: Python
- **Dependency Management**: UV with `pyproject.toml` (e.g., `typer`, `pyyaml`, `svgwrite`, `reportlab`, `pydantic`)
- **CLI**: Typer
- **Rendering**: SVG (`svgwrite`)
- **PDF**: `reportlab`
- **Validation**: Pydantic (for models, schemas, and params)
- **Testing**: pytest

##### 3.5 Design Decisions

- **Modularity**: CLI, coordinator, and output are distinct, ensuring UI and output independence.
- **Extensibility**: Entry points and interfaces support new plugins and output types.
- **Reproducibility**: JSON `data` drives deterministic SVG generation, excluding SVG from storage.
- **Performance**: Optimized SVG rendering and batched output assembly.
- **Testability**: Modules designed for unit testing with pytest.
- **Validation**: Pydantic integrates with Typer/FastAPI for consistent param validation and schema enforcement.

#### 4. Non-Functional Requirements

- **Performance**: Generate 100 problems in <5 seconds.
- **Scalability**: Support 10+ plugins.
- **Reliability**: Handle invalid inputs with clear errors; 99% pytest pass rate.
- **Maintainability**: PEP 8, >80% test coverage.
- **Extensibility**: Output interface and coordinator reusable for new UIs.

#### 5. Risks and Mitigations

- **Risk**: Entry point misconfiguration.
    - **Mitigation**: Log warnings, validate at startup.
- **Risk**: JSON `data` inconsistencies.
    - **Mitigation**: Use Pydantic schemas for validation.
- **Risk**: Output interface complexity.
    - **Mitigation**: Test with diverse layouts, plan for modular expansion.

#### 6. Review of Smells and Bad Practices

The design was reviewed against common Python/SWE antipatterns:

- **God Object**: Avoided by distributing responsibilities (e.g., coordinator delegates to interfaces, plugins handle
  generation).
- **Tight Coupling**: Loose coupling via interfaces and entry points; Pydantic models prevent direct dict manipulation.
- **Circular Imports**: Structure avoids cycles (e.g., `interface.py` imported one-way by plugins/coordinator).
- **Single Responsibility**: Each module has one primary role (e.g., coordinator coordinates, not renders).
- **Magic Numbers**: Defaults (e.g., `--clock-minute-interval 15`) defined in plugins, validated with Pydantic.
- **Error Handling**: Robust with Pydantic validation and logging, no silent failures.
- **Scalability/Performance**: Batched operations, no global state; entry points scale well.
- **Testability**: High, with isolated modules and Pydantic easing mock data.
- **Overall**: No major smells; design follows PEP 8, SOLID principles, and Python best practices (e.g., from
  Hitchhiker's Guide, Real Python).

#### 7. Implementation Phases / Units of Work

With this design, break into sequential units:

1. **Setup and Interfaces**: Configure `pyproject.toml`, implement `interface.py` (plugins, output, Pydantic models).
2. **Plugin Development**: Build `plugins/*.py` with Pydantic-validated generation logic.
3. **Registry and Coordinator**: Build `registry.py` and `coordinator.py`, integrating entry points and
   merging/validation.
4. **Output Implementation**: Develop `output/pdf.py` with layout features.
5. **CLI Integration**: Add `main.py` with Typer flags and coordinator calls.
6. **Testing and Validation**: Write pytest suites per module, validate JSON/PDF flows.
7. **Documentation**: Update README with usage and extension guides.

#### 8. Next Steps

- **Implementation**: Develop `mathtest/` modules based on this SDD, using the POC as a reference.
- **Review**: Conduct a design review to validate the architecture.
- **Testing**: Create pytest suites for each module.
- **Documentation**: Update `README.md` with setup and usage instructions.

