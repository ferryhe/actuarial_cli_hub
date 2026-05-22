from __future__ import annotations

import csv
import importlib.metadata
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actuarial_cli_hub.runtime.envelope import success_envelope


@dataclass(frozen=True)
class Triangle:
    origins: list[str]
    development_ages: list[str]
    values: list[list[float | None]]


def _parse_number(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    number = float(text)
    if math.isnan(number):
        return None
    return number


def load_wide_triangle(path: Path) -> Triangle:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("triangle CSV is empty") from exc
        if len(header) < 3:
            raise ValueError("triangle CSV must include origin plus at least two development columns")
        if header[0].strip().lower() != "origin":
            raise ValueError("first triangle CSV column must be 'origin'")

        development_ages = [item.strip() for item in header[1:]]
        origins: list[str] = []
        rows: list[list[float | None]] = []
        for row_number, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(header):
                raise ValueError(f"row {row_number} has {len(row)} columns; expected {len(header)}")
            origins.append(row[0].strip())
            rows.append([_parse_number(value) for value in row[1:]])

    if not rows:
        raise ValueError("triangle CSV has no data rows")
    return Triangle(origins=origins, development_ages=development_ages, values=rows)


def _latest_observation(row: list[float | None], development_ages: list[str]) -> tuple[str, float]:
    for index in range(len(row) - 1, -1, -1):
        value = row[index]
        if value is not None:
            return development_ages[index], value
    raise ValueError("each triangle row must contain at least one observed value")


def selected_age_to_age_factors(triangle: Triangle) -> list[float]:
    factors: list[float] = []
    for index in range(len(triangle.development_ages) - 1):
        current_sum = 0.0
        next_sum = 0.0
        for row in triangle.values:
            current = row[index]
            following = row[index + 1]
            if current is None or following is None:
                continue
            current_sum += current
            next_sum += following
        if current_sum <= 0 or next_sum <= 0:
            factors.append(1.0)
        else:
            factors.append(next_sum / current_sum)
    return factors


def _to_chainladder_triangle(triangle: Triangle) -> Any:
    import chainladder as cl
    import pandas as pd

    records: list[dict[str, Any]] = []
    for origin, row in zip(triangle.origins, triangle.values, strict=True):
        origin_start = pd.Timestamp(f"{origin}-01-01")
        for age_text, value in zip(triangle.development_ages, row, strict=True):
            if value is None:
                continue
            age_months = int(age_text)
            records.append(
                {
                    "origin": origin_start,
                    "valuation": origin_start + pd.DateOffset(months=age_months - 1),
                    "paid": value,
                }
            )
    frame = pd.DataFrame(records)
    return cl.Triangle(frame, origin="origin", development="valuation", columns="paid", cumulative=True)


def _triangle_frame_values(chainladder_triangle: Any) -> dict[str, float]:
    import pandas as pd

    frame = chainladder_triangle.to_frame().iloc[:, 0]
    values: dict[str, float] = {}
    for index, value in frame.items():
        origin = str(getattr(index, "year", index))
        if pd.isna(value):
            values[origin] = 0.0
        else:
            values[origin] = float(value)
    return values


def _selected_ldfs(model: Any, expected_count: int) -> list[float]:
    frame = model.ldf_.to_frame().iloc[0]
    return [float(value) for value in frame.iloc[:expected_count]]


def deterministic_chainladder(triangle: Triangle) -> dict[str, Any]:
    import chainladder as cl

    chainladder_triangle = _to_chainladder_triangle(triangle)
    model = cl.Chainladder().fit(chainladder_triangle)
    ultimate_by_origin = _triangle_frame_values(model.ultimate_)
    ibnr_by_origin = _triangle_frame_values(model.ibnr_)
    factors = _selected_ldfs(model, len(triangle.development_ages) - 1)
    origin_results: list[dict[str, Any]] = []
    for origin, row in zip(triangle.origins, triangle.values, strict=True):
        latest_age, latest_value = _latest_observation(row, triangle.development_ages)
        ultimate = ultimate_by_origin[origin]
        ibnr = ibnr_by_origin.get(origin, ultimate - latest_value)
        if math.isnan(ibnr):
            ibnr = 0.0
        cumulative_factor = ultimate / latest_value if latest_value else 1.0
        origin_results.append(
            {
                "origin": origin,
                "latest_development_age": latest_age,
                "latest": round(latest_value, 6),
                "cumulative_development_factor": round(cumulative_factor, 8),
                "ultimate": round(ultimate, 6),
                "ibnr": round(ibnr, 6),
            }
        )

    total_latest = sum(item["latest"] for item in origin_results)
    total_ultimate = sum(item["ultimate"] for item in origin_results)
    return {
        "method": "chainladder.Chainladder",
        "development_ages": triangle.development_ages,
        "selected_age_to_age_factors": [round(factor, 8) for factor in factors],
        "origins": origin_results,
        "totals": {
            "latest": round(total_latest, 6),
            "ultimate": round(total_ultimate, 6),
            "ibnr": round(total_ultimate - total_latest, 6),
        },
    }


def chainladder_version() -> str:
    try:
        return importlib.metadata.version("chainladder")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def write_chainladder_outputs(
    *,
    input_path: Path,
    output_path: Path,
    diagnostics_path: Path,
    explanation_path: Path,
    run_id: str,
) -> dict[str, Any]:
    triangle = load_wide_triangle(input_path)
    result = deterministic_chainladder(triangle)
    diagnostics = {
        "input_path": str(input_path),
        "origin_count": len(triangle.origins),
        "development_age_count": len(triangle.development_ages),
        "chainladder_package_version": chainladder_version(),
        "note": "Uses chainladder.Chainladder on a cumulative wide-triangle fixture.",
    }
    explanation = (
        "# Chainladder Reserving Result\n\n"
        "This wrapper reads a cumulative wide triangle CSV, builds a chainladder "
        "Triangle, runs the public chainladder.Chainladder estimator, and projects "
        "each origin to ultimate. Outputs are deterministic demo artifacts and "
        "require qualified actuarial review before business use.\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    explanation_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dumps(result), encoding="utf-8")
    diagnostics_path.write_text(_json_dumps(diagnostics), encoding="utf-8")
    explanation_path.write_text(explanation, encoding="utf-8")

    return success_envelope(
        tool="actuarial.reserve.chainladder",
        run_id=run_id,
        data={"summary": result["totals"], "method": result["method"]},
        artifacts=[
            {"id": "deterministic_result", "path": str(output_path), "media_type": "application/json"},
            {"id": "diagnostics", "path": str(diagnostics_path), "media_type": "application/json"},
            {"id": "explanation_markdown", "path": str(explanation_path), "media_type": "text/markdown"},
        ],
    ).to_dict()


def _json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
