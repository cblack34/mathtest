"""Command-line interface for Mathtest."""

from __future__ import annotations

import typer

app = typer.Typer(help="Generate customizable math tests.")


@app.callback()
def main() -> None:
    """Placeholder CLI callback to be expanded in future phases."""


if __name__ == "__main__":
    app()
