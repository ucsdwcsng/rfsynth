#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfsynth.native.atomic_compare import compare_iq, write_compare_plots
from rfsynth.native.plotting import read_cf32


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("python_iq")
    parser.add_argument("matlab_iq")
    parser.add_argument("--sample-rate", type=float, required=True)
    parser.add_argument("--title", default="Atomic IQ Compare")
    parser.add_argument("--out-prefix", required=True)
    args = parser.parse_args()

    python_iq = read_cf32(Path(args.python_iq))
    matlab_iq = read_cf32(Path(args.matlab_iq))
    metrics = compare_iq(python_iq, matlab_iq)
    plots = write_compare_plots(
        python_iq,
        matlab_iq,
        args.out_prefix,
        sample_rate_hz=args.sample_rate,
        title=args.title,
    )
    print(json.dumps({"metrics": metrics, "plots": plots}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
