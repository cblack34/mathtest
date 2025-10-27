# MVP Implementation Plan for MathTest

## Phase 1: Setup and Interfaces

- Set up pyproject.toml with production dependencies (pydantic, typer, pyyaml, reportlab, svglib, svgwrite) and dev
  tools (pytest, mypy, black, ruff, pydocstyle).
- Configure structured logging using logging module at module levels.
- Define protocols for MathProblemPlugin and OutputGenerator, along with supporting Pydantic models like
  ParameterDefinition and Problem.

## Phase 2: Registries and Utilities

- Implement separate registry classes for generation (loading from mathtest.generation_plugins) and outputs (from
  mathtest.output_plugins), including caching, validation against protocols, and logging.
- Develop config merging utility to produce unified dict from defaults, YAML, and CLI, with key normalization and
  precedence handling.
- Create svg_utils module for shared SVG rendering functions (e.g., vertical arithmetic layout with consistent
  dimensions, fonts, and paddings).

## Phase 3: Generation Plugins

- Implement addition, subtraction, multiplication, division, and clock plugins: Define Pydantic config models with
  aliases/validators, extract from unified dict, generate random/deterministic problems with SVG and immutable data.
- Add logging for init, extraction, and generation; handle edges like zero quantity or invalid data.
- Write unit tests in tests/unit/plugins (e.g., seeded determinism, SVG structure assertions, validation errors).

## Phase 4: Coordinator

- Build models like GenerationRequest (incorporating problems-per-test, test-count).
- Implement central merging to unified dict, plugin selection/instantiation, multi-test generation with interleaving (
  hashlib for shuffle seeds), and JSON reproduction.
- Add logging for each phase; specific error handling with user messages.
- Develop integration tests in tests/integration (e.g., full generation flows with mocked plugins).

## Phase 5: Output Plugin

- Implement "traditional-pdf": Pydantic config with parameters (e.g., margin_inches gt 0), extract from unified, use
  Platypus for title/header/problems/answers, handle scaling/tolerance/multi-test paging.
- Special-case JSON as output plugin: Serialize problems per test, ensure multi-compatibility without conflicts.
- Include logging for rendering; tests in tests/unit/output (layout assertions with mocks) and tests/integration (file
  outputs).

## Phase 6: CLI Integration

- Use custom TyperCommand for dynamic flag generation: Separate generation enables, repeatable --output-plugin,
  overrides from get_parameters.
- Parse YAML/JSON safely, build unified config, invoke coordinator, handle multi-outputs.
- Validate inputs (e.g., positive counts); echo success with details.
- Tests in tests/integration/cli (end-to-end with CliRunner, covering flag combos, help output, errors).

## Phase 7: Testing and Documentation

- Ensure >85% coverage via pytest --cov; organize into unit (isolated, fast) and integration (holistic, file-based)
  packages.
- Add Google-style docstrings comprehensively, covering args/returns/raises/examples.
- Create README with detailed CLI usage examples, plugin extension instructions, and configuration YAML samples.
