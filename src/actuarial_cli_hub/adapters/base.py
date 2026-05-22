from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from actuarial_cli_hub.runtime.envelope import Envelope


@dataclass(frozen=True)
class AdapterContext:
    tool_id: str
    run_id: str


class ActuarialAdapter(ABC):
    """Minimal base contract for future actuarial wrappers."""

    tool_id: str

    @abstractmethod
    def run(self, payload: dict[str, Any], context: AdapterContext) -> Envelope:
        """Run the adapter and return a v1 envelope."""
