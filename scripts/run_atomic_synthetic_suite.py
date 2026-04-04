#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")
MATLAB_RUNNER_DIR = REPO_ROOT / "matlab" / "examples"
PLOTTER = REPO_ROOT / "scripts" / "plot_and_verify_synthetic.py"
DEFAULT_MATLAB = Path("/Applications/MATLAB_R2025b.app/bin/matlab")
DEFAULT_PYTHON = Path("/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        default=str(REPO_ROOT / "configs" / "synthetic_atomic"),
        help="Directory holding atomic synthetic JSON configs",
    )
    parser.add_argument(
        "--matlab",
        default=str(DEFAULT_MATLAB),
        help="Path to MATLAB executable",
    )
    parser.add_argument(
        "--python",
        default=str(DEFAULT_PYTHON),
        help="Python interpreter with numpy and matplotlib installed",
    )
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    matlab = Path(args.matlab)
    python = Path(args.python)
    configs = sorted(config_dir.glob("*.json"))
    if not configs:
        raise SystemExit(f"No configs found in {config_dir}")

    results = []
    for config in configs:
        print(f"[suite] generating {config.name}")
        batch_expr = (
            f"addpath('{MATLAB_RUNNER_DIR}'); "
            f"run_synthetic_json('{config}');"
        )
        subprocess.run([str(matlab), "-batch", batch_expr], check=True)

        with config.open() as f:
            cfg = json.load(f)
        base = Path(cfg["generationParameters"]["outputFolder"]) / cfg["generationParameters"]["outputBase"]

        print(f"[suite] plotting and verifying {base}")
        env = dict(os.environ)
        env.setdefault("MPLCONFIGDIR", "/tmp/mpl-rfsynth")
        subprocess.run([str(python), str(PLOTTER), "--base", str(base)], check=True, env=env)

        verify_path = Path(f"{base}_verify.json")
        with verify_path.open() as f:
            verify = json.load(f)
        results.append(
            {
                "config": str(config),
                "base": str(base),
                "verdict": verify["verdict"],
                "signal_box_count": verify["signal_box_count"],
                "energy_box_count": verify["energy_box_count"],
            }
        )

    summary_path = Path("/tmp/rfsynth_atomic_suite_summary.json")
    with summary_path.open("w") as f:
        json.dump({"results": results}, f, indent=2)
        f.write("\n")

    print(json.dumps({"results": results, "summary_path": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
