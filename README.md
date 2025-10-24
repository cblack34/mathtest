# Mathtest

Mathtest generates printable elementary math worksheets featuring vertically
stacked addition and subtraction problems. The implementation follows the
architecture defined in the project documents, using plugins for problem
generation and a PDF output backend for distribution-ready worksheets.

## Prerequisites

- [Python 3.14](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) for dependency management and task
  execution

Clone the repository and install the dependencies using uv:

```bash
uv sync
```

## Usage

Mathtest exposes a Typer-powered CLI. Generate a worksheet that mixes addition
and subtraction problems while exporting both PDF and JSON artifacts:

```bash
uv run mathtest generate \
  --addition \
  --subtraction \
  --total-problems 10 \
  --output worksheets/mixed.pdf \
  --json-output worksheets/mixed.json
```

Replay a worksheet using a previously captured JSON payload:

```bash
uv run mathtest generate \
  --json-input worksheets/mixed.json \
  --output worksheets/mixed-replay.pdf
```

Additional configuration, such as operand ranges or RNG seeds, is surfaced via
plugin-specific flags (for example `--addition-min-operand`). You can also pass
a YAML configuration file with `--config path/to/settings.yaml`.

### PDF layout configuration

When using a YAML configuration file you can fine-tune the PDF layout. The
`margin_inches` and `problem_spacing_inches` options continue to control the
outer margins and vertical spacing. Two new parameters extend the layout model:

- `columns` (default: 4) determines how many problems appear across each row.
- `column_spacing_inches` sets the gutter between columns (default: 0.25).

These values mirror the fields on `PdfOutputParams` and apply uniformly across
the generated worksheet and answer key pages.

## Development

The repository includes formatting, static analysis, and test tooling. Run
these commands with uv to keep contributions aligned with Phase 6 of the MVP:

```bash
# Format code
uv run black .

# Type checking
uv run mypy src tests

# Test suite
uv run pytest
```

## Project Documents

Architectural and planning documents that guided the MVP implementation:

- `documents/PRD.md`
- `documents/SDD.md`
- `documents/MVP.md`
