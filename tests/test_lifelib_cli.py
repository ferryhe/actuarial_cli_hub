from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_lifelib_help() -> None:
    result = run_cli("life", "lifelib", "--help")

    assert result.returncode == 0
    assert "lifelib/modelx" in result.stdout
    assert "--run-id" in result.stdout
    assert "--json" in result.stdout


def test_lifelib_command_returns_runtime_missing_json_without_optional_deps(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(cli, "_runtime_packages", lambda runtime: (["lifelib", "modelx"], ["lifelib", "modelx"]))

    exit_code = cli.cmd_life_lifelib(argparse.Namespace(json=True, run_id="missing-runtime"))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["run_id"] == "missing-runtime"
    assert payload["status"] == "error"
    assert payload["tool"] == "actuarial.life.lifelib"
    assert payload["error"]["code"] == "runtime_missing"
    assert payload["error"]["details"]["required_packages"] == ["lifelib", "modelx"]
    assert payload["error"]["details"]["missing_packages"] == ["lifelib", "modelx"]


def test_lifelib_command_reports_not_implemented_when_runtime_is_present(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli

    monkeypatch.setattr(cli, "_runtime_packages", lambda runtime: (["lifelib", "modelx"], []))

    exit_code = cli.cmd_life_lifelib(argparse.Namespace(json=True, run_id="present-runtime"))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["run_id"] == "present-runtime"
    assert payload["error"]["code"] == "not_implemented"
    assert payload["error"]["details"]["required_packages"] == ["lifelib", "modelx"]


def test_lifelib_runtime_doctor_reports_optional_dependency_status(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli
    from actuarial_cli_hub.registry.validator import RegistryValidationResult

    monkeypatch.setattr(cli, "_runtime_packages", lambda runtime: (["lifelib", "modelx"], ["lifelib", "modelx"]))

    validation = RegistryValidationResult(ok=True, manifest_count=11, errors=[])
    exit_code = cli.cmd_runtime_doctor(argparse.Namespace(runtime="lifelib", json=True), validation.ok)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["tool"] == "actuarial_cli_hub.doctor.lifelib"
    assert payload["error"]["code"] == "runtime_missing"
    assert payload["error"]["details"]["runtime"] == "lifelib"
    assert payload["error"]["details"]["packages"] == {"lifelib": False, "modelx": False}


def test_lifelib_runtime_doctor_success_when_runtime_is_present(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli
    from actuarial_cli_hub.registry.validator import RegistryValidationResult

    monkeypatch.setattr(cli, "_runtime_packages", lambda runtime: (["lifelib", "modelx"], []))

    validation = RegistryValidationResult(ok=True, manifest_count=11, errors=[])
    exit_code = cli.cmd_runtime_doctor(argparse.Namespace(runtime="lifelib", json=True), validation.ok)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["data"]["available"] is True
    assert payload["data"]["packages"] == {"lifelib": True, "modelx": True}


def test_lifelib_runtime_doctor_preserves_registry_invalid_contract(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli
    from actuarial_cli_hub.registry.validator import RegistryValidationError, RegistryValidationResult

    broken = RegistryValidationResult(
        ok=False,
        manifest_count=1,
        errors=[RegistryValidationError(path="registry/tools/broken.yaml", message="bad", json_path="$")],
    )
    monkeypatch.setattr(cli, "validate_registry", lambda: broken)
    monkeypatch.setattr(cli, "_runtime_packages", lambda runtime: (["lifelib", "modelx"], []))

    exit_code = cli.main(["doctor", "--runtime", "lifelib", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["error"]["code"] == "registry_invalid"
    assert payload["error"]["details"]["runtime"] == "lifelib"
