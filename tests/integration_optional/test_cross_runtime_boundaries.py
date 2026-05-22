from __future__ import annotations

import shutil
import subprocess

import pytest


def _runtime_or_skip(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        pytest.skip(f"optional runtime {command!r} is not installed")
    return executable


def test_mortality_table_boundary_runs_with_julia_runtime_when_present() -> None:
    _runtime_or_skip("julia")

    result = subprocess.run(
        ["python", "scripts/run_actuarial_cli.py", "mortality", "table", "--json"],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert '"code": "not_implemented"' in result.stdout or '"code": "runtime_unavailable"' in result.stdout


def test_lifecontingencies_boundary_runs_with_r_runtime_when_present() -> None:
    _runtime_or_skip("Rscript")

    result = subprocess.run(
        ["python", "scripts/run_actuarial_cli.py", "lifecontingencies", "r", "--json"],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert '"code": "not_implemented"' in result.stdout or '"code": "runtime_unavailable"' in result.stdout
