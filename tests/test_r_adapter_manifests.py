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


def test_r_adapter_manifests_keep_optional_boundaries() -> None:
    result = validate_registry()
    lifecontingencies = _tool_manifest("lifecontingencies-r")
    insurancerating = _tool_manifest("insurancerating-r")

    assert result.ok, [error.__dict__ for error in result.errors]
    assert lifecontingencies["id"] == "actuarial.lifecontingencies.r"
    assert lifecontingencies["runtime"]["kind"] == "optional-cli"
    assert lifecontingencies["runtime"]["availability"] == "planned"
    assert lifecontingencies["runtime"]["command"] == ["actuary", "lifecontingencies", "r"]
    assert lifecontingencies["runtime"]["allowedCommandPrefix"] == "actuary lifecontingencies r"
    assert insurancerating["id"] == "actuarial.pricing.insurancerating"
    assert insurancerating["runtime"]["kind"] == "optional-cli"
    assert insurancerating["runtime"]["availability"] == "planned"
    assert insurancerating["runtime"]["command"] == ["actuary", "pricing", "insurancerating"]
    assert insurancerating["runtime"]["allowedCommandPrefix"] == "actuary pricing insurancerating"


def test_lifecontingencies_boundary_reports_missing_r(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(
        cli,
        "check_r_runtime",
        lambda: RuntimeStatus(
            runtime="r",
            command="Rscript",
            executable=None,
            available=False,
            error="Rscript executable not found on PATH",
        ),
    )

    exit_code = cli.cmd_lifecontingencies_r(argparse.Namespace(run_id="demo", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "runtime_missing"
    assert payload["error"]["details"]["runtime"] == "r"
    assert payload["error"]["details"]["package"] == "lifecontingencies"


def test_insurancerating_boundary_reports_unavailable_r(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(
        cli,
        "check_r_runtime",
        lambda: RuntimeStatus(
            runtime="r",
            command="Rscript",
            executable="/usr/bin/Rscript",
            available=False,
            error="version command exited 1",
        ),
    )

    exit_code = cli.cmd_pricing_insurancerating(argparse.Namespace(run_id="demo", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "runtime_unavailable"
    assert payload["error"]["details"]["runtime_status"]["executable"] == "/usr/bin/Rscript"
    assert payload["error"]["details"]["runtime_status"]["error"] == "version command exited 1"


def test_insurancerating_boundary_is_not_implemented_when_r_is_ready(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(
        cli,
        "check_r_runtime",
        lambda: RuntimeStatus(
            runtime="r",
            command="Rscript",
            executable="/usr/bin/Rscript",
            available=True,
            version="Rscript 4.4.0",
        ),
    )

    exit_code = cli.cmd_pricing_insurancerating(argparse.Namespace(run_id="demo", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "not_implemented"
    assert payload["error"]["details"]["package"] == "insurancerating"
