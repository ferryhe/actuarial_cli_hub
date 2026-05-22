from __future__ import annotations

import json
import subprocess
import sys

from actuarial_cli_hub.registry.loader import _installed_data_roots, load_manifests
from actuarial_cli_hub.registry.validator import validate_registry


def test_registry_validates_against_schema() -> None:
    result = validate_registry()
    assert result.ok, result.to_dict()
    assert result.manifest_count >= 10


def test_runtime_availability_is_explicit() -> None:
    manifests = load_manifests()
    assert manifests
    assert {manifest.runtime_availability for manifest in manifests} == {"planned"}


def test_installed_data_roots_include_user_base() -> None:
    roots = _installed_data_roots()
    assert roots
    assert all(root.is_absolute() for root in roots)


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
