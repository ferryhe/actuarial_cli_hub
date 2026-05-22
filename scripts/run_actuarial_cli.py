#!/usr/bin/env python3
"""Repo-local entrypoint for sibling-checkout execution.

Downstream tools may clone this repository next to other projects and execute this
script without installing the package. Keep the bootstrap tiny and explicit.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from actuarial_cli_hub.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
