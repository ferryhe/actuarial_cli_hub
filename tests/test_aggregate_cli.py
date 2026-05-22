from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROADMAP_DECL = "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_aggregate_help() -> None:
    result = run_cli("loss", "aggregate", "--help")

    assert result.returncode == 0
    assert "aggregate loss DSL" in result.stdout
    assert "--decl" in result.stdout


def test_aggregate_cli_writes_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    explanation = tmp_path / "explanation.md"

    result = run_cli(
        "loss",
        "aggregate",
        "--decl",
        ROADMAP_DECL,
        "--output",
        str(output),
        "--explain-output",
        str(explanation),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["tool"] == "actuarial.loss.aggregate"
    assert {artifact["id"] for artifact in envelope["artifacts"]} == {
        "aggregate_result",
        "diagnostics",
        "explanation_markdown",
    }

    aggregate_result = json.loads(output.read_text())
    assert aggregate_result["method"] == "aggregate.build"
    assert aggregate_result["declaration"] == ROADMAP_DECL
    assert aggregate_result["normalized_declaration"].endswith(" poisson")
    assert aggregate_result["summary"]["expected_loss"] > 0
    assert aggregate_result["summary"]["coefficient_of_variation"] > 0
    assert "p95" in aggregate_result["quantiles"]
    assert aggregate_result["diagnostics"]["aggregate_package_version"] != "not-installed"
    diagnostics_artifact = next(artifact for artifact in envelope["artifacts"] if artifact["id"] == "diagnostics")
    assert json.loads(Path(diagnostics_artifact["path"]).read_text())["aggregate_package_version"] != "not-installed"
    assert explanation.read_text().startswith("# Aggregate Loss Result")


def test_aggregate_cli_returns_json_error_for_invalid_declaration(tmp_path: Path) -> None:
    result = run_cli(
        "loss",
        "aggregate",
        "--decl",
        "not an aggregate declaration",
        "--output",
        str(tmp_path / "result.json"),
        "--explain-output",
        str(tmp_path / "explanation.md"),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["tool"] == "actuarial.loss.aggregate"
    assert envelope["error"]["code"] == "invalid_input"
    assert envelope["error"]["details"]["declaration"] == "not an aggregate declaration"


def test_aggregate_cli_maps_parser_rejections_to_invalid_input(tmp_path: Path) -> None:
    result = run_cli(
        "loss",
        "aggregate",
        "--decl",
        "agg Bad 100 claims 1000 xs 0 sev nosuch 50 cv 1",
        "--output",
        str(tmp_path / "result.json"),
        "--explain-output",
        str(tmp_path / "explanation.md"),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["error"]["code"] == "invalid_input"
    assert envelope["error"]["message"]
