from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable
from typing import Any

from jsonschema import Draft202012Validator

from .loader import ToolManifest, load_manifest, manifest_paths, schema_path, tools_dir


@dataclass(frozen=True)
class RegistryValidationError:
    path: str
    message: str
    json_path: str


@dataclass(frozen=True)
class RegistryValidationResult:
    ok: bool
    manifest_count: int
    errors: list[RegistryValidationError]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "manifest_count": self.manifest_count,
            "errors": [error.__dict__ for error in self.errors],
        }


def _json_path(parts: Iterable[str | int]) -> str:
    values = list(parts)
    if not values:
        return "$"
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in values)


def load_schema(root: Path | None = None) -> dict[str, Any]:
    return json.loads(schema_path(root).read_text(encoding="utf-8"))


def validate_manifest(manifest: ToolManifest, schema: dict[str, Any]) -> list[RegistryValidationError]:
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(manifest.data), key=lambda item: list(item.path)):
        errors.append(
            RegistryValidationError(
                path=str(manifest.path),
                message=error.message,
                json_path=_json_path(error.path),
            )
        )
    return errors


def validate_registry(root: Path | None = None) -> RegistryValidationResult:
    errors: list[RegistryValidationError] = []
    paths = manifest_paths(root)
    if not paths:
        return RegistryValidationResult(
            ok=False,
            manifest_count=0,
            errors=[RegistryValidationError(path=str(tools_dir(root)), message="No registry manifests found", json_path="$")],
        )

    try:
        schema = load_schema(root)
    except Exception as exc:
        return RegistryValidationResult(
            ok=False,
            manifest_count=len(paths),
            errors=[RegistryValidationError(path=str(schema_path(root)), message=str(exc), json_path="$")],
        )

    for path in paths:
        try:
            manifest = load_manifest(path)
        except Exception as exc:  # Keep CLI diagnostics explicit and bounded.
            errors.append(RegistryValidationError(path=str(path), message=str(exc), json_path="$"))
            continue
        errors.extend(validate_manifest(manifest, schema))
    return RegistryValidationResult(ok=not errors, manifest_count=len(paths), errors=errors)
