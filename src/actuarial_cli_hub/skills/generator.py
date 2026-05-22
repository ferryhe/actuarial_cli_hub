from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from actuarial_cli_hub.registry.loader import ToolManifest, load_manifests


SUPPORTED_TARGETS = ("hermes", "generic", "ai_interface")


@dataclass(frozen=True)
class ExportedSkill:
    target: str
    tool_id: str
    path: Path


def export_skills(target: str, output_dir: Path) -> list[ExportedSkill]:
    """Export agent-facing tool instructions from registry manifests.

    The exports are intentionally generated into caller-provided directories so
    downstream repos can consume them as preview artifacts without this repo
    modifying the downstream checkout.
    """
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported skill export target: {target}")

    manifests = load_manifests()
    output_dir.mkdir(parents=True, exist_ok=True)
    if target == "hermes":
        return _export_hermes(manifests, output_dir)
    if target == "generic":
        return _export_generic(manifests, output_dir)
    return _export_ai_interface(manifests, output_dir)


def _export_hermes(manifests: list[ToolManifest], output_dir: Path) -> list[ExportedSkill]:
    exported: list[ExportedSkill] = []
    for manifest in _implemented_manifests(manifests):
        slug = _hermes_slug(manifest.tool_id)
        path = output_dir / slug / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_hermes_skill(manifest), encoding="utf-8")
        exported.append(ExportedSkill(target="hermes", tool_id=manifest.tool_id, path=path))
    return exported


def _export_generic(manifests: list[ToolManifest], output_dir: Path) -> list[ExportedSkill]:
    exported: list[ExportedSkill] = []
    for manifest in manifests:
        path = output_dir / f"{_slug(manifest.tool_id)}.yaml"
        _write_yaml(path, _generic_card(manifest))
        exported.append(ExportedSkill(target="generic", tool_id=manifest.tool_id, path=path))
    return exported


def _export_ai_interface(manifests: list[ToolManifest], output_dir: Path) -> list[ExportedSkill]:
    path = output_dir / "actuarial_cli_hub" / "skill.yaml"
    payload = {
        "schema_version": "ai-interface-preview.v1",
        "preview_only": True,
        "source": "ferryhe/actuarial_cli_hub",
        "note": "Preview export only; ai_interface must add its own fallback mapping before executing this sibling repo.",
        "tools": [_generic_card(manifest) for manifest in manifests],
    }
    _write_yaml(path, payload)
    return [ExportedSkill(target="ai_interface", tool_id=manifest.tool_id, path=path) for manifest in manifests]


def _implemented_manifests(manifests: list[ToolManifest]) -> list[ToolManifest]:
    return [manifest for manifest in manifests if manifest.runtime_availability == "implemented"]


def _hermes_skill(manifest: ToolManifest) -> str:
    data = manifest.data
    command = " ".join(data["runtime"].get("command", []))
    use_cases = "\n".join(f"    - {item}" for item in data["agent"].get("useCases", []))
    limitations = "\n".join(f"    - {item}" for item in data["agent"].get("limitations", []))
    artifacts = "\n".join(f"- `{item}`" for item in data["io"].get("artifacts", []))
    return f"""---
name: {_hermes_slug(manifest.tool_id)}
description: Use `{command}` from actuarial_cli_hub for {data['name']} workflows.
version: 0.1.0
metadata:
  source_tool_id: {manifest.tool_id}
  runtime_availability: {manifest.runtime_availability}
  use_cases:
{use_cases}
  limitations:
{limitations}
---

# {data['name']}

Use this skill when an agent needs the `{manifest.tool_id}` tool from `actuarial_cli_hub`.

## Command

```bash
{command} --help
```

## Artifact Contract

{artifacts}

## Safety Notes

- Treat outputs as actuarial analysis aids, not signed actuarial opinions.
- Keep upstream repositories and downstream consumers read-only unless a separate task explicitly scopes changes there.
"""


def _generic_card(manifest: ToolManifest) -> dict[str, Any]:
    data = manifest.data
    agent = dict(data["agent"])
    if manifest.runtime_availability == "implemented":
        agent["skillPath"] = f"skills/hermes/{_hermes_slug(manifest.tool_id)}/SKILL.md"
    else:
        agent.pop("skillPath", None)
    return {
        "schema_version": "actuarial-cli-tool-card.v1",
        "id": manifest.tool_id,
        "name": manifest.name,
        "status": manifest.status,
        "priority": manifest.priority,
        "runtime": {
            "kind": manifest.runtime_kind,
            "availability": manifest.runtime_availability,
            "command": data["runtime"].get("command", []),
            "allowedCommandPrefix": data["runtime"].get("allowedCommandPrefix"),
        },
        "io": data["io"],
        "agent": agent,
        "upstream": data["upstream"],
    }


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _slug(tool_id: str) -> str:
    return tool_id.removeprefix("actuarial.").replace(".", "-").replace("_", "-")


def _hermes_slug(tool_id: str) -> str:
    names = {
        "actuarial.reserve.chainladder": "actuarial-reserving",
        "actuarial.loss.aggregate": "actuarial-aggregate-loss",
    }
    return names.get(tool_id, _slug(tool_id))
