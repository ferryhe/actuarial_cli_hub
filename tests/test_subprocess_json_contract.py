from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from actuarial_cli_hub.adapters.subprocess_json import run_json_command


def test_run_json_command_reads_json_stdout() -> None:
    payload = run_json_command([sys.executable, "-c", "import json; print(json.dumps({'ok': True, 'value': 7}))"])

    assert payload == {"ok": True, "value": 7}


def test_run_json_command_can_pass_file_content_on_stdin(tmp_path: Path) -> None:
    input_path = tmp_path / "payload.json"
    input_path.write_text('{"value": 3}', encoding="utf-8")

    payload = run_json_command(
        [
            sys.executable,
            "-c",
            "import json, sys; data=json.load(sys.stdin); print(json.dumps({'value': data['value'] * 2}))",
        ],
        input_path=input_path,
    )

    assert payload == {"value": 6}


def test_run_json_command_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        run_json_command([sys.executable, "-c", "print('not json')"])


def test_run_json_command_rejects_nonzero_exit() -> None:
    with pytest.raises(RuntimeError, match="subprocess exited 9"):
        run_json_command([sys.executable, "-c", "import sys; print('bad', file=sys.stderr); raise SystemExit(9)"])


def test_run_json_command_rejects_oversized_output() -> None:
    script = "import json; print(json.dumps({'blob': 'x' * 2048}))"

    with pytest.raises(RuntimeError, match="max_output_bytes"):
        run_json_command([sys.executable, "-c", script], max_output_bytes=1024)


def test_run_json_command_requires_object_output() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        run_json_command([sys.executable, "-c", "import json; print(json.dumps([1, 2, 3]))"])
