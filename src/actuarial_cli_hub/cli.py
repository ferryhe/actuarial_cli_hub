from __future__ import annotations

import argparse
import json
import platform
import sys
from typing import Any, Sequence

from actuarial_cli_hub import __version__
from actuarial_cli_hub.registry.loader import load_manifests
from actuarial_cli_hub.registry.validator import validate_registry
from actuarial_cli_hub.runtime.envelope import error_envelope, success_envelope


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))
