"""End-to-end tests for the Typer CLI introduced in MVP Phase 5."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mathtest.main import app


def test_cli_generates_pdf_and_json(tmp_path: Path) -> None:
    """CLI should generate both PDF and JSON artifacts in a single run."""

    runner = CliRunner()
    pdf_path = tmp_path / "worksheet.pdf"
    json_path = tmp_path / "worksheet.json"

    result = runner.invoke(
        app,
        [
            "generate",
            "--addition",
            "1",
            "--subtraction",
            "1",
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
    assert len(serialized) == 2
    assert {entry["type"] for entry in serialized} == {"addition", "subtraction"}

    replay_pdf = tmp_path / "replay.pdf"
    replay_result = runner.invoke(
        app,
        [
            "generate",
            "--json-input",
            str(json_path),
            "--output",
            str(replay_pdf),
        ],
    )

    assert replay_result.exit_code == 0, replay_result.output
    assert replay_pdf.exists()
