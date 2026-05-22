from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from actuarial_cli_hub.skills.generator import export_skills

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_actuarial_cli.py"


def test_generic_tool_cards_include_registry_contracts(tmp_path: Path) -> None:
    exported = export_skills("generic", tmp_path)

    paths = {item.path.name for item in exported}
    assert "reserve-chainladder.yaml" in paths
    assert "loss-aggregate.yaml" in paths

    card = yaml.safe_load((tmp_path / "loss-aggregate.yaml").read_text(encoding="utf-8"))
    assert card["schema_version"] == "actuarial-cli-tool-card.v1"
    assert card["id"] == "actuarial.loss.aggregate"
    assert card["runtime"]["availability"] == "implemented"
    assert card["runtime"]["command"] == ["actuary", "loss", "aggregate"]
    assert card["agent"]["skillPath"] == "skills/hermes/actuarial-aggregate-loss/SKILL.md"
    assert "aggregate_result" in card["io"]["artifacts"]


def test_hermes_export_writes_implemented_tool_skills_only(tmp_path: Path) -> None:
    exported = export_skills("hermes", tmp_path)

    tool_ids = {item.tool_id for item in exported}
    assert {"actuarial.reserve.chainladder", "actuarial.loss.aggregate"} <= tool_ids
    assert all("future" not in item.path.parts for item in exported)

    skill_path = tmp_path / "actuarial-aggregate-loss" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert "name: actuarial-aggregate-loss" in text
    assert "actuary loss aggregate --help" in text
    assert "aggregate_result" in text


def test_skills_export_cli_json_envelope(tmp_path: Path) -> None:
    output_dir = tmp_path / "cards"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "skills",
            "export",
            "--target",
            "generic",
            "--output",
            str(output_dir),
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "success"
    assert payload["data"]["target"] == "generic"
    assert payload["data"]["file_count"] == payload["data"]["tool_count"] == payload["data"]["count"]
    assert (output_dir / "loss-aggregate.yaml").is_file()


def test_ai_interface_export_cli_reports_one_file_with_many_tools(tmp_path: Path) -> None:
    output_dir = tmp_path / "ai-preview"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "skills",
            "export",
            "--target",
            "ai_interface",
            "--output",
            str(output_dir),
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "success"
    assert payload["data"]["target"] == "ai_interface"
    assert payload["data"]["file_count"] == 1
    assert payload["data"]["tool_count"] == payload["data"]["count"]
    assert "actuarial.loss.aggregate" in payload["data"]["tools"]
    assert (output_dir / "actuarial_cli_hub" / "skill.yaml").is_file()
