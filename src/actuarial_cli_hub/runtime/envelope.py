from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

EnvelopeStatus = Literal["success", "error"]


@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Envelope:
    """Stable v1 JSON envelope for CLI responses and future adapters."""

    schema_version: str
    status: EnvelopeStatus
    tool: str
    run_id: str
    created_at: str
    data: dict[str, Any] | None = None
    error: ErrorDetail | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.error is None:
            payload.pop("error")
        if self.data is None:
            payload.pop("data")
        return payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def success_envelope(
    *,
    tool: str,
    run_id: str,
    data: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> Envelope:
    return Envelope(
        schema_version="actuarial-cli-envelope.v1",
        status="success",
        tool=tool,
        run_id=run_id,
        created_at=utc_now_iso(),
        data=data or {},
        artifacts=artifacts or [],
    )


def error_envelope(*, tool: str, run_id: str, code: str, message: str, details: dict[str, Any] | None = None) -> Envelope:
    return Envelope(
        schema_version="actuarial-cli-envelope.v1",
        status="error",
        tool=tool,
        run_id=run_id,
        created_at=utc_now_iso(),
        error=ErrorDetail(code=code, message=message, details=details or {}),
    )
