### Updated Product Requirements Document (PRD) for Mathtest

#### 1. Overview

**Product Name**: Mathtest  
**Version**: 0.1  
**Date**: October 23, 2025  
**Objective**: Mathtest is a Python-based application designed to generate customizable math tests with a plugin
architecture, initially supporting addition, subtraction, multiplication, division, and clock-reading problems. It
provides a Typer-based CLI with optional YAML configuration, reproducible tests via JSON output, and advanced PDF
formatting options, built for extensibility to a new UI (e.g., FastAPI) without altering core coordination logic.

#### 2. Target Audience

- **Educators and Teachers**: Create tailored tests with specific layouts, answer keys, and problem types.
- **Students**: Practice with reproducible or custom tests.
- **Developers**: Extend with new plugins using entry points.

#### 3. Key Features

##### 3.1 Core Functionality

- **Plugin-Based Problem Generation**:
    - Supports full-named plugins: addition, subtraction, multiplication, division, clock-reading.
    - Loaded dynamically via `pyproject.toml` entry points within the `mathtest` package.
    - Each plugin returns a `Problem` object with `svg` (resizable output) and `data` (problem state, including `answer`
      for answer keys).
    - Plugins support generating SVG from a provided `data` dict (e.g., `{"operands": [5, 3], "answer": 8}` for
      addition) without random generation, enabling exact reproduction from JSON input.
    - For addition, subtraction, and multiplication problems, the SVG rendering must use vertical stacking: the top
      operand above the bottom operand, with the operator to the left of the bottom operand, and a horizontal line under
      the bottom operand (e.g., like "5 + 9" stacked as in the provided PDF).
- **CLI Interface**:
    - Built with Typer, using flag-based type selection (e.g., `--addition`, `--subtraction`).
    - Options include `--total-problems`, `--questions-per-page`, `--num-tests`, `--grid-cols`, `--student-name`,
      `--date`, `--output`, and `--answer-key`.
    - Supports optional YAML configuration (`--config`) with `common` and per-plugin sections, overridden by CLI flags (
      e.g., `--addition-max-operand`).
- **PDF Assembly**:
    - Assembles SVGs into a PDF with customizable layout (grid, pages, answer keys) using a library like `reportlab`.

##### 3.2 Reproducible Tests

- **JSON Output**:
    - `--json-output <filename>` saves a JSON file with `data` objects from each `Problem`, excluding SVG data (e.g.,
      `{"type": "addition", "data": {"operands": [5, 3], "operator": "+", "answer": 8}}`).
- **JSON Input**:
    - `--json-input <filename>` recreates the exact test from JSON by passing the `data` dict to plugins, which generate
      corresponding SVGs without random generation. JSON input overrides type flags.
- **Custom Test Creation**:
    - Users edit JSON to craft custom tests (e.g., specific operands or clock times), with plugins validating `data`.

##### 3.3 Parameter Management

- **Dynamic CLI Flags**:
    - Plugins define parameters (e.g., `max-operand`, `min-operand`) via `get_parameters`, generating flags like
      `--addition-max-operand`.
    - Clock-reading uses `--clock-12-hour` (default), `--clock-24-hour`, and `--clock-minute-interval <interval>` (
      default 15, option 5).
- **Optional YAML Configuration**:
    - Nested structure: `common` for global defaults, per-plugin sections for overrides (e.g.,
      `common: {max-operand: 10}`, `addition: {max-operand: 12}`).
    - CLI flags take precedence; YAML is optional and provides a convenient default setup if provided.
- **Parameter Handling**:
    - Full param dict passed to plugins, ignored if unused, ensuring flexibility. Plugins use `data` from JSON input to
      deterministic SVG generation.

##### 3.4 Extensibility and Formatting

- **Future UI Readiness**:
    - Coordination of test building (e.g., plugin invocation, problem collection) is separated from the CLI module,
      allowing easy replacement with a new UI (e.g., FastAPI) without modifying core logic.
- **Advanced Formatting**:
    - `--questions-per-page`, `--num-tests`, `--grid-cols` for layout; `--student-name`, `--date` for headers;
      `--answer-key` for solutions.

#### 4. Architecture

##### 4.1 Directory Structure

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

##### 4.2 Component Breakdown

- **Plugins**: In `mathtest/plugins/`, return `Problem` objects, define params via `get_parameters`, loaded via entry
  points. For arithmetic plugins, SVGs use vertical stacking.
- **CLI Module (`main.py`)**:
    - Handles Typer command definition, parses CLI flags, and calls the coordinator.
    - Keeps UI-specific logic separate from test generation.
- **Coordinator Module (`coordinator.py`)**:
    - Contains core logic for loading plugins, merging parameters, generating problems, and assembling PDFs/JSON.
    - Reusable layer, independent of CLI, for future UI integration.
- **Registry (`registry.py`)**:
    - Manages plugin instances, queried by type name.
- **Interface (`interface.py`)**:
    - Defines `MathProblemPlugin` with `generate_problem` (returns `Problem` based on params or `data`) and
      `get_parameters`.
- **PDF Layout**: Uses `reportlab` to implement `--grid-cols`, `--questions-per-page`, etc.

##### 4.3 Data Flow

1. CLI input sets flags (e.g., `--addition`, `--num-problems`).
2. Coordinator loads plugins, merges params, generates problems, produces output.
3. PDF assembled with layout options, recreated from JSON if `--json-input` set.

##### 4.4 Technology Stack

- **Language**: Python
- **Dependency Management**: UV with `pyproject.toml` (e.g., `typer`, `pyyaml`, `svgwrite`, `reportlab`, `pydantic`)
- **CLI**: Typer
- **Rendering**: SVG (`svgwrite`)
- **PDF**: `reportlab`
- **Validation**: Pydantic (for models, schemas, and params)
- **Testing**: pytest

#### 5. Non-Functional Requirements

- **Performance**: 100 problems in <5 seconds.
- **Scalability**: Support 10+ plugins.
- **Reliability**: Handle invalid inputs with clear errors; 99% pytest pass rate.
- **Maintainability**: PEP 8, >80% test coverage.
- **Extensibility**: Output interface and coordinator reusable for new UIs.

#### 6. Future Considerations

- **Advanced Features**: Graphing, multi-language support.
- **Deployment**: PyPI package with UV.

#### 7. Risks and Mitigations

- **Risk**: Entry point misconfiguration.
    - **Mitigation**: Log warnings, validate at startup.
- **Risk**: JSON `data` inconsistencies.
    - **Mitigation**: Use Pydantic schemas for validation.
- **Risk**: PDF layout issues.
    - **Mitigation**: Test with large grids, multi-page tests.

#### 8. Next Steps

- **Implementation**: Develop `mathtest/` modules based on the SDD, using the POC as a reference.
- **Review**: Conduct a design review to validate the architecture.
- **Testing**: Create pytest suites for each module.
- **Documentation**: Update `README.md` with setup and usage instructions.

