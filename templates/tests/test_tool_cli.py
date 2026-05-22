from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from actuarial_cli_hub.registry.validator import validate_registry


TOOL_MANIFEST = Path("registry/tools/<tool>.yaml")


def test_tool_manifest_validates() -> None:
    result = validate_registry()
    assert result.ok, [error.__dict__ for error in result.errors]
    assert TOOL_MANIFEST.is_file()
    manifest = yaml.safe_load(TOOL_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["id"] == "actuarial.<domain>.<tool>"
    assert manifest["io"]["artifacts"]


def test_tool_help() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_actuarial_cli.py", "<domain>", "<tool>", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--json" in proc.stdout


def test_tool_invalid_input_returns_json_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_actuarial_cli.py",
            "<domain>",
            "<tool>",
            "--input",
            str(missing),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "error"
    assert payload["error"]["code"] in {"invalid_input", "runtime_missing", "runtime_unavailable", "not_implemented"}
