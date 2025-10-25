"""Command-line interface implementing MVP Phase 5 for Mathtest."""

from __future__ import annotations

import inspect
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import click
import typer
import yaml
from pydantic import ValidationError
from typer.main import TyperCommand
from typer.models import CommandInfo

from .coordinator import (
    Coordinator,
    GenerationRequest,
    ParameterSet,
    PluginRequest,
    SerializedProblem,
)
from .interface import ParameterDefinition
from .output import PdfOutputGenerator
from .registry import PluginRegistry


app = typer.Typer(help="Generate printable math worksheets from the terminal.")

_REGISTRY = PluginRegistry()


def _collect_plugin_parameters() -> dict[str, list[ParameterDefinition]]:
    """Gather parameter metadata from each registered plugin.

    Returns:
        Mapping of plugin names to the parameter definitions they expose.
    """

    parameters: dict[str, list[ParameterDefinition]] = {}
    for name in _REGISTRY.names():
        plugin_cls = _REGISTRY.get_class(name)
        try:
            definitions = list(plugin_cls.get_parameters())
        except Exception as exc:  # pragma: no cover - plugin misbehavior
            msg = f"Unable to load parameter definitions for '{name}'"
            raise RuntimeError(msg) from exc
        parameters[name] = definitions
    return parameters


_PLUGIN_PARAMETERS = _collect_plugin_parameters()

_CLICK_TYPE_ALIASES: dict[str, click.ParamType | type[Any]] = {
    "int": int,
    "float": float,
    "bool": click.BOOL,
    "str": str,
}

_CLICK_TYPE_TYPES: dict[type[Any], click.ParamType | type[Any]] = {
    bool: click.BOOL,
    int: int,
    float: float,
    str: str,
}


def _option_storage_key(plugin_name: str, parameter_name: str) -> str:
    """Create the internal storage key for a plugin CLI option.

    Args:
        plugin_name: Name of the plugin that owns the parameter.
        parameter_name: Parameter identifier provided by the plugin.

    Returns:
        The key Typer uses to store the parsed option value.
    """

    return f"{plugin_name}_{parameter_name.replace('-', '_')}"


def _load_parameter_set(config_path: Path | None) -> ParameterSet:
    """Load YAML configuration values into a :class:`ParameterSet`.

    Args:
        config_path: Optional path to the YAML file provided through ``--config``.

    Returns:
        A parameter set containing configuration sourced from the YAML file.

    Raises:
        typer.BadParameter: If the file cannot be read or parsed.
    """

    if config_path is None:
        return ParameterSet()

    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise typer.BadParameter(f"Unable to read config file: {exc}") from exc

    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise typer.BadParameter("Configuration file contains invalid YAML") from exc

    if not isinstance(data, dict):
        raise typer.BadParameter("Configuration file must define a mapping")

    try:
        return ParameterSet.model_validate(data)
    except ValidationError as exc:
        raise typer.BadParameter("Configuration file is invalid") from exc


def _load_json_input(path: Path) -> list[SerializedProblem]:
    """Parse serialized problems from the JSON file at ``path``.

    Args:
        path: Path to the JSON file supplied via ``--json-input``.

    Returns:
        A list of validated :class:`SerializedProblem` entries.

    Raises:
        typer.BadParameter: If the file is unreadable or fails validation.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise typer.BadParameter(f"Unable to read JSON input: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("JSON input is not valid JSON") from exc

    if not isinstance(payload, list):
        raise typer.BadParameter("JSON input must be a list of problems")

    try:
        return [SerializedProblem.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter("JSON input failed validation") from exc


def _build_cli_parameter_set(params: dict[str, Any]) -> ParameterSet:
    """Convert CLI plugin overrides into a :class:`ParameterSet`.

    Args:
        params: Dictionary of CLI parameter values reported by Typer.

    Returns:
        Parameter set populated with plugin-specific override mappings.
    """

    plugin_overrides: dict[str, dict[str, Any]] = {}
    for plugin_name, definitions in _PLUGIN_PARAMETERS.items():
        overrides: dict[str, Any] = {}
        for definition in definitions:
            key = _option_storage_key(plugin_name, definition.name)
            value = params.get(key)
            if value is not None:
                overrides[definition.name] = value
        if overrides:
            plugin_overrides[plugin_name] = overrides
    return ParameterSet(common={}, plugins=plugin_overrides)


def _build_plugin_requests(
    params: dict[str, Any], total_problems: int, rng: random.Random | None = None
) -> list[PluginRequest]:
    """Create plugin generation requests derived from CLI flag selections.

    Args:
        params: Dictionary of CLI parameter values reported by Typer.
        total_problems: Total number of problems requested across all plugins.
        rng: Optional random number generator used for allocation.

    Returns:
        Requested quantities for each registered plugin (zero when omitted).
    """

    rng = rng or random.Random()
    selected_plugins = [
        plugin_name
        for plugin_name in _PLUGIN_PARAMETERS
        if params.get(plugin_name, False)
    ]

    allocations: dict[str, int] = {name: 0 for name in selected_plugins}
    remaining = total_problems if selected_plugins else 0

    if selected_plugins and remaining > 0:
        shuffled = selected_plugins.copy()
        rng.shuffle(shuffled)
        initial_allocation = min(remaining, len(selected_plugins))
        for name in shuffled[:initial_allocation]:
            allocations[name] += 1
        remaining -= initial_allocation

        while remaining > 0:
            name = rng.choice(selected_plugins)
            allocations[name] += 1
            remaining -= 1

    requests: list[PluginRequest] = []
    for plugin_name in _PLUGIN_PARAMETERS:
        quantity = allocations.get(plugin_name, 0)
        requests.append(PluginRequest(name=plugin_name, quantity=quantity))
    return requests


def _write_json_output(path: Path, problems: Iterable[dict[str, Any]]) -> None:
    """Persist ``problems`` to ``path`` as formatted JSON.

    Args:
        path: Destination path provided by ``--json-output``.
        problems: Serialized problem dictionaries produced by the coordinator.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(problems), indent=2), encoding="utf-8")


def _static_generate_options() -> list[click.Option]:
    """Return Click options that are always available on the generate command."""

    return [
        click.Option(
            ["--config", "-c"],
            type=click.Path(
                path_type=Path, exists=True, dir_okay=False, file_okay=True
            ),
            default=None,
            help="Path to a YAML configuration file providing default parameters.",
        ),
        click.Option(
            ["--json-input"],
            type=click.Path(
                path_type=Path, exists=True, dir_okay=False, file_okay=True
            ),
            default=None,
            help="Optional JSON file containing serialized problems to reproduce.",
        ),
        click.Option(
            ["--json-output"],
            type=click.Path(path_type=Path, dir_okay=False, file_okay=True),
            default=None,
            help="Destination for JSON serialization of generated problems.",
        ),
        click.Option(
            ["--output", "-o"],
            type=click.Path(path_type=Path, dir_okay=False, file_okay=True),
            default=Path("worksheet.pdf"),
            show_default=True,
            help="Destination PDF file path.",
        ),
        click.Option(
            ["--title"],
            type=str,
            default="Test",
            show_default=True,
            help="Title displayed at the top of the worksheet.",
        ),
        click.Option(
            ["--answer-key/--no-answer-key"],
            default=False,
            show_default=True,
            help="Include the answer key section in the generated PDF.",
        ),
        click.Option(
            ["--total-problems", "--total-problems-per-test"],
            type=click.IntRange(min=1),
            default=10,
            show_default=True,
            help="Total number of problems generated across selected plugins.",
        ),
    ]


def _plugin_generate_options() -> list[click.Option]:
    """Return plugin-derived Click options for the generate command."""

    options: list[click.Option] = []
    for plugin_name, definitions in _PLUGIN_PARAMETERS.items():
        options.append(
            click.Option(
                [f"--{plugin_name}"],
                is_flag=True,
                default=False,
                help=f"Include {plugin_name} problems in the worksheet.",
            )
        )
        for definition in definitions:
            options.append(
                click.Option(
                    [f"--{plugin_name}-{definition.name}"],
                    type=_click_type_for(definition),
                    default=None,
                    metavar="VALUE",
                    help=(
                        f"Override for {plugin_name} parameter '{definition.name}': "
                        f"{definition.description}"
                    ),
                )
            )
    return options


def _click_type_for(definition: ParameterDefinition) -> click.ParamType | type[Any]:
    """Resolve the Click type for ``definition`` based on its declared type."""

    declared = definition.type
    result: click.ParamType | type[Any] = str
    if isinstance(declared, str):
        result = _CLICK_TYPE_ALIASES.get(declared.lower(), str)
    elif isinstance(declared, type):
        result = _CLICK_TYPE_TYPES.get(declared, str)
    return result


class _GenerateCommand(TyperCommand):
    """Custom Click command that injects dynamic plugin options."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        params = list(kwargs.pop("params", []))
        params.extend(_static_generate_options())
        params.extend(_plugin_generate_options())
        super().__init__(*args, params=params, **kwargs)


def generate(
    config: Path | None,
    json_input: Path | None,
    json_output: Path | None,
    output: Path,
    title: str,
    answer_key: bool,
    total_problems: int,
    **plugin_options: Any,
) -> None:
    """Generate a math worksheet PDF using registered plugins.

    Args:
        config: Optional YAML configuration file path.
        json_input: Optional JSON file containing serialized problems.
        json_output: Optional path for writing the JSON serialization output.
        output: Destination PDF path for the generated worksheet.
        title: Worksheet title rendered at the top of the PDF.
        answer_key: Whether to include the answer key section in the PDF.
        total_problems: Number of problems distributed across selected plugins.
        **plugin_options: Plugin-specific flags and parameter overrides.

    Raises:
        typer.BadParameter: If the supplied CLI arguments cannot be processed.
    """

    yaml_parameters = _load_parameter_set(config)
    cli_parameters = _build_cli_parameter_set(plugin_options)
    plugin_requests = _build_plugin_requests(plugin_options, total_problems)
    json_entries = _load_json_input(json_input) if json_input else None

    selected_plugins = [
        plugin_name
        for plugin_name in _PLUGIN_PARAMETERS
        if plugin_options.get(plugin_name, False)
    ]

    if json_entries is None and not selected_plugins:
        raise typer.BadParameter(
            "Select at least one plugin flag or provide --json-input.",
            param_hint="--addition/--subtraction or --json-input",
        )

    request = GenerationRequest(
        plugin_requests=plugin_requests,
        yaml_parameters=yaml_parameters,
        cli_parameters=cli_parameters,
        json_input=json_entries,
    )

    coordinator = Coordinator(registry=_REGISTRY)
    result = coordinator.generate(request)

    pdf_params = {
        "path": output,
        "title": title,
        "include_answers": answer_key,
    }
    PdfOutputGenerator().generate(result.problems, pdf_params)

    if json_output is not None:
        _write_json_output(json_output, result.json_ready())

    typer.echo(f"Generated worksheet with {len(result.problems)} problems -> {output}")


def _generate_entrypoint(**kwargs) -> None:
    """Execute :func:`generate` using parameters parsed by Click."""

    generate(**kwargs)


# Register the command with Typer using the custom Click command class.
_GENERATE_HELP = (
    inspect.cleandoc(generate.__doc__ or "").splitlines()[0] if generate.__doc__ else ""
)
app.registered_commands.append(
    CommandInfo(
        name="generate",
        cls=_GenerateCommand,
        callback=_generate_entrypoint,
        help=_GENERATE_HELP,
    ),
)


def _normalize_argv(args: Sequence[str]) -> list[str]:
    """Ensure the CLI falls back to ``generate`` when flags are provided directly."""

    if not args:
        return ["generate"]

    first = args[0]
    known_commands = {command.name for command in app.registered_commands}

    if first in known_commands or not first.startswith("-"):
        return list(args)

    return ["generate", *args]


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point used by the console script defined in ``pyproject.toml``."""

    raw_args = list(argv if argv is not None else sys.argv[1:])
    app(args=_normalize_argv(raw_args))
