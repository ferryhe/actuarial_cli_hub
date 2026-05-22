from __future__ import annotations

from actuarial_cli_hub.runtimes.base import RuntimeStatus, check_command_runtime


def check_r_runtime() -> RuntimeStatus:
    return check_command_runtime("r", "Rscript", ["--version"])
