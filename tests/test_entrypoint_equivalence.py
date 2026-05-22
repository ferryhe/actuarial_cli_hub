from __future__ import annotations

import json
import subprocess
import sys


def run_command(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_repo_script_and_module_registry_list_match() -> None:
    script_payload = run_command([sys.executable, "scripts/run_actuarial_cli.py", "registry", "list", "--json"])
    module_payload = run_command([sys.executable, "-m", "actuarial_cli_hub", "registry", "list", "--json"])

    assert script_payload == module_payload
    count = script_payload["count"]
    assert isinstance(count, int)
    assert count >= 10
