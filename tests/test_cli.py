"""End-to-end tests for the Typer CLI introduced in MVP Phase 5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import Result
from typer.testing import CliRunner

import yaml

from mathtest.coordinator import (
    Coordinator,
    GenerationRequest,
    ParameterSet,
    PluginRequest,
)
from mathtest.main import _PLUGIN_PARAMETERS, _normalize_argv, app


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


def test_cli_mixed_plugins_are_interleaved(tmp_path: Path) -> None:
    """Runs with multiple plugins should interleave problem types."""

    runner = CliRunner()
    args = [
        "--addition",
        "--subtraction",
        "--addition-random-seed",
        "1",
        "--subtraction-random-seed",
        "1",
    ]

    first_path = tmp_path / "mixed.json"
    first_result = _invoke(
        runner,
        [
            *args,
            "--json-output",
            str(first_path),
        ],
    )
    assert first_result.exit_code == 0, first_result.output

    first_serialized = json.loads(first_path.read_text(encoding="utf-8"))

    first_types = [entry["type"] for entry in first_serialized]
    assert len(first_types) == 10
    assert "addition" in first_types and "subtraction" in first_types
    assert any(left != right for left, right in zip(first_types, first_types[1:]))

    manual_request = GenerationRequest(
        plugin_requests=[
            PluginRequest(name="addition", quantity=5),
            PluginRequest(name="subtraction", quantity=5),
        ],
        cli_parameters=ParameterSet(
            plugins={
                "addition": {"random-seed": 3},
                "subtraction": {"random-seed": 3},
            }
        ),
    )

    manual_first = Coordinator().generate(manual_request)
    manual_second = Coordinator().generate(manual_request)

    manual_types_first = [entry.problem_type for entry in manual_first.serialized]
    manual_types_second = [entry.problem_type for entry in manual_second.serialized]

    assert manual_types_first == manual_types_second


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


def test_cli_answer_key_flag_controls_pdf_section(tmp_path: Path) -> None:
    """The answer key should only render when the dedicated flag is provided."""

    runner = CliRunner()
    base_args = [
        "--addition",
        "--addition-random-seed",
        "7",
        "--total-problems",
        "1",
    ]

    without_path = tmp_path / "without.pdf"
    without_result = _invoke(
        runner,
        [
            *base_args,
            "--output",
            str(without_path),
        ],
    )

    assert without_result.exit_code == 0, without_result.output
    assert without_path.exists()
    assert b"Answer Key" not in without_path.read_bytes()

    with_path = tmp_path / "with.pdf"
    with_result = _invoke(
        runner,
        [
            *base_args,
            "--answer-key",
            "--output",
            str(with_path),
        ],
    )

    assert with_result.exit_code == 0, with_result.output
    assert with_path.exists()
    assert b"Answer Key" in with_path.read_bytes()


def test_cli_generates_clock_problems(tmp_path: Path) -> None:
    """Clock plugin flags should integrate with the CLI surface."""

    runner = CliRunner()
    json_path = tmp_path / "clock.json"

    result = _invoke(
        runner,
        [
            "--clock",
            "--clock-random-seed",
            "5",
            "--clock-minute-interval",
            "5",
            "--clock-accurate-hour",
            "True",
            "--total-problems",
            "4",
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json_path.exists()

    serialized = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(serialized) == 4
    assert {entry["type"] for entry in serialized} == {"clock"}

    first = serialized[0]["data"]
    assert first["minute"] % first["minute_interval"] == 0
    assert first["answer"].endswith(f":{first['minute']:02d}")


def test_cli_help_sections_group_plugins() -> None:
    """Help output should summarize plugins and isolate override options."""

    runner = CliRunner()
    result = _invoke(runner, ["generate", "--help"])

    assert result.exit_code == 0, result.stdout

    output = result.stdout
    assert "KWARGS" not in output
    assert "Plugins" in output
    assert "Generate vertically stacked addition problems" in output

    plugins_start = output.index("Plugins")
    options_block = output[:plugins_start]
    assert "--addition" not in options_block
    assert "--addition-min-operand" not in options_block

    assert "Addition Options" in output
    assert "--addition-min-operand" in output


def test_cli_top_level_help_is_default() -> None:
    """Requesting help without a command should show application help."""

    runner = CliRunner()
    result = _invoke(runner, ["--help"])

    assert result.exit_code == 0, result.stdout
    assert "Usage:" in result.stdout
    assert "COMMAND [ARGS]" in result.stdout
    assert "Commands" in result.stdout
    assert "generate" in result.stdout
    assert "write-config" in result.stdout


def test_write_config_command_generates_template(tmp_path: Path) -> None:
    """The write-config command should emit a comprehensive YAML template."""

    runner = CliRunner()
    destination = tmp_path / "settings.yaml"

    result = runner.invoke(app, ["write-config", "--output", str(destination)])

    assert result.exit_code == 0, result.output
    assert destination.exists()

    content = destination.read_text(encoding="utf-8")
    template = yaml.safe_load(content)

    assert isinstance(template, dict)
    assert "common" in template
    assert "plugins" in template

    common_defaults = template["common"]
    shared_names: set[str] | None = None
    for definitions in _PLUGIN_PARAMETERS.values():
        names = {definition.name for definition in definitions}
        shared_names = names if shared_names is None else shared_names & names

    if shared_names:
        for name in shared_names:
            expected: Any | None = None
            for definitions in _PLUGIN_PARAMETERS.values():
                for definition in definitions:
                    if definition.name == name:
                        expected = definition.default
                        break
                if expected is not None:
                    break
            assert name in common_defaults
            assert common_defaults[name] == expected

    plugin_defaults = template["plugins"]
    for plugin_name, definitions in _PLUGIN_PARAMETERS.items():
        assert plugin_name in plugin_defaults
        plugin_section = plugin_defaults[plugin_name]
        for definition in definitions:
            assert plugin_section[definition.name] == definition.default
