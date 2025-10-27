# Product Requirements Document (PRD) for MathTest

## 1. Product Overview

MathTest is a sophisticated command-line application engineered to facilitate the creation of customizable, printable
math worksheets primarily for elementary school students. It leverages a dual-plugin architecture: generation plugins to
produce diverse math problems (such as arithmetic operations and time-telling via analog clocks) and output plugins to
render the results in various formats. In the MVP, prioritize implementing generation plugins for addition, subtraction,
multiplication, division, and clock problems, alongside the "traditional-pdf" output plugin for generating PDFs with
structured layouts including titles, student metadata fields, scalable visual representations of problems, and an
optional enumerated answer key. JSON output is treated as a special-case output plugin that can coexist with others for
enhanced flexibility in saving and reproducing worksheets. The system emphasizes deterministic behavior for
reproducibility, comprehensive configurability through CLI flags and YAML files, and robust error handling to ensure a
seamless user experience. This design allows educators to generate tailored practice materials efficiently while
providing extensibility for developers to introduce new problem types or output formats without altering core logic.

### 1.1 Target Audience

- Educators and teachers who require quick generation of varied math drills with consistent formatting and answer keys.
- Parents and homeschoolers seeking reproducible worksheets for consistent practice sessions.
- Software developers or contributors interested in extending the tool with custom plugins for specialized problem sets
  or alternative output renderers, such as HTML or image-based formats.

### 1.2 Key Features

- **Generation Plugin Selection and Configuration**: Users can enable multiple generation plugins via separate CLI
  flags (e.g., `--addition`, `--subtraction`) and provide overrides for plugin-specific parameters (e.g.,
  `--addition-min-operand 0 --addition-max-operand 10`). This allows mixing problem types in a single worksheet, with
  problems interleaved in a deterministic manner when seeds are applied.
- **Output Plugin Selection and Configuration**: Specify one or more output plugins using the repeatable
  `--output-plugin <name>` flag (e.g., `--output-plugin traditional-pdf --output-plugin json`). Each can have dynamic
  overrides (e.g., `--traditional-pdf-columns 4 --traditional-pdf-margin-inches 0.75`). JSON output is compatible with
  multiple selections and handles serialization of problem data for later reproduction.
- **Worksheet Generation Capabilities**: Produce worksheets with configurable problems per test (via
  `--problems-per-test`, default 10) and multiple tests (via `--test-count`, default 1). Problems are rendered
  visually (e.g., vertical arithmetic stacks or analog clock faces) with space for student answers.
- **Reproducibility and Persistence**: Support JSON input for exact recreation of worksheets (via `--json-input`) and
  JSON output for saving generated content (integrated as an output plugin but allowable alongside others).
- **Configuration Flexibility**: Merge settings from plugin defaults, YAML files (with sections for common,
  problem-plugins, and output-plugins), and CLI overrides, ensuring CLI takes precedence.
- **Logging and Error Handling**: Implement structured logging for all key operations (e.g., config merging, plugin
  instantiation, generation steps) and provide descriptive, user-friendly error messages for issues like invalid
  parameters or plugin conflicts.
- **Help and Discoverability**: Dynamically generate CLI help with grouped panels detailing available plugins, their
  parameters, descriptions, defaults, and types for intuitive usage.

### 1.3 Non-Functional Requirements

- **Performance**: Ensure generation and rendering for worksheets up to 100 problems complete in under 5 seconds on
  standard hardware, with efficient scaling for multiple tests.
- **Usability**: The CLI should be intuitive, with validation for conflicts (e.g., multiple non-compatible outputs if
  future plugins require it) and clear feedback; help text should include examples of flag usage without code snippets.
- **Reliability**: Use immutable data structures to prevent unintended modifications; achieve test coverage exceeding
  85% across unit and integration tests; handle edge cases like zero problems, invalid bounds, or missing configs
  gracefully without crashes.
- **Security**: Employ safe loading for YAML and JSON to mitigate injection risks; restrict plugins to local execution
  without network or file system vulnerabilities.
- **Compatibility**: Target Python 3.12+ environments; ensure cross-platform consistency in rendering (e.g., PDF fonts
  and SVG handling).
- **Maintainability**: Modular components with entry points for plugins; separate test packages for unit (isolated
  component checks) and integration (end-to-end workflows); adherence to clean code practices like DRY, SRP, and
  meaningful naming.

## 2. Functional Requirements

### 2.1 CLI Interface

- **Invocation**: Support `mathtest generate` explicitly, but allow implicit execution when flags are provided
  directly (e.g., `mathtest --addition --problems-per-test 5`).
- **Generation Flags**: Enable plugins with separate flags (e.g., `--addition` to include addition problems); provide
  overrides as `--<plugin-name>-<param-name>` (e.g., `--clock-minute-interval 15`). Distribute problems across enabled
  plugins proportionally.
- **Output Flags**: Use repeatable `--output-plugin <name>` for selection (e.g., `--output-plugin traditional-pdf`);
  overrides as `--<output-name>-<param-name>` (e.g., `--traditional-pdf-answer-key true`). Allow multiple, but
  special-case JSON for compatibility.
- **General Flags**: `--problems-per-test <int>` (problems per worksheet, default 10), `--test-count <int>` (number of
  worksheets, default 1), `--config <path>` (YAML file), `--json-input <path>` (for reproduction).
- **Validation and Feedback**: Error on invalid combinations (e.g., negative counts, bounds mismatches); provide
  descriptive messages like "min-operand must be <= max-operand".
- **Help System**: Grouped panels (e.g., "Problem Plugins" listing enables and descriptions, "Traditional-Pdf Options"
  detailing parameters like columns with defaults and types).

### 2.2 Problem Generation

- **Plugins**:
    - Addition/Subtraction/Multiplication: Vertical stacked operands with operator and underline for answers; support
      min/max operands, allow-negative-result for subtraction.
    - Division: Long division format with quotient and remainder.
    - Clock: Analog clock with hands; configurable minute intervals, accurate-hour, 24-hour mode.
- **Generation Logic**: For random mode, use seeded random for operands/hands; interleave types deterministically across
  tests. For reproduction, parse JSON and delegate to plugins' from_data methods.
- **Multi-Test Support**: Generate independent sets for each test count, applying the same config.
- **Configuration Extraction**: Plugins receive the full unified dict and pull defaults + common +
  problem-plugins[<name>].

### 2.3 Output Rendering

- **Plugins**: "traditional-pdf" renders to PDF with configurable margins (default 0.75 inches), columns (default 4),
  font sizes (title 20, answers 12), problem spacing (0.35 inches), and toggles like include_answers (default False),
  include_student_header (default True).
- **Multi-Output**: Invoke all selected; JSON serializes problem type/data (e.g., operands, answer) in a list,
  compatible with multi-output runs.
- **Rendering Details**: Scale SVGs to fit columns without distortion; distribute problems evenly with vertical spacing;
  add title centered, student fields with underlines, and answer key as numbered list if enabled.
- **Configuration Extraction**: Outputs receive full unified dict, pulling defaults + common + output-plugins[<name>].

### 2.4 Configuration

- **YAML Structure**: Top-level keys: common, problem-plugins (mapping plugin names to params), output-plugins (
  similar).
- **Merging Process**: Start with plugin-provided defaults; apply common; then specific sections; normalize keys (hyphen
  to snake); validate post-merge.
- **Unified Dict**: Passed to all plugins for self-extraction, ensuring consistency.

### 2.5 Plugins

- **Generation Plugins**: Implement protocol with name, parameters (e.g., min-operand: int default 0, description "
  Minimum operand value"), generate_problem (random SVG/data), generate_from_data (deterministic).
- **Output Plugins**: Similar protocol; generate renders to file based on params like path.
- **Entry Points**: mathtest.generation_plugins for generation; mathtest.output_plugins for outputs.
- **Extensibility**: Plugins define unique params; CLI/help auto-adapts.

## 3. User Stories

- As an educator, I can enable addition and clock plugins, set problems-per-test to 20 and test-count to 3, choose
  traditional-pdf with custom columns, and add JSON output to generate and save multiple worksheets.
- As a parent, I can load a JSON input to reproduce exact worksheets across tests, applying the same output plugins.
- As a developer, I can create a new generation plugin with custom params and an output plugin for CSV, integrating via
  entry points with dynamic CLI support.

## 4. Assumptions and Constraints

- Integer operands only; JSON output always multi-compatible even if other outputs are selected.
- Single language (English); no advanced rendering like interactivity.
- CLI-only; assume users have basic command-line familiarity.

## 5. Success Metrics

- Worksheets visually and functionally match configurations with high fidelity.
- Error-free reproduction from JSON across multiple tests.
- Test coverage >85%; positive usability in CLI interactions.
