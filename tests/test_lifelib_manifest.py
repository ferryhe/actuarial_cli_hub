from __future__ import annotations

from pathlib import Path

import yaml

from actuarial_cli_hub.registry.validator import validate_registry


def _tool_manifest(tool_name: str) -> dict:
    path = Path("registry/tools") / f"{tool_name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_lifelib_and_modelx_manifests_validate() -> None:
    result = validate_registry()

    assert result.ok, [error.__dict__ for error in result.errors]


def test_lifelib_manifest_keeps_optional_boundary_contract() -> None:
    lifelib = _tool_manifest("lifelib")

    assert lifelib["id"] == "actuarial.life.lifelib"
    assert lifelib["runtime"]["kind"] == "optional-cli"
    assert lifelib["runtime"]["availability"] == "planned"
    assert lifelib["runtime"]["command"] == ["actuary", "life", "lifelib"]
    assert lifelib["runtime"]["allowedCommandPrefix"] == "actuary life lifelib"
    assert lifelib["io"]["artifacts"] == ["deterministic_result", "diagnostics", "run_manifest"]
    assert any("Optional dependencies" in item for item in lifelib["agent"]["limitations"])


def test_modelx_manifest_is_doctor_readiness_support_not_standalone_wrapper() -> None:
    modelx = _tool_manifest("modelx")

    assert modelx["id"] == "actuarial.life.modelx"
    assert modelx["runtime"]["kind"] == "optional-cli"
    assert modelx["runtime"]["availability"] == "planned"
    assert modelx["runtime"]["command"] == ["actuary", "doctor", "--runtime", "modelx"]
    assert "Not a standalone" in " ".join(modelx["agent"]["limitations"])
