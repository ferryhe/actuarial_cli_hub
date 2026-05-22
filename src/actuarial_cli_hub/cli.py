from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any, Sequence

from actuarial_cli_hub import __version__
from actuarial_cli_hub.registry.loader import load_manifests
from actuarial_cli_hub.registry.validator import validate_registry
from actuarial_cli_hub.runtime.envelope import error_envelope, success_envelope
from actuarial_cli_hub.skills.generator import SUPPORTED_TARGETS


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="actuary",
        description="Contract-first CLI hub for actuarial open-source tools.",
    )
    parser.add_argument("--version", action="version", version=f"actuarial-cli-hub {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    registry = subparsers.add_parser("registry", help="Inspect and validate tool manifests.")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)

    registry_list = registry_sub.add_parser("list", help="List registered actuarial tools.")
    registry_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    registry_list.set_defaults(func=cmd_registry_list)

    registry_validate = registry_sub.add_parser("validate", help="Validate manifests against the registry schema.")
    registry_validate.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    registry_validate.set_defaults(func=cmd_registry_validate)

    doctor = subparsers.add_parser("doctor", help="Report core CLI readiness.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor.set_defaults(func=cmd_doctor)

    skills = subparsers.add_parser("skills", help="Export agent-facing skills and portable tool cards.")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_export = skills_sub.add_parser("export", help="Generate skill/tool-card files from registry metadata.")
    skills_export.add_argument(
        "--target",
        choices=SUPPORTED_TARGETS,
        default="generic",
        help="Export format to generate.",
    )
    skills_export.add_argument("--output", "--output-dir", dest="output_dir", required=True, help="Directory for generated files.")
    skills_export.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope.")
    skills_export.set_defaults(func=cmd_skills_export)

    reserve = subparsers.add_parser("reserve", help="Run reserving adapters.")
    reserve_sub = reserve.add_subparsers(dest="reserve_command", required=True)
    chainladder = reserve_sub.add_parser(
        "chainladder",
        help="Run deterministic chain-ladder reserving.",
        description="Run deterministic chain-ladder reserving.",
    )
    chainladder.add_argument("--input", required=True, help="Wide cumulative triangle CSV with an origin column.")
    chainladder.add_argument("--output", required=True, help="Path for deterministic_result JSON.")
    chainladder.add_argument("--diagnostics-output", required=True, help="Path for diagnostics JSON.")
    chainladder.add_argument("--explain-output", required=True, help="Path for explanation Markdown.")
    chainladder.add_argument("--run-id", default="chainladder", help="Run identifier for the stdout envelope.")
    chainladder.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope.")
    chainladder.set_defaults(func=cmd_reserve_chainladder)

    loss = subparsers.add_parser("loss", help="Run aggregate loss adapters.")
    loss_sub = loss.add_subparsers(dest="loss_command", required=True)
    aggregate = loss_sub.add_parser(
        "aggregate",
        help="Run an aggregate loss DSL declaration.",
        description="Run an aggregate loss DSL declaration with the aggregate package.",
    )
    aggregate.add_argument(
        "--decl",
        required=True,
        help="Aggregate DSL declaration, for example: agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1",
    )
    aggregate.add_argument("--output", required=True, help="Path for aggregate_result JSON.")
    aggregate.add_argument("--diagnostics-output", help="Optional path for diagnostics JSON; defaults beside --output.")
    aggregate.add_argument("--explain-output", required=True, help="Path for explanation Markdown.")
    aggregate.add_argument("--run-id", default="aggregate", help="Run identifier for the stdout envelope.")
    aggregate.add_argument("--log2", type=int, default=16, help="Aggregate grid log2 size.")
    aggregate.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope.")
    aggregate.set_defaults(func=cmd_loss_aggregate)

    cashflow = subparsers.add_parser("cashflow", help="Run cash-flow/model-runner adapters.")
    cashflow_sub = cashflow.add_subparsers(dest="cashflow_command", required=True)
    cashflower = cashflow_sub.add_parser(
        "cashflower",
        help="Run a cashflower model.py with YAML assumptions.",
        description="Run a cashflower model.py with generated input.py from YAML assumptions.",
    )
    cashflower.add_argument("--model", required=True, help="Path to a cashflower model.py file.")
    cashflower.add_argument("--assumptions", required=True, help="YAML assumptions/settings for the model run.")
    cashflower.add_argument("--output", required=True, help="Path for deterministic_result JSON.")
    cashflower.add_argument("--diagnostics-output", help="Optional path for diagnostics JSON; defaults beside --output.")
    cashflower.add_argument("--run-id", default="cashflower", help="Run identifier for the stdout envelope.")
    cashflower.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope.")
    cashflower.set_defaults(func=cmd_cashflow_cashflower)

    return parser


def cmd_registry_list(args: argparse.Namespace) -> int:
    manifests = load_manifests()
    tools = [
        {
            "id": item.tool_id,
            "name": item.name,
            "status": item.status,
            "priority": item.priority,
            "runtime_kind": item.runtime_kind,
            "runtime_availability": item.runtime_availability,
        }
        for item in manifests
    ]
    if args.json:
        emit_json({"tools": tools, "count": len(tools)})
    else:
        for tool in tools:
            print(f"{tool['id']}\t{tool['status']}\t{tool['runtime_availability']}")
    return 0


def cmd_registry_validate(args: argparse.Namespace) -> int:
    result = validate_registry()
    payload = result.to_dict()
    if args.json:
        emit_json(payload)
    elif result.ok:
        print(f"registry validation ok ({result.manifest_count} manifests)")
    else:
        for error in result.errors:
            print(f"{error.path} {error.json_path}: {error.message}", file=sys.stderr)
    return 0 if result.ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    validation = validate_registry()
    data = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "package_version": __version__,
        "registry_ok": validation.ok,
        "manifest_count": validation.manifest_count,
    }
    if validation.ok:
        payload = success_envelope(tool="actuarial_cli_hub.doctor", run_id="doctor", data=data).to_dict()
    else:
        payload = error_envelope(
            tool="actuarial_cli_hub.doctor",
            run_id="doctor",
            code="registry_invalid",
            message="Registry validation failed",
            details={"validation": validation.to_dict(), **data},
        ).to_dict()
    if args.json:
        emit_json(payload)
    else:
        print(f"actuarial-cli-hub {data['package_version']} on Python {data['python']}")
        print(f"registry_ok={data['registry_ok']} manifest_count={data['manifest_count']}")
    return 0 if validation.ok else 1


def cmd_skills_export(args: argparse.Namespace) -> int:
    from actuarial_cli_hub.skills.generator import export_skills

    try:
        exported = export_skills(target=args.target, output_dir=Path(args.output_dir))
    except ValueError as exc:
        payload = error_envelope(
            tool="actuarial_cli_hub.skills.export",
            run_id="skills-export",
            code="invalid_input",
            message=str(exc),
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 2

    files = sorted({str(item.path) for item in exported})
    tools = [item.tool_id for item in exported]
    data = {
        "target": args.target,
        "output_dir": str(Path(args.output_dir)),
        "count": len(exported),
        "tool_count": len(tools),
        "file_count": len(files),
        "files": files,
        "tools": tools,
    }
    payload = success_envelope(tool="actuarial_cli_hub.skills.export", run_id="skills-export", data=data).to_dict()
    if args.json:
        emit_json(payload)
    else:
        for file_path in data["files"]:
            print(file_path)
    return 0


def cmd_reserve_chainladder(args: argparse.Namespace) -> int:
    try:
        from actuarial_cli_hub.adapters.chainladder import write_chainladder_outputs

        payload = write_chainladder_outputs(
            input_path=Path(args.input),
            output_path=Path(args.output),
            diagnostics_path=Path(args.diagnostics_output),
            explanation_path=Path(args.explain_output),
            run_id=args.run_id,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"chainladder", "pandas"}:
            raise
        payload = error_envelope(
            tool="actuarial.reserve.chainladder",
            run_id=args.run_id,
            code="runtime_missing",
            message="The chainladder runtime is not installed. Install with: pip install 'actuarial-cli-hub[chainladder]'",
            details={"missing_module": exc.name},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    except ValueError as exc:
        payload = error_envelope(
            tool="actuarial.reserve.chainladder",
            run_id=args.run_id,
            code="invalid_input",
            message=str(exc),
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        payload = error_envelope(
            tool="actuarial.reserve.chainladder",
            run_id=args.run_id,
            code="invalid_input",
            message=f"Could not read triangle input: {exc}",
            details={"input_path": args.input},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    if args.json:
        emit_json(payload)
    else:
        summary = payload["data"]["summary"]
        print(
            "chainladder ultimate="
            f"{summary['ultimate']} latest={summary['latest']} ibnr={summary['ibnr']}"
        )
    return 0


def cmd_loss_aggregate(args: argparse.Namespace) -> int:
    try:
        from actuarial_cli_hub.adapters.aggregate import write_aggregate_outputs

        payload = write_aggregate_outputs(
            declaration=args.decl,
            output_path=Path(args.output),
            diagnostics_path=Path(args.diagnostics_output) if args.diagnostics_output else None,
            explanation_path=Path(args.explain_output),
            run_id=args.run_id,
            log2=args.log2,
        )
    except ModuleNotFoundError as exc:
        if exc.name not in {"aggregate", "pandas", "numpy", "scipy"}:
            raise
        payload = error_envelope(
            tool="actuarial.loss.aggregate",
            run_id=args.run_id,
            code="runtime_missing",
            message="The aggregate runtime is not installed. Install with: pip install 'actuarial-cli-hub[aggregate]'",
            details={"missing_module": exc.name},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    except ValueError as exc:
        payload = error_envelope(
            tool="actuarial.loss.aggregate",
            run_id=args.run_id,
            code="invalid_input",
            message=str(exc),
            details={"declaration": args.decl},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        payload = error_envelope(
            tool="actuarial.loss.aggregate",
            run_id=args.run_id,
            code="upstream_failure",
            message=f"aggregate runtime failed: {exc}",
            details={"declaration": args.decl},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    if args.json:
        emit_json(payload)
    else:
        summary = payload["data"]["summary"]
        print(
            "aggregate expected_loss="
            f"{summary['expected_loss']} cv={summary['coefficient_of_variation']}"
        )
    return 0

def cmd_cashflow_cashflower(args: argparse.Namespace) -> int:
    try:
        from actuarial_cli_hub.adapters.cashflower import write_cashflower_outputs

        payload = write_cashflower_outputs(
            model_path=Path(args.model),
            assumptions_path=Path(args.assumptions),
            output_path=Path(args.output),
            diagnostics_path=Path(args.diagnostics_output) if args.diagnostics_output else None,
            run_id=args.run_id,
        )
    except ModuleNotFoundError as exc:
        if exc.name in {"cashflower", "pandas", "numpy", "networkx", "yaml"}:
            payload = error_envelope(
                tool="actuarial.cashflow.cashflower",
                run_id=args.run_id,
                code="runtime_missing",
                message="The cashflower runtime is not installed. Install with: pip install 'actuarial-cli-hub[cashflower]'",
                details={"missing_module": exc.name},
            ).to_dict()
        else:
            payload = error_envelope(
                tool="actuarial.cashflow.cashflower",
                run_id=args.run_id,
                code="upstream_failure",
                message=f"cashflower model dependency is missing: {exc.name}",
                details={"missing_module": exc.name, "model": args.model, "assumptions": args.assumptions},
            ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        payload = error_envelope(
            tool="actuarial.cashflow.cashflower",
            run_id=args.run_id,
            code="invalid_input",
            message=str(exc),
            details={"model": args.model, "assumptions": args.assumptions},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        payload = error_envelope(
            tool="actuarial.cashflow.cashflower",
            run_id=args.run_id,
            code="upstream_failure",
            message=f"cashflower runtime failed: {exc}",
            details={"model": args.model, "assumptions": args.assumptions},
        ).to_dict()
        if args.json:
            emit_json(payload)
        else:
            print(payload["error"]["message"], file=sys.stderr)
        return 2
    if args.json:
        emit_json(payload)
    else:
        summary = payload["data"]["summary"]
        print(f"cashflower rows={payload['data']['row_count']} final_t={summary['final_t']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))
