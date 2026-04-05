#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfsynth.native.plotting import plot_artifacts, verify_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Artifact base path without extension, e.g. /tmp/atomic_bluetooth")
    args = parser.parse_args()

    plots = plot_artifacts(Path(args.base))
    verify = verify_artifacts(Path(args.base))
    verify["plots"] = {k: str(v) for k, v in plots.paths.items()}
    print(json.dumps(verify, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
