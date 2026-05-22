from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path


MODEL = "examples/cashflower/simple_model.py"
ASSUMPTIONS = "examples/cashflower/assumptions.yaml"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_cashflower_help() -> None:
    result = run_cli("cashflow", "cashflower", "--help")

    assert result.returncode == 0
    assert "cashflower model.py" in result.stdout
    assert "--assumptions" in result.stdout


def test_cashflower_cli_writes_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "cashflows.json"

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        MODEL,
        "--assumptions",
        ASSUMPTIONS,
        "--output",
        str(output),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["tool"] == "actuarial.cashflow.cashflower"
    assert {artifact["id"] for artifact in envelope["artifacts"]} == {"deterministic_result", "diagnostics"}
    assert envelope["data"]["row_count"] == 4

    cashflows = json.loads(output.read_text())
    assert cashflows["method"] == "cashflower.run"
    assert cashflows["row_count"] == 4
    assert cashflows["summary"]["final_record"]["net_cashflow"] > 0
    assert cashflows["diagnostics"]["cashflower_package_version"] != "not-installed"

    diagnostics_path = next(artifact["path"] for artifact in envelope["artifacts"] if artifact["id"] == "diagnostics")
    diagnostics = json.loads(Path(diagnostics_path).read_text())
    assert diagnostics["diagnostic_rows"] >= 1


def test_cashflower_cli_returns_json_error_for_invalid_assumptions(tmp_path: Path) -> None:
    bad_assumptions = tmp_path / "bad.yaml"
    bad_assumptions.write_text("[]\n", encoding="utf-8")

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        MODEL,
        "--assumptions",
        str(bad_assumptions),
        "--output",
        str(tmp_path / "cashflows.json"),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["error"]["code"] == "invalid_input"
    assert "YAML mapping" in envelope["error"]["message"]


def test_cashflower_cli_accepts_null_yaml_sections(tmp_path: Path) -> None:
    assumptions = tmp_path / "assumptions.yaml"
    assumptions.write_text(
        "settings:\n"
        "assumptions:\n"
        "  initial_premium: 100.0\n"
        "  growth_rate: 0.02\n"
        "  claim_ratio: 0.6\n",
        encoding="utf-8",
    )

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        MODEL,
        "--assumptions",
        str(assumptions),
        "--output",
        str(tmp_path / "cashflows.json"),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["data"]["row_count"] > 0


def test_cashflower_cli_accepts_yaml_dates(tmp_path: Path) -> None:
    assumptions = tmp_path / "assumptions.yaml"
    assumptions.write_text(
        "settings:\n"
        "  T_MAX_CALCULATION: 1\n"
        "  T_MAX_OUTPUT: 1\n"
        "assumptions:\n"
        "  initial_premium: 100.0\n"
        "  growth_rate: 0.02\n"
        "  claim_ratio: 0.6\n"
        "  effective_date: 2026-01-01\n",
        encoding="utf-8",
    )

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        MODEL,
        "--assumptions",
        str(assumptions),
        "--output",
        str(tmp_path / "cashflows.json"),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["data"]["row_count"] == 2


def test_cashflower_cli_rejects_colliding_artifact_paths(tmp_path: Path) -> None:
    output = tmp_path / "cashflows.json"

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        MODEL,
        "--assumptions",
        ASSUMPTIONS,
        "--output",
        str(output),
        "--diagnostics-output",
        str(output),
        "--json",
    )

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["error"]["code"] == "invalid_input"
    assert "must differ" in envelope["error"]["message"]


def test_cashflower_cli_returns_json_error_for_missing_model_dependency(tmp_path: Path) -> None:
    model = tmp_path / "model.py"
    model.write_text(
        "import definitely_missing_cashflower_test_dependency\n"
        "from cashflower import variable\n"
        "@variable()\n"
        "def amount(t):\n"
        "    return 1.0\n",
        encoding="utf-8",
    )

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        str(model),
        "--assumptions",
        ASSUMPTIONS,
        "--output",
        str(tmp_path / "cashflows.json"),
        "--json",
    )

    assert result.returncode == 2
    assert result.stderr == ""
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "error"
    assert envelope["error"]["code"] == "upstream_failure"
    assert envelope["error"]["details"]["missing_module"] == "definitely_missing_cashflower_test_dependency"


def test_cashflower_cli_preserves_sibling_model_files(tmp_path: Path) -> None:
    (tmp_path / "helper.py").write_text("CLAIM_RATIO = 0.6\n", encoding="utf-8")
    model = tmp_path / "model.py"
    model.write_text(
        "from cashflower import variable\n"
        "from input import assumptions\n"
        "from helper import CLAIM_RATIO\n"
        "@variable()\n"
        "def premium(t):\n"
        "    return assumptions['initial_premium']\n"
        "@variable()\n"
        "def claims(t):\n"
        "    return premium(t) * CLAIM_RATIO\n",
        encoding="utf-8",
    )
    assumptions = tmp_path / "assumptions.yaml"
    assumptions.write_text(
        "settings:\n"
        "  T_MAX_CALCULATION: 0\n"
        "  T_MAX_OUTPUT: 0\n"
        "assumptions:\n"
        "  initial_premium: 100.0\n",
        encoding="utf-8",
    )

    result = run_cli(
        "cashflow",
        "cashflower",
        "--model",
        str(model),
        "--assumptions",
        str(assumptions),
        "--output",
        str(tmp_path / "cashflows.json"),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "success"
    assert envelope["data"]["summary"]["final_record"]["claims"] == 60.0


def test_cashflower_in_process_runs_do_not_reuse_stale_sibling_modules(tmp_path: Path, monkeypatch) -> None:
    from actuarial_cli_hub.adapters.cashflower import run_cashflower_model

    assumptions = tmp_path / "assumptions.yaml"
    assumptions.write_text(
        "settings:\n"
        "  T_MAX_CALCULATION: 0\n"
        "  T_MAX_OUTPUT: 0\n"
        "assumptions:\n"
        "  initial_premium: 100.0\n",
        encoding="utf-8",
    )

    def make_project(name: str, claim_ratio: float) -> Path:
        project = tmp_path / name
        package = project / "factors"
        package.mkdir(parents=True)
        (project / "helper.py").write_text(f"CLAIM_RATIO = {claim_ratio}\n", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "mortality.py").write_text(f"PACKAGE_RATIO = {claim_ratio}\n", encoding="utf-8")
        (project / "model.py").write_text(
            "from cashflower import variable\n"
            "from input import assumptions\n"
            "from helper import CLAIM_RATIO\n"
            "from factors.mortality import PACKAGE_RATIO\n"
            "@variable()\n"
            "def premium(t):\n"
            "    return assumptions['initial_premium']\n"
            "@variable()\n"
            "def claims(t):\n"
            "    return premium(t) * CLAIM_RATIO\n"
            "@variable()\n"
            "def package_claims(t):\n"
            "    return premium(t) * PACKAGE_RATIO\n",
            encoding="utf-8",
        )
        return project

    first = make_project("first", 0.6)
    second = make_project("second", 0.7)
    stale_helper = types.ModuleType("helper")
    setattr(stale_helper, "CLAIM_RATIO", 0.9)
    stale_package = types.ModuleType("factors")
    stale_submodule = types.ModuleType("factors.mortality")
    setattr(stale_submodule, "PACKAGE_RATIO", 0.9)
    monkeypatch.setitem(sys.modules, "helper", stale_helper)
    monkeypatch.setitem(sys.modules, "factors", stale_package)
    monkeypatch.setitem(sys.modules, "factors.mortality", stale_submodule)

    first_result, _ = run_cashflower_model(model_path=first / "model.py", assumptions_path=assumptions)
    second_result, _ = run_cashflower_model(model_path=second / "model.py", assumptions_path=assumptions)

    assert first_result["summary"]["final_record"]["claims"] == 60.0
    assert first_result["summary"]["final_record"]["package_claims"] == 60.0
    assert second_result["summary"]["final_record"]["claims"] == 70.0
    assert second_result["summary"]["final_record"]["package_claims"] == 70.0
    assert sys.modules["helper"] is stale_helper
    assert sys.modules["factors"] is stale_package
    assert sys.modules["factors.mortality"] is stale_submodule
