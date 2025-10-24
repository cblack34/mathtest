"""End-to-end tests for the Typer CLI introduced in MVP Phase 5."""

from __future__ import annotations

import json
import random
from pathlib import Path

from click.testing import Result
from typer.testing import CliRunner

from mathtest.main import _normalize_argv, app


def _invoke(runner: CliRunner, args: list[str]) -> Result:
    """Invoke the CLI replicating entry-point argument normalization."""

    return runner.invoke(app, _normalize_argv(args))


def test_cli_generates_pdf_and_json(tmp_path: Path) -> None:
    """CLI should generate both PDF and JSON artifacts in a single run."""

    runner = CliRunner()
    pdf_path = tmp_path / "worksheet.pdf"
    json_path = tmp_path / "worksheet.json"

    result = _invoke(
        runner,
        [
            "--addition",
            "--subtraction",
            "--addition-random-seed",
            "1",
            "--subtraction-random-seed",
            "1",
            "--addition-min-operand",
            "2",
            "--addition-max-operand",
            "2",
            "--subtraction-min-operand",
            "3",
            "--subtraction-max-operand",
            "3",
            "--output",
            str(pdf_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert pdf_path.exists()

    serialized = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(serialized) == 10
    assert {entry["type"] for entry in serialized} == {"addition", "subtraction"}

    replay_pdf = tmp_path / "replay.pdf"
    replay_result = _invoke(
        runner,
        [
            "--json-input",
            str(json_path),
            "--output",
            str(replay_pdf),
        ],
    )

    assert replay_result.exit_code == 0, replay_result.output
    assert replay_pdf.exists()

    override_pdf = tmp_path / "override.pdf"
    override_json = tmp_path / "override.json"
    override_result = _invoke(
        runner,
        [
            "--addition",
            "--addition-random-seed",
            "2",
            "--addition-min-operand",
            "4",
            "--addition-max-operand",
            "4",
            "--total-problems",
            "3",
            "--output",
            str(override_pdf),
            "--json-output",
            str(override_json),
        ],
    )

    assert override_result.exit_code == 0, override_result.output
    assert override_pdf.exists()

    override_serialized = json.loads(override_json.read_text(encoding="utf-8"))
    assert len(override_serialized) == 3
    assert {entry["type"] for entry in override_serialized} == {"addition"}


def test_cli_requires_plugin_without_json(tmp_path: Path) -> None:
    """CLI should error when neither plugin flags nor JSON input is provided."""

    runner = CliRunner()
    result = _invoke(
        runner,
        [
            "--output",
            str(tmp_path / "unused.pdf"),
        ],
    )

    assert result.exit_code != 0
    assert "Select at least one plugin flag" in result.output


def test_cli_mixed_plugins_are_interleaved(tmp_path: Path) -> None:
    """Runs with multiple plugins should interleave problem types."""

    runner = CliRunner()
    random.seed(0)

    json_path = tmp_path / "mixed.json"
    result = _invoke(
        runner,
        [
            "--addition",
            "--subtraction",
            "--addition-random-seed",
            "1",
            "--subtraction-random-seed",
            "1",
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0, result.output

    serialized = json.loads(json_path.read_text(encoding="utf-8"))
    types = [entry["type"] for entry in serialized]

    assert len(types) == 10
    assert "addition" in types and "subtraction" in types
    assert any(left != right for left, right in zip(types, types[1:]))


def test_cli_inserts_generate_prefix_for_flags(tmp_path: Path) -> None:
    """Providing only flags should still execute the generate command."""

    runner = CliRunner()
    pdf_path = tmp_path / "implicit.pdf"

    result = _invoke(
        runner,
        [
            "--addition",
            "--addition-random-seed",
            "42",
            "--total-problems",
            "1",
            "--output",
            str(pdf_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert pdf_path.exists()
