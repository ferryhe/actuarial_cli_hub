from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from actuarial_cli_hub.registry.validator import validate_registry


def _tool_manifest(tool_name: str) -> dict:
    path = Path("registry/tools") / f"{tool_name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_catalog_importer_manifest_stays_catalog_boundary() -> None:
    result = validate_registry()
    catalog = _tool_manifest("actuarial-foss")

    assert result.ok, [error.__dict__ for error in result.errors]
    assert catalog["id"] == "actuarial.catalog.actuarial_foss"
    assert catalog["runtime"]["kind"] == "catalog"
    assert catalog["runtime"]["command"] == ["actuary", "registry", "import-catalog"]
    assert catalog["runtime"]["allowedCommandPrefix"] == "actuary registry import-catalog"
    assert catalog["io"]["artifacts"] == ["run_manifest", "diagnostics"]


def test_catalog_importer_writes_run_manifest_and_diagnostics(tmp_path: Path) -> None:
    from actuarial_cli_hub.adapters.reference import write_catalog_import_outputs

    output = tmp_path / "run_manifest.json"
    diagnostics = tmp_path / "diagnostics.json"
    payload = write_catalog_import_outputs(
        query="reserving tools",
        source_path=None,
        output_path=output,
        diagnostics_path=diagnostics,
        run_id="catalog-test",
    )

    assert payload["status"] == "success"
    assert payload["tool"] == "actuarial.catalog.actuarial_foss"
    assert {item["id"] for item in payload["artifacts"]} == {"run_manifest", "diagnostics"}
    run_manifest = json.loads(output.read_text(encoding="utf-8"))
    diagnostics_data = json.loads(diagnostics.read_text(encoding="utf-8"))
    assert run_manifest["source"] == "actuarial-foss"
    assert any(entry["id"] == "FASLR" for entry in run_manifest["entries"])
    assert diagnostics_data["live_fetch"] is False


def test_catalog_importer_default_artifacts_are_under_run_root(tmp_path: Path, monkeypatch) -> None:
    from actuarial_cli_hub.adapters.reference import write_catalog_import_outputs

    monkeypatch.chdir(tmp_path)
    payload = write_catalog_import_outputs(
        query="all",
        source_path=None,
        output_path=None,
        diagnostics_path=None,
        run_id="catalog-defaults",
    )

    paths = {item["id"]: Path(item["path"]) for item in payload["artifacts"]}
    assert paths["run_manifest"] == Path(".tmp/actuarial-cli-runs/catalog-defaults/output/run_manifest.json")
    assert paths["diagnostics"] == Path(".tmp/actuarial-cli-runs/catalog-defaults/output/diagnostics.json")
    assert paths["run_manifest"].is_file()
    assert paths["diagnostics"].is_file()


def test_catalog_importer_accepts_reviewed_source_file(tmp_path: Path) -> None:
    source = tmp_path / "catalog.yaml"
    source.write_text(
        """
source: reviewed-catalog
entries:
  - id: custom-tool
    domain: reserving
    conversion_class: reference
    recommended_status: cataloged
limitations:
  - Reviewed local fixture only.
""".lstrip(),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_actuarial_cli.py",
            "registry",
            "import-catalog",
            "--source",
            str(source),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["data"]["result"]["source"] == "reviewed-catalog"
    assert payload["data"]["result"]["entries"][0]["id"] == "custom-tool"
    assert payload["data"]["summary"]["source_path"] == str(source)


def test_catalog_importer_malformed_yaml_source_returns_json_error(tmp_path: Path) -> None:
    source = tmp_path / "bad.yaml"
    source.write_text("entries: [\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_actuarial_cli.py",
            "registry",
            "import-catalog",
            "--source",
            str(source),
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
    assert payload["error"]["code"] == "invalid_input"
    assert "YAML is invalid" in payload["error"]["message"]


def test_reference_commands_return_json_error_for_bad_output_path(tmp_path: Path) -> None:
    directory_output = tmp_path / "directory-output"
    directory_output.mkdir()

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_actuarial_cli.py",
            "reference",
            "lda",
            "search",
            "--output",
            str(directory_output),
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
    assert payload["tool"] == "actuarial.reference.loss_data_analytics"
    assert payload["error"]["code"] == "invalid_input"


def test_catalog_importer_invalid_run_id_returns_json_error_without_traceback() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_actuarial_cli.py",
            "registry",
            "import-catalog",
            "--run-id",
            "bad/id",
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
    assert payload["tool"] == "actuarial.catalog.actuarial_foss"
    assert payload["run_id"] == "bad/id"
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"]["run_id"] == "bad/id"
