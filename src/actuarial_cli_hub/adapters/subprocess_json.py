from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any, BinaryIO, Sequence


def run_json_command(
    argv: Sequence[str],
    *,
    input_path: Path | None = None,
    timeout: float = 300,
    max_output_bytes: int = 1_048_576,
) -> dict[str, Any]:
    if not argv:
        raise ValueError("argv must not be empty")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_output_bytes < 1024:
        raise ValueError("max_output_bytes must be at least 1024")

    result = _run_bounded(argv, input_path=input_path, timeout=timeout, max_output_bytes=max_output_bytes)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"subprocess exited {result.returncode}: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"subprocess did not emit valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("subprocess JSON output must be an object")
    return payload


class _CompletedJsonProcess:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run_bounded(
    argv: Sequence[str],
    *,
    input_path: Path | None,
    timeout: float,
    max_output_bytes: int,
) -> _CompletedJsonProcess:
    stdin_file: BinaryIO | None = None
    if input_path is not None:
        stdin_file = input_path.open("rb")

    try:
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen(
                list(argv),
                stdin=stdin_file if stdin_file is not None else subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
            )
            try:
                returncode = _wait_bounded(
                    process,
                    stdout_file=stdout_file,
                    stderr_file=stderr_file,
                    timeout=timeout,
                    max_output_bytes=max_output_bytes,
                )
            except Exception:
                process.kill()
                process.wait()
                raise

            stdout = _read_limited(stdout_file, max_output_bytes).decode("utf-8", errors="replace")
            stderr = _read_limited(stderr_file, max_output_bytes).decode("utf-8", errors="replace")
            return _CompletedJsonProcess(returncode=returncode, stdout=stdout, stderr=stderr)
    finally:
        if stdin_file is not None:
            stdin_file.close()


def _wait_bounded(
    process: subprocess.Popen[bytes],
    *,
    stdout_file: BinaryIO,
    stderr_file: BinaryIO,
    timeout: float,
    max_output_bytes: int,
) -> int:
    deadline = time.monotonic() + timeout
    while True:
        returncode = process.poll()
        if returncode is not None:
            _raise_if_too_large(stdout_file, stderr_file, max_output_bytes)
            return returncode
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, timeout)
        _raise_if_too_large(stdout_file, stderr_file, max_output_bytes)
        time.sleep(0.05)


def _raise_if_too_large(stdout_file: BinaryIO, stderr_file: BinaryIO, max_output_bytes: int) -> None:
    if _file_size(stdout_file) > max_output_bytes or _file_size(stderr_file) > max_output_bytes:
        raise RuntimeError("subprocess output exceeded max_output_bytes")


def _file_size(file_obj: BinaryIO) -> int:
    return os.fstat(file_obj.fileno()).st_size


def _read_limited(file_obj: BinaryIO, max_output_bytes: int) -> bytes:
    file_obj.seek(0)
    data = file_obj.read(max_output_bytes + 1)
    if len(data) > max_output_bytes:
        raise RuntimeError("subprocess output exceeded max_output_bytes")
    return data
