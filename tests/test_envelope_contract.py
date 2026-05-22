from __future__ import annotations

import json

from actuarial_cli_hub.runtime.artifacts import RunArtifacts
from actuarial_cli_hub.runtime.envelope import error_envelope, success_envelope


def test_success_envelope_contract() -> None:
    envelope = success_envelope(
        tool="actuarial.test",
        run_id="demo",
        data={"value": 42},
        artifacts=[{"id": "deterministic_result", "path": "out.json", "media_type": "application/json"}],
    ).to_dict()

    assert envelope["schema_version"] == "actuarial-cli-envelope.v1"
    assert envelope["status"] == "success"
    assert envelope["tool"] == "actuarial.test"
    assert envelope["run_id"] == "demo"
    assert envelope["data"] == {"value": 42}
    assert "error" not in envelope


def test_error_envelope_contract() -> None:
    envelope = error_envelope(
        tool="actuarial.test",
        run_id="demo",
        code="invalid_input",
        message="bad payload",
    ).to_dict()

    assert envelope["status"] == "error"
    assert envelope["error"]["code"] == "invalid_input"
    assert "data" not in envelope


def test_doctor_uses_error_envelope_when_registry_invalid(monkeypatch, capsys) -> None:
    from actuarial_cli_hub import cli
    from actuarial_cli_hub.registry.validator import RegistryValidationError, RegistryValidationResult

    broken = RegistryValidationResult(
        ok=False,
        manifest_count=1,
        errors=[RegistryValidationError(path="registry/tools/broken.yaml", message="bad", json_path="$")],
    )
    monkeypatch.setattr(cli, "validate_registry", lambda: broken)

    exit_code = cli.main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "registry_invalid"


def test_run_artifacts_write_json(tmp_path) -> None:
    artifacts = RunArtifacts("demo", root=tmp_path / "runs" / "demo")
    ref = artifacts.write_json("diagnostics", "diagnostics.json", {"ok": True})

    assert ref.id == "diagnostics"
    assert ref.path.endswith("output/diagnostics.json")
    assert json.loads((tmp_path / "runs" / "demo" / "output" / "diagnostics.json").read_text()) == {"ok": True}
