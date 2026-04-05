#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfsynth.native.atomic_compare import (
    compare_iq,
    generate_python_atomic_burst,
    generate_test_vector,
    load_single_signal,
    write_cf32,
)
from rfsynth.native.plotting import read_cf32


REPO_ROOT = Path(__file__).resolve().parents[1]
MATLAB = Path("/Applications/MATLAB_R2025b.app/bin/matlab")
MATLAB_EXAMPLES = REPO_ROOT / "matlab" / "examples"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--out", default="/tmp/rfsynth_atomic_compare")
    parser.add_argument("--matlab", default=str(MATLAB))
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    scene, signal_spec = load_single_signal(config_path)
    vector_path = out_root / f"{config_path.stem}_test_vector.json"
    generate_test_vector(config_path, vector_path, seed=args.seed)

    compare_cfg = build_compare_config(config_path, out_root, vector_path, args.seed)
    python_burst = generate_python_atomic_burst(compare_cfg, seed=args.seed)
    python_path = write_cf32(out_root / f"{config_path.stem}_python.32cf", python_burst.samples)
    matlab_path = run_matlab(compare_cfg, Path(args.matlab), out_root)

    result = {
        "config": str(config_path),
        "signal_type": signal_spec.type_name,
        "seed": args.seed,
        "test_vector_path": None if vector_path is None else str(vector_path),
        "python_iq_path": str(python_path),
        "matlab_iq_path": str(matlab_path),
        "iq_compare": compare_iq(read_cf32(python_path), read_cf32(matlab_path)),
    }
    print(json.dumps(result, indent=2))
    return 0


def build_compare_config(config_path: Path, out_root: Path, vector_path: Path | None, seed: int) -> Path:
    cfg = json.loads(config_path.read_text())
    if "generationParameters" not in cfg:
        cfg["generationParameters"] = {}
    cfg["generationParameters"]["seed"] = seed
    cfg["generationParameters"]["outputFolder"] = str(out_root)
    cfg["generationParameters"]["outputBase"] = f"{config_path.stem}_matlab"

    if "sources" in cfg:
        signal_args = cfg["sources"][0]["signals"][0].setdefault("args", {})
    elif "signals" in cfg:
        signal = cfg["signals"][0]
        if "args" in signal:
            signal_args = signal["args"]
        else:
            signal_args = {k: v for k, v in signal.items() if k != "type"}
            signal["args"] = signal_args
            for key in list(signal.keys()):
                if key not in {"type", "args"}:
                    del signal[key]
    else:
        raise ValueError("Atomic compare config must define sources or signals")

    if vector_path is not None:
        signal_type = None
        if "sources" in cfg:
            signal_type = cfg["sources"][0]["signals"][0]["type"]
        elif "signals" in cfg:
            signal_type = cfg["signals"][0]["type"]

        if signal_type == "LTE_DL_FDD":
            signal_args["messagePath"] = str(vector_path)
        else:
            signal_args["testVectorPath"] = str(vector_path)

    compare_cfg_path = out_root / f"{config_path.stem}_compare_config.json"
    compare_cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    return compare_cfg_path


def run_matlab(compare_cfg: Path, matlab: Path, out_root: Path) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    expr = (
        f"addpath('{MATLAB_EXAMPLES}'); "
        f"run_atomic_test_vector('{compare_cfg}');"
    )
    proc = subprocess.run([str(matlab), "-batch", expr], check=False, env=dict(os.environ))
    cfg = json.loads(compare_cfg.read_text())
    output_base = cfg.get("generationParameters", {}).get("outputBase", f"{compare_cfg.stem.replace('_compare_config', '')}_matlab")
    matlab_path = out_root / f"{output_base}.32cf"
    if proc.returncode != 0 and not matlab_path.exists():
        raise RuntimeError(f"MATLAB atomic compare run failed for {compare_cfg}")
    return matlab_path


if __name__ == "__main__":
    raise SystemExit(main())
