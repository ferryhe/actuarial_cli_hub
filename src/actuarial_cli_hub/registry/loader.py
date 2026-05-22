from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import site
import sys
import sysconfig
from typing import Any

import yaml


@dataclass(frozen=True)
class ToolManifest:
    """Small typed wrapper around the registry YAML document."""

    path: Path
    data: dict[str, Any]

    @property
    def tool_id(self) -> str:
        return str(self.data["id"])

    @property
    def name(self) -> str:
        return str(self.data["name"])

    @property
    def status(self) -> str:
        return str(self.data["status"])

    @property
    def priority(self) -> str:
        return str(self.data["priority"])

    @property
    def runtime_kind(self) -> str:
        return str(self.data["runtime"]["kind"])

    @property
    def runtime_availability(self) -> str:
        return str(self.data["runtime"]["availability"])


def repo_root() -> Path:
    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "registry" / "tools").is_dir():
        return source_root

    for installed_root in _installed_data_roots():
        if (installed_root / "registry" / "tools").is_dir():
            return installed_root

    return source_root


def _installed_data_roots() -> list[Path]:
    roots = [Path(sys.prefix)]
    data_path = sysconfig.get_path("data")
    if data_path:
        roots.append(Path(data_path))
    try:
        roots.append(Path(site.getuserbase()))
    except Exception:
        pass

    unique_roots: list[Path] = []
    for root in roots:
        if root not in unique_roots:
            unique_roots.append(root)
    return unique_roots


def registry_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "registry"


def schema_path(root: Path | None = None) -> Path:
    return registry_root(root) / "schemas" / "tool-manifest.schema.json"


def tools_dir(root: Path | None = None) -> Path:
    return registry_root(root) / "tools"


def manifest_paths(root: Path | None = None) -> list[Path]:
    path = tools_dir(root)
    return sorted(path.glob("*.yaml"))


def load_manifest(path: Path) -> ToolManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping")
    return ToolManifest(path=path, data=data)


def load_manifests(root: Path | None = None) -> list[ToolManifest]:
    return [load_manifest(path) for path in manifest_paths(root)]
