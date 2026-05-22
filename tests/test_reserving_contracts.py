from __future__ import annotations

import pytest
from pathlib import Path

from actuarial_cli_hub.adapters.chainladder import deterministic_chainladder, load_wide_triangle


def test_sample_triangle_projects_all_origins() -> None:
    triangle = load_wide_triangle(Path("examples/reserving/sample_triangle.csv"))
    result = deterministic_chainladder(triangle)

    assert result["development_ages"] == ["12", "24", "36", "48", "60"]
    assert result["selected_age_to_age_factors"][-1] > 1.0
    assert [item["origin"] for item in result["origins"]] == ["2020", "2021", "2022", "2023", "2024"]
    assert result["totals"]["ibnr"] > 0


def test_triangle_csv_requires_origin_header(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("year,12,24\n2020,1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="origin"):
        load_wide_triangle(path)
