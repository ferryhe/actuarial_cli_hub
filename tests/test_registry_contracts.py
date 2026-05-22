from __future__ import annotations

import json
import site
import subprocess
import sys

from actuarial_cli_hub.registry.loader import _installed_data_roots, load_manifests
from actuarial_cli_hub.registry.validator import validate_registry


def test_registry_validates_against_schema() -> None:
    result = validate_registry()
    assert result.ok, result.to_dict()
    assert result.manifest_count >= 10


def test_empty_registry_is_not_ready(tmp_path) -> None:
    (tmp_path / "registry" / "tools").mkdir(parents=True)
    (tmp_path / "registry" / "schemas").mkdir(parents=True)

    result = validate_registry(tmp_path)

    assert result.ok is False
    assert result.manifest_count == 0
    assert result.errors[0].message == "No registry manifests found"


def test_missing_schema_is_not_ready(tmp_path) -> None:
    tools = tmp_path / "registry" / "tools"
    tools.mkdir(parents=True)
    (tools / "demo.yaml").write_text("id: actuarial.demo\n", encoding="utf-8")

    result = validate_registry(tmp_path)

    assert result.ok is False
    assert result.manifest_count == 1
    assert "tool-manifest.schema.json" in result.errors[0].path


def test_runtime_availability_is_explicit() -> None:
    manifests = load_manifests()
    assert manifests
    availability = {manifest.tool_id: manifest.runtime_availability for manifest in manifests}
    assert availability["actuarial.reserve.chainladder"] == "implemented"
    assert set(availability.values()) <= {"planned", "implemented", "external"}


def test_installed_data_roots_include_user_base() -> None:
    roots = _installed_data_roots()
    assert roots
    assert all(root.is_absolute() for root in roots)
    assert any(root == site.getuserbase() for root in map(str, roots))


def test_registry_validate_json_cli() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", "registry", "validate", "--json"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []
