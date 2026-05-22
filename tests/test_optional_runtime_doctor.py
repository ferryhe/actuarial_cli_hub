from __future__ import annotations

import argparse
import json

from actuarial_cli_hub.runtimes.base import RuntimeStatus


def test_julia_doctor_reports_missing_runtime(monkeypatch, capsys) -> None:
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

    exit_code = cli.cmd_runtime_doctor(argparse.Namespace(runtime="julia", json=True), registry_ok=True)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "runtime_missing"
    assert payload["error"]["details"]["runtime"] == "julia"
    assert payload["error"]["details"]["packages"] == {"julia": False}
    assert payload["error"]["details"]["runtime_status"]["error"] == "julia executable not found on PATH"


def test_r_doctor_reports_available_runtime(monkeypatch, capsys) -> None:
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

    exit_code = cli.cmd_runtime_doctor(argparse.Namespace(runtime="r", json=True), registry_ok=True)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["data"]["runtime"] == "r"
    assert payload["data"]["packages"] == {"Rscript": True}
    assert payload["data"]["runtime_status"]["version"] == "Rscript 4.4.0"


def test_r_doctor_reports_unavailable_when_version_probe_fails(monkeypatch, capsys) -> None:
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

    exit_code = cli.cmd_runtime_doctor(argparse.Namespace(runtime="r", json=True), registry_ok=True)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"]["code"] == "runtime_unavailable"
    assert payload["error"]["details"]["packages"] == {"Rscript": True}
    assert payload["error"]["details"]["available"] is False
    assert payload["error"]["details"]["runtime_status"]["error"] == "version command exited 1"


def test_runtime_doctor_help_lists_cross_runtime_choices() -> None:
    parser = __import__("actuarial_cli_hub.cli", fromlist=["build_parser"]).build_parser()

    doctor = next(action for action in parser._subparsers._actions if getattr(action, "choices", None)).choices["doctor"]
    runtime_action = next(action for action in doctor._actions if "--runtime" in action.option_strings)
    assert set(runtime_action.choices) >= {"lifelib", "modelx", "julia", "r"}
