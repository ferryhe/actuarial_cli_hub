from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from actuarial_cli_hub.registry.validator import validate_registry
from actuarial_cli_hub.runtimes.base import RuntimeStatus


def _tool_manifest(tool_name: str) -> dict:
    path = Path("registry/tools") / f"{tool_name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_mortality_manifest_keeps_optional_julia_boundary_contract() -> None:
    result = validate_registry()
    mortality = _tool_manifest("mortalitytables-jl")

    assert result.ok, [error.__dict__ for error in result.errors]
    assert mortality["id"] == "actuarial.mortality.tables_jl"
    assert mortality["runtime"]["kind"] == "optional-cli"
    assert mortality["runtime"]["availability"] == "planned"
    assert mortality["runtime"]["command"] == ["actuary", "mortality", "table"]
    assert mortality["runtime"]["allowedCommandPrefix"] == "actuary mortality table"
    assert mortality["io"]["artifacts"] == ["mortality_result", "diagnostics"]


def test_mortality_boundary_reports_missing_julia(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(
        cli,
        "check_julia_runtime",
        lambda: RuntimeStatus(
            runtime="julia",
            command="julia",
            executable=None,
            available=False,
            error="julia executable not found on PATH",
        ),
    )

    exit_code = cli.cmd_mortality_table(argparse.Namespace(run_id="demo", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "runtime_missing"
    assert payload["error"]["details"]["runtime"] == "julia"
    assert payload["error"]["details"]["package"] == "MortalityTables.jl"


def test_mortality_boundary_is_not_implemented_when_julia_is_ready(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(
        cli,
        "check_julia_runtime",
        lambda: RuntimeStatus(
            runtime="julia",
            command="julia",
            executable="/usr/bin/julia",
            available=True,
            version="julia version 1.10.0",
        ),
    )

    exit_code = cli.cmd_mortality_table(argparse.Namespace(run_id="demo", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "not_implemented"
    assert payload["error"]["details"]["runtime_status"]["available"] is True
