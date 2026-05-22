from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from actuarial_cli_hub.runtime.artifacts import ArtifactRef, RunArtifacts
from actuarial_cli_hub.runtime.envelope import success_envelope


def write_catalog_import_outputs(
    *,
    query: str,
    source_path: Path | None,
    output_path: Path | None,
    diagnostics_path: Path | None,
    run_id: str,
) -> dict[str, Any]:
    source = _load_catalog_source(source_path) if source_path is not None else _default_catalog_source()
    entries = source["entries"]
    result = {
        "source": source["source"],
        "query": query,
        "entries": entries,
        "limitations": source["limitations"],
    }
    diagnostics = {
        "entry_count": len(entries),
        "runtime": "reference-only",
        "live_fetch": False,
        "source_path": str(source_path) if source_path is not None else None,
    }
    return _write_reference_payload(
        tool="actuarial.catalog.actuarial_foss",
        run_id=run_id,
        primary_id="run_manifest",
        primary_filename="run_manifest.json",
        primary_payload=result,
        output_path=output_path,
        diagnostics_path=diagnostics_path,
        diagnostics=diagnostics,
    )


def write_lda_search_outputs(*, query: str, output_path: Path | None, diagnostics_path: Path | None, run_id: str) -> dict[str, Any]:
    result = {
        "source": "Loss Data Analytics Materials",
        "query": query,
        "results": [
            {
                "title": "Loss Data Analytics online text",
                "url": "https://openacttexts.github.io/Loss-Data-Analytics/",
                "topics": ["loss severity", "frequency", "aggregate losses", "credibility", "risk measures"],
                "use": "Reference material for education, examples, and dataset discovery; not a deterministic calculation engine.",
            }
        ],
        "citation_note": "Check upstream license and cite the source when using material in reports.",
    }
    diagnostics = {"result_count": len(result["results"]), "runtime": "reference-only", "live_search": False}
    return _write_reference_payload(
        tool="actuarial.reference.loss_data_analytics",
        run_id=run_id,
        primary_id="reference_result",
        primary_filename="reference_result.json",
        primary_payload=result,
        output_path=output_path,
        diagnostics_path=diagnostics_path,
        diagnostics=diagnostics,
    )


def write_faslr_catalog_outputs(*, query: str, output_path: Path | None, diagnostics_path: Path | None, run_id: str) -> dict[str, Any]:
    result = {
        "source": "FASLR Reserving Workbench",
        "query": query,
        "capabilities": [
            "GUI-oriented reserving workflow",
            "Potential source for future public API spike",
            "Catalog/reference target until an executable CLI/API contract is proven",
        ],
        "upstream": "https://github.com/casact/FASLR",
        "execution_status": "not_executable_in_v1",
    }
    diagnostics = {"capability_count": len(result["capabilities"]), "runtime": "reference-only", "live_probe": False}
    return _write_reference_payload(
        tool="actuarial.reserve.faslr",
        run_id=run_id,
        primary_id="run_manifest",
        primary_filename="run_manifest.json",
        primary_payload=result,
        output_path=output_path,
        diagnostics_path=diagnostics_path,
        diagnostics=diagnostics,
    )


def _write_reference_payload(
    *,
    tool: str,
    run_id: str,
    primary_id: str,
    primary_filename: str,
    primary_payload: dict[str, Any],
    output_path: Path | None,
    diagnostics_path: Path | None,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    artifacts = RunArtifacts(run_id)
    refs: list[ArtifactRef] = []
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output_path, primary_payload)
        refs.append(ArtifactRef(id=primary_id, path=str(output_path)))
    else:
        refs.append(artifacts.write_json(primary_id, primary_filename, primary_payload))

    if diagnostics_path is not None:
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(diagnostics_path, diagnostics)
        refs.append(ArtifactRef(id="diagnostics", path=str(diagnostics_path)))
    else:
        refs.append(artifacts.write_json("diagnostics", "diagnostics.json", diagnostics))

    return success_envelope(
        tool=tool,
        run_id=run_id,
        data={"summary": diagnostics, "result": primary_payload},
        artifacts=[ref.to_dict() for ref in refs],
    ).to_dict()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_catalog_source() -> dict[str, Any]:
    return {
        "source": "actuarial-foss",
        "entries": [
            {
                "id": "chainladder-python",
                "domain": "reserving",
                "conversion_class": "python-library",
                "recommended_status": "implemented",
            },
            {
                "id": "aggregate",
                "domain": "aggregate_loss",
                "conversion_class": "python-dsl",
                "recommended_status": "implemented",
            },
            {
                "id": "FASLR",
                "domain": "reserving",
                "conversion_class": "application-spike",
                "recommended_status": "cataloged",
            },
        ],
        "limitations": [
            "This is a curated seed snapshot, not a live upstream scrape.",
            "Catalog entries require human license/runtime review before promotion.",
        ],
    }


def _load_catalog_source(source_path: Path) -> dict[str, Any]:
    if not source_path.is_file():
        raise ValueError(f"Catalog source does not exist or is not a file: {source_path}")

    if source_path.suffix.lower() == ".json":
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    else:
        import yaml

        try:
            raw = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Catalog source YAML is invalid: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Catalog source must be a mapping with source and entries fields.")
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Catalog source must include a non-empty entries list.")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError(f"Catalog source entry {index} must be a mapping with an id.")

    return {
        "source": str(raw.get("source") or source_path.stem),
        "entries": entries,
        "limitations": list(raw.get("limitations") or _default_catalog_source()["limitations"]),
    }
