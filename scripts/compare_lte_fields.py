#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compare_atomic_iq import MATLAB, MATLAB_EXAMPLES, build_compare_config
from rfsynth.native.atomic.lte_dl_fdd import _lte_direct_active_grid, _lte_direct_channel_grids, _lte_message_bits
from rfsynth.native.atomic_compare import compare_iq, generate_test_vector, load_single_signal, mt19937, write_compare_plots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--out", default="/tmp/rfsynth_lte_field_compare")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--matlab", default=str(MATLAB))
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    scene, signal_spec = load_single_signal(config_path)
    if signal_spec.type_name != "LTE_DL_FDD":
        raise ValueError("compare_lte_fields.py requires a single LTE_DL_FDD signal config")

    vector_path = generate_test_vector(config_path, out_root / f"{config_path.stem}_test_vector.json", seed=args.seed)
    compare_cfg = build_compare_config(config_path, out_root, vector_path, args.seed)
    run_matlab_export(compare_cfg, out_root, Path(args.matlab))

    scene_cmp, signal_cmp = load_single_signal(compare_cfg)
    bits = _lte_message_bits(signal_cmp.args, mt19937(args.seed))
    py_channels = {
        name: grid.astype(np.complex64)
        for name, grid in _lte_direct_channel_grids(signal_cmp.args, bits).items()
    }
    py_grid = _lte_direct_active_grid(signal_cmp.args, bits).astype(np.complex64)

    matlab_payload = json.loads((out_root / "lte_grid.json").read_text())
    ml_grid = (
        np.asarray(matlab_payload["grid_real"], dtype=np.float32)
        + 1j * np.asarray(matlab_payload["grid_imag"], dtype=np.float32)
    ).astype(np.complex64)

    py_flat = py_grid.reshape(-1, order="F")
    ml_flat = ml_grid.reshape(-1, order="F")
    metrics = compare_iq(py_flat, ml_flat, drop_first_samples=0, xcorr_window_samples=min(py_flat.size, ml_flat.size))
    plots = write_compare_plots(
        py_flat,
        ml_flat,
        out_root / "lte_grid",
        sample_rate_hz=1.0,
        title=f"LTE grid {config_path.stem}",
        drop_first_samples=0,
        xcorr_window_samples=min(py_flat.size, ml_flat.size),
    )

    channel_metrics: dict[str, dict[str, object]] = {}
    if "channels" in matlab_payload:
        matlab_channels = matlab_payload["channels"]
        for channel_name, py_channel in py_channels.items():
            if channel_name == "control":
                ml_control = sum(
                    _load_channel_grid(matlab_channels[name])
                    for name in ("pcfich", "phich", "pdcch")
                    if name in matlab_channels
                )
                ml_channel = ml_control.astype(np.complex64)
            elif channel_name in matlab_channels:
                ml_channel = _load_channel_grid(matlab_channels[channel_name])
            else:
                continue
            py_flat_channel = py_channel.reshape(-1, order="F")
            ml_flat_channel = ml_channel.reshape(-1, order="F")
            channel_metrics[channel_name] = compare_iq(
                py_flat_channel,
                ml_flat_channel,
                drop_first_samples=0,
                xcorr_window_samples=min(py_flat_channel.size, ml_flat_channel.size),
            )

    summary = {
        "config": str(config_path),
        "compare_config": str(compare_cfg),
        "seed": args.seed,
        "python_grid_shape": list(py_grid.shape),
        "matlab_grid_shape": list(ml_grid.shape),
        "metrics": metrics,
        "channel_metrics": channel_metrics,
        "plots": plots,
    }
    summary_path = out_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


def run_matlab_export(compare_cfg: Path, out_root: Path, matlab: Path) -> None:
    expr = (
        f"addpath('{MATLAB_EXAMPLES}'); "
        f"export_lte_field_artifacts('{compare_cfg}', '{out_root}');"
    )
    cmd = f"{shlex.quote(str(matlab))} -batch {shlex.quote(expr)}"
    proc = subprocess.run(["/bin/zsh", "-lc", cmd], check=False, env=dict(os.environ))
    if proc.returncode != 0 and not (out_root / "lte_grid.json").exists():
        raise RuntimeError(f"MATLAB LTE field export failed for {compare_cfg}")


def _load_channel_grid(payload: dict[str, object]) -> np.ndarray:
    return (
        np.asarray(payload["real"], dtype=np.float32)
        + 1j * np.asarray(payload["imag"], dtype=np.float32)
    ).astype(np.complex64)


if __name__ == "__main__":
    raise SystemExit(main())
