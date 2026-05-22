from __future__ import annotations

import json
from pathlib import Path

from actuarial_cli_hub.adapters.aggregate import build_aggregate_result, normalize_declaration, write_aggregate_outputs

ROADMAP_DECL = "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1"


def test_aggregate_declaration_normalizes_roadmap_shorthand() -> None:
    assert normalize_declaration(ROADMAP_DECL) == f"{ROADMAP_DECL} poisson"
    assert normalize_declaration(f"{ROADMAP_DECL} poisson") == f"{ROADMAP_DECL} poisson"
    assert normalize_declaration(f"{ROADMAP_DECL} negbin 2") == f"{ROADMAP_DECL} negbin 2"
    assert normalize_declaration(f"{ROADMAP_DECL} mixed gamma 0.4") == f"{ROADMAP_DECL} mixed gamma 0.4"
    assert normalize_declaration("agg One 1 claim dsev [1]") == "agg One 1 claim dsev [1] poisson"
    assert normalize_declaration("agg B.Basic03 dfreq [1:3] dsev [1 2 10]") == "agg B.Basic03 dfreq [1:3] dsev [1 2 10]"
    assert normalize_declaration("agg Premium 1000 prem at 0.6 lr sev gamma 100 cv 1") == "agg Premium 1000 prem at 0.6 lr sev gamma 100 cv 1 poisson"


def test_aggregate_declaration_validation_ignores_line_name_tokens() -> None:
    try:
        normalize_declaration("agg Premium 100 sev lognorm 50 cv 1")
    except ValueError as exc:
        assert "frequency/exposure" in str(exc)
    else:  # pragma: no cover - defensive clarity for this regression test.
        raise AssertionError("line names must not satisfy exposure validation")


def test_aggregate_result_contract_contains_summary_and_quantiles() -> None:
    result = build_aggregate_result(ROADMAP_DECL, log2=16)

    assert result["method"] == "aggregate.build"
    assert result["name"] == "MyLine"
    assert result["summary"]["expected_loss"] > 0
    assert result["summary"]["standard_deviation"] > 0
    assert result["statistics"]["name"] == "MyLine"
    assert result["statistics_rows"] == [result["statistics"]]
    assert set(result["quantiles"]) == {"p50", "p75", "p90", "p95", "p99"}


def test_aggregate_result_preserves_vectorized_statistics_rows() -> None:
    result = build_aggregate_result("agg Test [100 200] claims 1000 xs 0 sev lognorm 50 cv 1", log2=16)

    assert result["summary"]["expected_loss"] > 0
    assert len(result["statistics_rows"]) == 2
    assert result["statistics_rows"][0]["freq_m"] == 100.0
    assert result["statistics_rows"][1]["freq_m"] == 200.0


def test_aggregate_output_envelope_uses_contract_artifact_ids(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    explanation = tmp_path / "explanation.md"

    envelope = write_aggregate_outputs(
        declaration=ROADMAP_DECL,
        output_path=output,
        explanation_path=explanation,
        run_id="aggregate-test",
    )

    assert envelope["schema_version"] == "actuarial-cli-envelope.v1"
    assert envelope["status"] == "success"
    assert envelope["run_id"] == "aggregate-test"
    assert {artifact["id"] for artifact in envelope["artifacts"]} == {
        "aggregate_result",
        "diagnostics",
        "explanation_markdown",
    }
    assert output.exists()
    assert explanation.exists()


def test_aggregate_default_diagnostics_path_does_not_overwrite_result(tmp_path: Path) -> None:
    output = tmp_path / "diagnostics.json"
    explanation = tmp_path / "explanation.md"

    envelope = write_aggregate_outputs(
        declaration=ROADMAP_DECL,
        output_path=output,
        explanation_path=explanation,
        run_id="aggregate-test",
    )

    artifact_paths = {artifact["id"]: Path(artifact["path"]) for artifact in envelope["artifacts"]}
    assert artifact_paths["aggregate_result"] == output
    assert artifact_paths["diagnostics"] == tmp_path / "aggregate_diagnostics.json"
    assert artifact_paths["aggregate_result"] != artifact_paths["diagnostics"]
    assert output.exists()
    assert artifact_paths["diagnostics"].exists()


def test_aggregate_outputs_strict_json_for_unbounded_declarations(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    explanation = tmp_path / "explanation.md"

    write_aggregate_outputs(
        declaration="agg One 1 claim dsev [1]",
        output_path=output,
        explanation_path=explanation,
        run_id="aggregate-test",
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["statistics"]["limit"] is None
