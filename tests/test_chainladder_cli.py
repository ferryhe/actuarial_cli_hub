from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_chainladder_help() -> None:
    result = run_cli("reserve", "chainladder", "--help")

    assert result.returncode == 0
    assert "chain-ladder" in result.stdout
    assert "--diagnostics-output" in result.stdout


def test_chainladder_cli_writes_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "deterministic_result.json"
    diagnostics = tmp_path / "diagnostics.json"
    explanation = tmp_path / "explanation.md"

    result = run_cli(
        "reserve",
        "chainladder",
        "--input",
        "examples/reserving/sample_triangle.csv",
        "--output",
        str(output),
        "--diagnostics-output",
        str(diagnostics),
        "--explain-output",
        str(explanation),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["tool"] == "actuarial.reserve.chainladder"
    assert {artifact["id"] for artifact in envelope["artifacts"]} == {
        "deterministic_result",
        "diagnostics",
        "explanation_markdown",
    }

    deterministic_result = json.loads(output.read_text())
    assert deterministic_result["method"] == "chainladder.Chainladder"
    assert len(deterministic_result["origins"]) == 5
    assert deterministic_result["totals"]["ultimate"] > deterministic_result["totals"]["latest"]

    diagnostic_payload = json.loads(diagnostics.read_text())
    assert diagnostic_payload["origin_count"] == 5
    assert "chainladder_package_version" in diagnostic_payload
    assert explanation.read_text().startswith("# Chainladder Reserving Result")


def test_chainladder_cli_returns_json_error_for_invalid_input(tmp_path: Path) -> None:
    bad_input = tmp_path / "bad.csv"
    bad_input.write_text("year,12,24\n2020,1,2\n", encoding="utf-8")

    result = run_cli(
        "reserve",
        "chainladder",
        "--input",
        str(bad_input),
        "--output",
        str(tmp_path / "deterministic_result.json"),
        "--diagnostics-output",
        str(tmp_path / "diagnostics.json"),
        "--explain-output",
        str(tmp_path / "explanation.md"),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["tool"] == "actuarial.reserve.chainladder"
    assert envelope["error"]["code"] == "invalid_input"
    assert "origin" in envelope["error"]["message"]


def test_chainladder_cli_returns_json_error_for_missing_input(tmp_path: Path) -> None:
    missing_input = tmp_path / "missing.csv"

    result = run_cli(
        "reserve",
        "chainladder",
        "--input",
        str(missing_input),
        "--output",
        str(tmp_path / "deterministic_result.json"),
        "--diagnostics-output",
        str(tmp_path / "diagnostics.json"),
        "--explain-output",
        str(tmp_path / "explanation.md"),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["error"]["code"] == "invalid_input"
    assert str(missing_input) in envelope["error"]["details"]["input_path"]
