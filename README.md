# Mathtest

Mathtest is a plugin-driven tool for generating printable math tests. The MVP focuses on addition and subtraction while laying the groundwork for more problem types and output formats.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

The command installs runtime and development dependencies into a local virtual environment.

## Common Commands

Run the (placeholder) CLI:

```bash
uv run mathtest --help
```

Run the test suite once tests exist:

```bash
uv run pytest
```

## Project Structure

See `documents/SDD.md` for the full architecture. The key modules include:

- `mathtest.main`: Typer-based CLI entry point.
- `mathtest.coordinator`: Coordinates plugin execution and output.
- `mathtest.plugins`: Addition and subtraction plugins (stubs for now).
- `mathtest.output`: Output generators such as PDF (stub).

Refer to `documents/MVP.md` for the development phases and scope.
