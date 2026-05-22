from __future__ import annotations

import importlib.metadata
import json
import math
from pathlib import Path
from typing import Any

from actuarial_cli_hub.runtime.envelope import success_envelope

TOOL_ID = "actuarial.loss.aggregate"
DEFAULT_FREQUENCY = "poisson"


def normalize_declaration(declaration: str) -> str:
    """Return a parser-ready aggregate DSL declaration.

    The roadmap fixture uses a compact ``... claims ... sev ...`` shorthand that
    older aggregate examples accepted informally. aggregate==0.30.x expects an
    explicit frequency family after the severity clause, so default the compact
    form to Poisson while leaving declarations that already specify a frequency
    family untouched.
    """
    text = " ".join(declaration.split())
    if not text:
        raise ValueError("aggregate declaration must not be empty")
    if not text.startswith("agg "):
        raise ValueError("aggregate declaration must start with 'agg '")

    tokens = text.split()
    normalized_tokens = [token.lower() for token in tokens]
    body_tokens = normalized_tokens[2:]
    exposure_tokens = {"claims", "claim", "loss", "prem", "premium", "exposure"}
    frequency_tokens = {
        "dfreq",
        "fixed",
        "poisson",
        "bernoulli",
        "binomial",
        "geometric",
        "pascal",
        "negbin",
        "logarithmic",
        "neyman",
        "neymana",
        "mixed",
    }
    if not ({*exposure_tokens, "dfreq"} & set(body_tokens)):
        raise ValueError("aggregate declaration must include a frequency/exposure clause")
    has_severity = any(token in {"sev", "dsev"} or token.startswith(("sev.", "dsev")) for token in body_tokens)
    if not has_severity:
        raise ValueError("aggregate declaration must include a severity clause")

    # Append a default only for the compact roadmap form. Explicit aggregate
    # frequency families, discrete frequency declarations (dfreq), and
    # parameterized forms such as ``negbin 2`` are passed through unchanged.
    return text if set(body_tokens) & frequency_tokens else f"{text} {DEFAULT_FREQUENCY}"


def aggregate_version() -> str:
    try:
        return importlib.metadata.version("aggregate")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def build_aggregate_result(declaration: str, *, log2: int = 16) -> dict[str, Any]:
    import aggregate

    normalized_declaration = normalize_declaration(declaration)
    try:
        model = aggregate.build(normalized_declaration, log2=log2)
    except AssertionError as exc:
        message = str(exc) or "aggregate parser rejected the declaration"
        raise ValueError(message) from exc
    statistics = _first_record(model.statistics_df)
    statistics_rows = _records(model.statistics_df)
    report = _report_summary(model.report_df)
    quantiles = _quantile_summary(model.density_df)

    return {
        "method": "aggregate.build",
        "declaration": declaration,
        "normalized_declaration": normalized_declaration,
        "name": str(getattr(model, "name", statistics.get("name", "aggregate"))),
        "log2": log2,
        "summary": {
            "expected_loss": _rounded(getattr(model, "agg_m", statistics.get("agg_m"))),
            "standard_deviation": _rounded(getattr(model, "agg_sd", statistics.get("agg_sd"))),
            "coefficient_of_variation": _rounded(getattr(model, "agg_cv", statistics.get("agg_cv"))),
        },
        "statistics": statistics,
        "statistics_rows": statistics_rows,
        "report": report,
        "quantiles": quantiles,
    }


def write_aggregate_outputs(
    *,
    declaration: str,
    output_path: Path,
    diagnostics_path: Path | None = None,
    explanation_path: Path,
    run_id: str,
    log2: int = 16,
) -> dict[str, Any]:
    result = build_aggregate_result(declaration, log2=log2)
    diagnostics = {
        "aggregate_package_version": aggregate_version(),
        "declaration_was_normalized": result["declaration"] != result["normalized_declaration"],
        "note": "Uses aggregate.build on a DSL declaration; outputs are demonstration artifacts.",
    }
    result["diagnostics"] = diagnostics
    diagnostics_path = diagnostics_path or _default_diagnostics_path(output_path)
    explanation = (
        "# Aggregate Loss Result\n\n"
        "This wrapper builds an aggregate loss distribution using the public "
        "aggregate.build DSL entry point. The roadmap shorthand defaults to a "
        "Poisson claim count when no frequency family is supplied. Outputs are "
        "deterministic demo artifacts and require qualified actuarial review "
        "before business use.\n\n"
        f"Declaration: `{result['declaration']}`\n\n"
        f"Normalized declaration: `{result['normalized_declaration']}`\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    explanation_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dumps(result), encoding="utf-8")
    diagnostics_path.write_text(_json_dumps(diagnostics), encoding="utf-8")
    explanation_path.write_text(explanation, encoding="utf-8")

    return success_envelope(
        tool=TOOL_ID,
        run_id=run_id,
        data={"summary": result["summary"], "method": result["method"]},
        artifacts=[
            {"id": "aggregate_result", "path": str(output_path), "media_type": "application/json"},
            {"id": "diagnostics", "path": str(diagnostics_path), "media_type": "application/json"},
            {"id": "explanation_markdown", "path": str(explanation_path), "media_type": "text/markdown"},
        ],
    ).to_dict()


def _first_record(frame: Any) -> dict[str, Any]:
    records = _records(frame)
    return records[0] if records else {}


def _records(frame: Any) -> list[dict[str, Any]]:
    records = frame.to_dict(orient="records")
    if not records:
        return []
    return [{str(key): _json_scalar(value) for key, value in record.items()} for record in records]


def _default_diagnostics_path(output_path: Path) -> Path:
    candidate = output_path.parent / "diagnostics.json"
    if candidate == output_path:
        return output_path.parent / "aggregate_diagnostics.json"
    return candidate


def _report_summary(frame: Any) -> dict[str, Any]:
    if frame is None:
        return {}
    report: dict[str, Any] = {}
    for row_name in ["freq_m", "sev_m", "sev_cv", "agg_m", "agg_cv", "agg_skew"]:
        try:
            row = frame.loc[row_name]
        except KeyError:
            continue
        report[row_name] = {str(key): _json_scalar(value) for key, value in row.to_dict().items()}
    return report


def _quantile_summary(frame: Any) -> dict[str, float]:
    if frame is None or frame.empty:
        return {}
    quantiles: dict[str, float] = {}
    for probability in (0.5, 0.75, 0.9, 0.95, 0.99):
        candidates = frame[frame["F"] >= probability]
        if candidates.empty:
            loss = frame.iloc[-1]["loss"]
        else:
            loss = candidates.iloc[0]["loss"]
        quantiles[f"p{int(probability * 100)}"] = _rounded(loss)
    return quantiles


def _json_scalar(value: Any) -> Any:
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except (ModuleNotFoundError, TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return _rounded(value)
    return value


def _rounded(value: Any) -> float:
    return round(float(value), 6)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"
