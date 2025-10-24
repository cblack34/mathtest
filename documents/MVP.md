### Implementation Plan for MVP with Addition and Subtraction Problems

This plan focuses on a Minimal Viable Product (MVP) implementing only addition and subtraction problems, as specified.
The MVP will validate the core architecture (plugin loading, coordination, CLI, JSON I/O, PDF output) with a reduced
scope, ensuring quick iteration and early feedback. It follows the SDD's units of work but prioritizes essentials,
aiming for a functional CLI that generates simple tests. Estimated timeline: 1-2 weeks for a solo developer using Codex,
assuming 20-30 hours/week.

#### MVP Scope

- **Included**: Addition and subtraction plugins; basic CLI flags (e.g., `--addition`, `--subtraction`,
  `--total-problems`, `--output`); optional YAML; JSON input/output; PDF assembly with answer keys (no advanced layout
  like `--grid-cols` initially).
- **Excluded**: Multiplication, division, clock-reading; advanced formatting (`--questions-per-page`, `--num-tests`,
  etc.); full error handling; comprehensive tests (focus on smoke tests).
- **Success Criteria**: Run `mathtest generate --addition --total-problems 5 --output test.pdf` to produce a PDF with 5
  addition problems and answers; reproduce via JSON.
- **Assumptions**: Use Python 3.14, UV for dependencies, Codex for code generation/review, pytest for basics.

#### Phase 1: Setup and Foundations (1-2 days)

- **Tasks**:
    - Create repo structure: `mathtest/`, `tests/`, `pyproject.toml`.
    - Configure `pyproject.toml`: Add dependencies (`typer`, `pyyaml`, `svgwrite`, `fpdf2`, `pydantic`), entry
      points for addition/subtraction (e.g., `addition = mathtest.plugins.addition:AdditionPlugin`).
    - Implement `interface.py`: Define Protocols and Pydantic models as per latest artifact.
    - Use Codex to generate/review stubs.
- **Milestone**: Empty project runs with `uv sync` and `pytest` (no tests yet).
- **Risks**: Dependency conflicts—mitigate by pinning versions in `pyproject.toml`.

#### Phase 2: Plugin Implementation (2-3 days)

- **Tasks**:
    - Create `plugins/addition.py` and `plugins/subtraction.py`: Implement Protocol methods (classmethods for
      `get_parameters` and `generate_from_data`, instance `generate_problem`).
    - Support random generation (e.g., add operands within defaults like max-operand=10) and deterministic from `data`.
    - Use `svgwrite` for SVG with vertical stacking for arithmetic problems (top operand above bottom, operator left,
      line under).
    - Validate params/`data` with Pydantic inside methods.
    - Document init policy (optional params dict).
- **Milestone**: Manually test plugins (e.g., `plugin = AdditionPlugin(params); problem = plugin.generate_problem()`
  yields valid `Problem` with stacked SVG).
- **Risks**: SVG rendering issues—start with text-only for MVP.

#### Phase 3: Registry and Coordinator (3-4 days)

- **Tasks**:
    - Implement `registry.py`: Dictionary for plugin lookup, populated via entry points.
    - Implement `coordinator.py`: Functions for loading plugins, merging params (defaults + YAML + CLI, override with
      JSON), generating problems (loop over types or JSON data), saving JSON, delegating to output.
    - Handle JSON input override: If provided, use `generate_from_data` classmethod per entry, ignoring type flags.
    - Use Pydantic for param merging/validation.
- **Milestone**: Coordinator can generate a list of `Problem` objects from mock inputs, including JSON reproduction.
- **Risks**: Param merging complexity—test edge cases (no YAML, JSON override) early.

#### Phase 4: Output Implementation (1-2 days)

- **Tasks**:
    - Implement `output/pdf.py`: Basic PDF generation with `fpdf2`, embedding SVGs and adding answer keys from
      `Problem.data['answer']`.
    - Keep layout simple (e.g., vertical list, no grid for MVP).
    - Validate inputs with Pydantic.
- **Milestone**: Coordinator can delegate to PDF output, producing a file with stacked problems.
- **Risks**: Library quirks—use simple canvas for MVP.

#### Phase 5: CLI Integration and Basic Testing (2-3 days)

- **Tasks**:
    - Implement `main.py`: Typer command with dynamic flags from `get_parameters` (classmethod), call coordinator.
    - Support optional `--config`, `--json-input`/`--output`, basic flags.
    - Add smoke tests in `tests/` (e.g., `test_plugins.py` for generation, `test_coordinator.py` for merging/JSON).
    - Use `pytest` with coverage.
- **Milestone**: Full MVP run: CLI generates PDF/JSON for addition/subtraction, reproduces from JSON.
- **Risks**: Dynamic flags in Typer—test help menu and parsing.

#### Phase 6: Review, Polish, and Deployment (1 day)

- **Tasks**:
    - Review against PRD/SDD: Ensure no smells (e.g., run mypy, black for formatting).
    - Update `README.md`: Installation, usage examples.
    - Commit to Git, tag MVP v0.1.
- **Milestone**: MVP deployable via PyPI or local install.
- **Risks**: Scope creep—stick to addition/subtraction only.

#### Overall Timeline and Resources

- **Total**: 9-15 days, assuming iterative Codex use for generation/review.
- **Dependencies**: UV, Codex for code, Git for versioning.
- **Monitoring**: Track progress via Git issues or a simple Kanban (e.g., To Do, In Progress, Done).
- **Post-MVP**: Add remaining plugins, advanced features based on feedback.

This plan ensures a focused MVP, validating the architecture early. Let me know if you'd like to adjust timelines or add
tools!