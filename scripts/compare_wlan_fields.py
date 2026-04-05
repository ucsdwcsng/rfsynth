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

from rfsynth.native.atomic.wlan_nonht80211g import (
    _build_data_field,
    _build_l_ltf,
    _build_l_sig,
    _build_l_stf,
    _resolve_mcs,
    _resolve_psdu_bits,
)
from rfsynth.native.atomic_compare import compare_iq, load_single_signal, mt19937, write_compare_plots
from rfsynth.native.plotting import read_cf32


MATLAB = Path("/Applications/MATLAB_R2025b.app/bin/matlab")
MATLAB_EXAMPLES = REPO_ROOT / "matlab" / "examples"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--out", default="/tmp/rfsynth_wlan_field_compare")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--matlab", default=str(MATLAB))
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    scene, signal_spec = load_single_signal(config_path)
    if signal_spec.type_name != "WlanNonHT80211g":
        raise ValueError("compare_wlan_fields.py requires a single WlanNonHT80211g signal config")

    run_matlab_export(config_path, out_root, Path(args.matlab))

    rng = mt19937(args.seed)
    mcs = _resolve_mcs(signal_spec.args)
    psdu_bits, scrambler_initialization = _resolve_psdu_bits(signal_spec.args, rng)
    length_bytes = psdu_bits.size // 8

    py_fields = {
        "lstf": _build_l_stf().astype("complex64"),
        "lltf": _build_l_ltf().astype("complex64"),
        "lsig": _build_l_sig(length_bytes, mcs).astype("complex64"),
        "nonht_data": _build_data_field(psdu_bits, scrambler_initialization, mcs).astype("complex64"),
    }

    summary: dict[str, object] = {
        "config": str(config_path),
        "seed": args.seed,
        "mcs": int(mcs),
        "scrambler_initialization": int(scrambler_initialization),
        "psdu_length_bytes": int(length_bytes),
        "fields": {},
    }
    for field_name, py_samples in py_fields.items():
        matlab_path = out_root / f"{field_name}.32cf"
        ml_samples = read_cf32(matlab_path)
        metrics = compare_iq(py_samples, ml_samples, drop_first_samples=0, xcorr_window_samples=min(len(py_samples), len(ml_samples)))
        plot_paths = write_compare_plots(
            py_samples,
            ml_samples,
            out_root / field_name,
            sample_rate_hz=20e6,
            title=f"WLAN {field_name}",
            drop_first_samples=0,
            xcorr_window_samples=min(len(py_samples), len(ml_samples)),
        )
        summary["fields"][field_name] = {
            "python_samples": len(py_samples),
            "matlab_samples": len(ml_samples),
            "metrics": metrics,
            "plots": plot_paths,
        }

    summary_path = out_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


def run_matlab_export(config_path: Path, out_root: Path, matlab: Path) -> None:
    expr = (
        f"addpath('{MATLAB_EXAMPLES}'); "
        f"export_wlan_field_artifacts('{config_path}', '{out_root}');"
    )
    proc = subprocess.run([str(matlab), "-batch", expr], check=False, env=dict(os.environ))
    expected = [
        out_root / "lstf.32cf",
        out_root / "lltf.32cf",
        out_root / "lsig.32cf",
        out_root / "nonht_data.32cf",
    ]
    if proc.returncode != 0 and not all(path.exists() for path in expected):
        raise RuntimeError(f"MATLAB WLAN field export failed for {config_path}")


if __name__ == "__main__":
    raise SystemExit(main())
