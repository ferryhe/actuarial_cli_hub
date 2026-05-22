from __future__ import annotations

import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_repo_script_help() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "Contract-first CLI hub" in result.stdout
    assert "registry" in result.stdout
    assert "doctor" in result.stdout


def test_registry_help() -> None:
    result = run_cli("registry", "--help")
    assert result.returncode == 0
    assert "list" in result.stdout
    assert "validate" in result.stdout
