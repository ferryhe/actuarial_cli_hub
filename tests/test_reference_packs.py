from __future__ import annotations

import json
from pathlib import Path

import yaml

from actuarial_cli_hub.registry.validator import validate_registry


def _tool_manifest(tool_name: str) -> dict:
    path = Path("registry/tools") / f"{tool_name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_reference_manifests_remain_reference_not_runtime_wrappers() -> None:
    result = validate_registry()
    faslr = _tool_manifest("faslr")
    lda = _tool_manifest("loss-data-analytics")

    assert result.ok, [error.__dict__ for error in result.errors]
    assert faslr["runtime"]["kind"] == "reference"
    assert faslr["runtime"]["command"] == ["actuary", "reserve", "faslr"]
    assert "GUI/application target" in " ".join(faslr["agent"]["limitations"])
    assert lda["status"] == "external-reference"
    assert lda["runtime"]["kind"] == "reference"
    assert lda["runtime"]["command"] == ["actuary", "reference", "lda", "search"]


def test_lda_search_writes_reference_and_diagnostics_artifacts(tmp_path: Path) -> None:
    from actuarial_cli_hub.adapters.reference import write_lda_search_outputs

    output = tmp_path / "reference_result.json"
    diagnostics = tmp_path / "diagnostics.json"
    payload = write_lda_search_outputs(
        query="credibility",
        output_path=output,
        diagnostics_path=diagnostics,
        run_id="lda-test",
    )

    assert payload["status"] == "success"
    assert payload["tool"] == "actuarial.reference.loss_data_analytics"
    assert {item["id"] for item in payload["artifacts"]} == {"reference_result", "diagnostics"}
    result_data = json.loads(output.read_text(encoding="utf-8"))
    diagnostics_data = json.loads(diagnostics.read_text(encoding="utf-8"))
    assert result_data["query"] == "credibility"
    assert result_data["results"][0]["url"].startswith("https://openacttexts.github.io/")
    assert diagnostics_data["runtime"] == "reference-only"


def test_faslr_catalog_adapter_is_reference_only(tmp_path: Path) -> None:
    from actuarial_cli_hub.adapters.reference import write_faslr_catalog_outputs

    payload = write_faslr_catalog_outputs(
        query="reserving api",
        output_path=tmp_path / "run_manifest.json",
        diagnostics_path=tmp_path / "diagnostics.json",
        run_id="faslr-test",
    )

    assert payload["status"] == "success"
    assert payload["tool"] == "actuarial.reserve.faslr"
    assert payload["data"]["result"]["execution_status"] == "not_executable_in_v1"
    assert {item["id"] for item in payload["artifacts"]} == {"run_manifest", "diagnostics"}
