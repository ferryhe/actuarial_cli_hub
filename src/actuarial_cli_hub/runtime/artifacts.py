from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactRef:
    id: str
    path: str
    media_type: str = "application/json"

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "path": self.path, "media_type": self.media_type}


class RunArtifacts:
    """Filesystem helper for canonical run outputs.

    The canonical root is `.tmp/actuarial-cli-runs/<run_id>/` and all produced
    artifacts live under `output/`.
    """

    def __init__(self, run_id: str, root: Path | None = None) -> None:
        self.run_id = run_id
        self.root = root or Path(".tmp") / "actuarial-cli-runs" / run_id
        self.output_dir = self.root / "output"

    def ensure(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def output_path(self, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError("artifact filename must not contain directories")
        return self.output_dir / filename

    def write_json(self, artifact_id: str, filename: str, payload: dict[str, Any]) -> ArtifactRef:
        self.ensure()
        path = self.output_path(filename)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ArtifactRef(id=artifact_id, path=str(path))
