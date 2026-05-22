from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(frozen=True)
class RuntimeStatus:
    runtime: str
    command: str
    executable: str | None
    available: bool
    version: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "command": self.command,
            "executable": self.executable,
            "available": self.available,
            "version": self.version,
            "error": self.error,
        }


def check_command_runtime(runtime: str, command: str, version_args: list[str] | None = None) -> RuntimeStatus:
    executable = shutil.which(command)
    if executable is None:
        return RuntimeStatus(
            runtime=runtime,
            command=command,
            executable=None,
            available=False,
            error=f"{command} executable not found on PATH",
        )

    version = None
    error = None
    if version_args:
        try:
            result = subprocess.run(
                [executable, *version_args],
                check=False,
                text=True,
                capture_output=True,
                timeout=10,
            )
            output = (result.stdout or result.stderr).strip()
            if result.returncode == 0 and output:
                version = output.splitlines()[0]
            elif result.returncode != 0:
                error = (result.stderr or result.stdout).strip() or f"version command exited {result.returncode}"
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)

    return RuntimeStatus(
        runtime=runtime,
        command=command,
        executable=executable,
        available=error is None,
        version=version,
        error=error,
    )
