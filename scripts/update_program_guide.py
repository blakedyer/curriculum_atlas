#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    run([sys.executable, "scripts/sync_uvic_catalog.py"])
    run([sys.executable, "scripts/sync_uvic_computing_catalog.py"])
    run([sys.executable, "scripts/build_static_site.py"])


if __name__ == "__main__":
    main()
