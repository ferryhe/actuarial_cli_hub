from __future__ import annotations

import contextlib
import datetime as dt
import importlib.metadata
import io
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from actuarial_cli_hub.runtime.envelope import success_envelope

TOOL_ID = "actuarial.cashflow.cashflower"


def cashflower_version() -> str:
    try:
        return importlib.metadata.version("cashflower")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def load_assumptions(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("assumptions file must contain a YAML mapping")
    settings = data.get("settings", {})
    if settings is None:
        data["settings"] = {}
    elif not isinstance(settings, dict):
        raise ValueError("assumptions.settings must be a mapping when provided")
    values = data.get("assumptions", {})
    if values is None:
        data["assumptions"] = {}
    elif not isinstance(values, dict):
        raise ValueError("assumptions.assumptions must be a mapping when provided")
    return data


def run_cashflower_model(*, model_path: Path, assumptions_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    import cashflower

    if not model_path.is_file():
        raise ValueError(f"model file does not exist: {model_path}")
    if model_path.suffix != ".py":
        raise ValueError("model file must be a Python .py file")
    if not assumptions_path.is_file():
        raise ValueError(f"assumptions file does not exist: {assumptions_path}")

    assumptions = load_assumptions(assumptions_path)
    settings = {
        "SAVE_OUTPUT": False,
        "SAVE_DIAGNOSTIC": True,
        **assumptions.get("settings", {}),
    }
    values = assumptions.get("assumptions", {})
    model_points = assumptions.get("model_points")
    runplan = assumptions.get("runplan")

    with tempfile.TemporaryDirectory(prefix="actuarial-cashflower-") as tmp:
        work_dir = Path(tmp)
        shutil.copytree(
            model_path.parent,
            work_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "output"),
        )
        if model_path.name != "model.py":
            shutil.copyfile(model_path, work_dir / "model.py")
        (work_dir / "input.py").write_text(_input_module(values, model_points, runplan), encoding="utf-8")
        output, diagnostic, logs = _run_cashflower_in_directory(cashflower, work_dir, settings)

    records = _frame_records(output)
    diagnostic_records = _frame_records(diagnostic) if diagnostic is not None else []
    result = {
        "method": "cashflower.run",
        "model": str(model_path),
        "assumptions": str(assumptions_path),
        "settings": settings,
        "row_count": len(records),
        "columns": list(output.columns) if output is not None else [],
        "records": records,
        "summary": _summary(records),
    }
    diagnostics = {
        "cashflower_package_version": cashflower_version(),
        "diagnostic_rows": len(diagnostic_records),
        "diagnostic_records": diagnostic_records,
        "log_tail": [str(item) for item in logs[-20:]],
        "note": "Runs a user-supplied cashflower model.py with generated input.py from YAML assumptions.",
    }
    return result, diagnostics


def write_cashflower_outputs(
    *,
    model_path: Path,
    assumptions_path: Path,
    output_path: Path,
    diagnostics_path: Path | None,
    run_id: str,
) -> dict[str, Any]:
    result, diagnostics = run_cashflower_model(model_path=model_path, assumptions_path=assumptions_path)
    result["diagnostics"] = diagnostics
    diagnostics_path = diagnostics_path or _default_diagnostics_path(output_path)
    if output_path.resolve() == diagnostics_path.resolve():
        raise ValueError("diagnostics output path must differ from deterministic result output path")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dumps(result), encoding="utf-8")
    diagnostics_path.write_text(_json_dumps(diagnostics), encoding="utf-8")

    return success_envelope(
        tool=TOOL_ID,
        run_id=run_id,
        data={"summary": result["summary"], "method": result["method"], "row_count": result["row_count"]},
        artifacts=[
            {"id": "deterministic_result", "path": str(output_path), "media_type": "application/json"},
            {"id": "diagnostics", "path": str(diagnostics_path), "media_type": "application/json"},
        ],
    ).to_dict()


def _run_cashflower_in_directory(cashflower: Any, work_dir: Path, settings: dict[str, Any]) -> tuple[Any, Any, list[Any]]:
    previous_cwd = Path.cwd()
    old_path = list(sys.path)
    old_modules = dict(sys.modules)
    project_module_names = _project_module_names(work_dir)
    for name in list(sys.modules):
        if _is_project_module_name(name, project_module_names):
            sys.modules.pop(name, None)
    try:
        sys.path.insert(0, str(work_dir))
        import os

        os.chdir(work_dir)
        captured_stdout = io.StringIO()
        with contextlib.redirect_stdout(captured_stdout):
            output, diagnostic, logs = cashflower.run(settings=settings, path=str(work_dir))
        if output is None:
            raise ValueError("cashflower did not return an output table")
        return output, diagnostic, [*logs, captured_stdout.getvalue()]
    finally:
        import os

        os.chdir(previous_cwd)
        sys.path[:] = old_path
        _restore_modules_after_temp_run(old_modules, work_dir, project_module_names)


def _project_module_names(work_dir: Path) -> set[str]:
    names = {"input", "model"}
    names.update(path.stem for path in work_dir.glob("*.py") if path.stem.isidentifier())
    names.update(path.name for path in work_dir.iterdir() if (path / "__init__.py").is_file() and path.name.isidentifier())
    return names


def _restore_modules_after_temp_run(old_modules: dict[str, Any], work_dir: Path, project_module_names: set[str]) -> None:
    """Remove modules imported from a temporary cashflower project.

    Cashflower imports user files by plain names such as ``model`` and
    ``input``. User models can also import sibling helpers. Without removing
    every module loaded from the temp copy, a later in-process run can reuse a
    stale helper from a different model directory.
    """
    work_root = work_dir.resolve()
    for name, module in list(sys.modules.items()):
        if name in old_modules:
            continue
        module_file = getattr(module, "__file__", None)
        if module_file and _is_relative_to(Path(module_file).resolve(), work_root):
            sys.modules.pop(name, None)
    for name in list(sys.modules):
        if _is_project_module_name(name, project_module_names) and name not in old_modules:
            sys.modules.pop(name, None)
    for name, old_module in old_modules.items():
        if _is_project_module_name(name, project_module_names):
            sys.modules[name] = old_module


def _is_project_module_name(name: str, project_module_names: set[str]) -> bool:
    return any(name == project_name or name.startswith(f"{project_name}.") for project_name in project_module_names)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _input_module(assumptions: dict[str, Any], model_points: Any, runplan: Any) -> str:
    lines = ["import datetime", "from cashflower import ModelPointSet, Runplan", "import pandas as pd", ""]
    lines.append(f"assumptions = {_safe_repr(assumptions)}")
    if model_points is not None:
        if not isinstance(model_points, list) or not all(isinstance(item, dict) for item in model_points):
            raise ValueError("model_points must be a list of mappings when provided")
        lines.append(f"policy = ModelPointSet(data=pd.DataFrame({_safe_repr(model_points)}))")
    if runplan is not None:
        if not isinstance(runplan, list) or not all(isinstance(item, dict) for item in runplan):
            raise ValueError("runplan must be a list of mappings when provided")
        lines.append(f"runplan = Runplan(data=pd.DataFrame({_safe_repr(runplan)}))")
    lines.append("")
    return "\n".join(lines)


def _safe_repr(value: Any) -> str:
    return repr(value)


def _frame_records(frame: Any) -> list[dict[str, Any]]:
    records = frame.to_dict(orient="records")
    return [{str(key): _json_scalar(value) for key, value in record.items()} for record in records]


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"final_t": None, "numeric_totals": {}}
    final = records[-1]
    totals: dict[str, float] = {}
    for key in records[0]:
        values = [record.get(key) for record in records]
        if all(isinstance(value, (int, float)) for value in values):
            totals[key] = round(sum(float(value) for value in values if value is not None), 6)
    return {"final_t": final.get("t"), "final_record": final, "numeric_totals": totals}


def _default_diagnostics_path(output_path: Path) -> Path:
    candidate = output_path.parent / "diagnostics.json"
    if candidate == output_path:
        return output_path.parent / "cashflower_diagnostics.json"
    return candidate


def _json_scalar(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except (ModuleNotFoundError, TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, 6)
    return value


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"
