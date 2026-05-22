from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from actuarial_cli_hub.runtime.artifacts import ArtifactRef, RunArtifacts
from actuarial_cli_hub.runtime.envelope import error_envelope, success_envelope

# Replace these placeholders when copying the template.
TOOL_ID = "actuarial.<domain>.<tool>"


def write_tool_outputs(*, input_path: Path, output_path: Path | None, diagnostics_path: Path | None, run_id: str) -> dict[str, Any]:
    """Write artifacts for a new wrapper.

    Replace this template with the smallest public upstream API/CLI call. Keep
    optional/heavy imports inside this function so unrelated CLI commands such
    as ``--help`` and ``doctor`` do not fail when the wrapper runtime is absent.
    """
    if not input_path.is_file():
        return error_envelope(
            tool=TOOL_ID,
            run_id=run_id,
            code="invalid_input",
            message=f"Input file does not exist: {input_path}",
            details={"input": str(input_path)},
        ).to_dict()

    try:
        case = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return error_envelope(
            tool=TOOL_ID,
            run_id=run_id,
            code="invalid_input",
            message=f"Input file is not valid JSON: {input_path}",
            details={"input": str(input_path), "line": exc.lineno, "column": exc.colno},
        ).to_dict()

    result = {"input": case, "note": "replace template logic with a public upstream call"}
    diagnostics = {"runtime": "template", "input_path": str(input_path)}

    artifacts = RunArtifacts(run_id)
    refs: list[ArtifactRef] = []
    if output_path is None:
        refs.append(artifacts.write_json("deterministic_result", "deterministic_result.json", result))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        refs.append(ArtifactRef(id="deterministic_result", path=str(output_path)))

    if diagnostics_path is None:
        refs.append(artifacts.write_json("diagnostics", "diagnostics.json", diagnostics))
    else:
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        refs.append(ArtifactRef(id="diagnostics", path=str(diagnostics_path)))

    return success_envelope(
        tool=TOOL_ID,
        run_id=run_id,
        data={"summary": diagnostics, "result": result},
        artifacts=[ref.to_dict() for ref in refs],
    ).to_dict()
