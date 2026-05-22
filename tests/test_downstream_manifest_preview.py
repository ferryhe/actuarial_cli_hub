from __future__ import annotations

from pathlib import Path

import yaml

from actuarial_cli_hub.skills.generator import export_skills


def test_ai_interface_export_is_preview_only(tmp_path: Path) -> None:
    exported = export_skills("ai_interface", tmp_path)

    assert len(exported) > 1
    assert {item.path for item in exported} == {tmp_path / "actuarial_cli_hub" / "skill.yaml"}
    payload = yaml.safe_load((tmp_path / "actuarial_cli_hub" / "skill.yaml").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "ai-interface-preview.v1"
    assert payload["preview_only"] is True
    assert "ai_interface must add its own fallback mapping" in payload["note"]
    assert any(tool["id"] == "actuarial.loss.aggregate" for tool in payload["tools"])
    aggregate = next(tool for tool in payload["tools"] if tool["id"] == "actuarial.loss.aggregate")
    assert aggregate["agent"]["skillPath"] == "skills/hermes/actuarial-aggregate-loss/SKILL.md"
    planned = next(tool for tool in payload["tools"] if tool["id"] == "actuarial.catalog.actuarial_foss")
    assert "skillPath" not in planned["agent"]


def test_checked_in_ai_interface_preview_stays_preview_only() -> None:
    path = Path("skills/ai_interface/actuarial_cli_hub/skill.yaml")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["preview_only"] is True
    assert payload["source"] == "ferryhe/actuarial_cli_hub"
    assert any(tool["id"] == "actuarial.reserve.chainladder" for tool in payload["tools"])
