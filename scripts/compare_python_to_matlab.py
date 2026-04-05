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

from rfsynth import render_synthetic, verify_artifacts
from rfsynth.native.plotting import read_cf32


MATLAB_RUNNER_DIR = REPO_ROOT / "matlab" / "examples"
DEFAULT_MATLAB = Path("/Applications/MATLAB_R2025b.app/bin/matlab")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--python-out", default="/tmp/rfsynth_python_oracle")
    parser.add_argument("--matlab-out", default="/tmp/rfsynth_matlab_oracle")
    parser.add_argument("--matlab", default=str(DEFAULT_MATLAB))
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    config = Path(args.config).resolve()
    python_bundle = render_synthetic(config, out_dir=args.python_out, seed=args.seed)
    matlab_base = run_matlab(config, Path(args.matlab), Path(args.matlab_out), seed=args.seed)

    python_md = json.loads(python_bundle.metadata_path.read_text())
    matlab_md = json.loads(Path(f"{matlab_base}.json").read_text())
    iq_compare = compare_iq(read_cf32(python_bundle.iq_path), read_cf32(Path(f"{matlab_base}.32cf")))
    python_verify = verify_artifacts(python_bundle)
    matlab_verify = verify_artifacts(matlab_base)
    result = compare_metadata(
        python_md,
        matlab_md,
        python_bundle.scene.rx.sample_rate_hz,
        python_verify=python_verify,
        matlab_verify=matlab_verify,
    )
    result["seed"] = args.seed
    result["iq_compare"] = iq_compare
    result["python_base"] = str(python_bundle.base_path)
    result["matlab_base"] = str(matlab_base)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def run_matlab(config: Path, matlab: Path, out_dir: Path, seed: int, retries: int = 3) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with config.open() as f:
        cfg = json.load(f)
    generation = cfg.get("generationParameters", {})
    output = cfg.get("output", {})
    output_base = generation.get("outputBase", output.get("outputBase", config.stem))
    cfg.setdefault("generationParameters", {})
    cfg["generationParameters"]["seed"] = seed
    cfg["generationParameters"]["outputFolder"] = str(out_dir)
    cfg["generationParameters"]["outputBase"] = output_base
    temp_config = out_dir / f"{config.stem}_oracle_config.json"
    temp_config.write_text(json.dumps(cfg, indent=2) + "\n")
    batch_expr = f"addpath('{MATLAB_RUNNER_DIR}'); run_synthetic_json('{temp_config}');"
    base = out_dir / output_base
    required = [base.with_suffix(".32cf"), base.with_suffix(".json"), Path(f"{base}_scoring.json")]
    last_returncode: int | None = None
    for _ in range(max(1, retries)):
        proc = subprocess.run(
            [str(matlab), "-batch", batch_expr],
            check=False,
            env=dict(os.environ),
        )
        last_returncode = proc.returncode
        if all(path.exists() for path in required):
            break
    else:
        raise RuntimeError(
            "MATLAB oracle run failed without producing expected artifacts\n"
            f"returncode={last_returncode}\n"
        )
    return base


def compare_iq(python_iq: np.ndarray, matlab_iq: np.ndarray) -> dict:
    sample_count = min(len(python_iq), len(matlab_iq))
    python_iq = python_iq[:sample_count]
    matlab_iq = matlab_iq[:sample_count]
    diff = python_iq - matlab_iq

    denom = float(np.linalg.norm(matlab_iq))
    if denom == 0.0:
        denom = 1.0
    py_norm = float(np.linalg.norm(python_iq))
    ml_norm = float(np.linalg.norm(matlab_iq))
    if py_norm == 0.0 or ml_norm == 0.0:
        corr_mag = 0.0
    else:
        corr_mag = float(abs(np.vdot(python_iq, matlab_iq)) / (py_norm * ml_norm))

    gain = complex(np.vdot(python_iq, matlab_iq) / np.vdot(python_iq, python_iq)) if py_norm > 0.0 else 0.0j
    aligned = gain * python_iq
    aligned_rrmse = float(np.linalg.norm(aligned - matlab_iq) / denom)

    return {
        "sample_count_python": int(len(python_iq)),
        "sample_count_matlab": int(len(matlab_iq)),
        "sample_count_compared": int(sample_count),
        "exact_match": bool(np.array_equal(python_iq, matlab_iq)),
        "allclose_atol_1e-6": bool(np.allclose(python_iq, matlab_iq, atol=1e-6, rtol=1e-6)),
        "rmse": float(np.sqrt(np.mean(np.abs(diff) ** 2))),
        "relative_rmse": float(np.linalg.norm(diff) / denom),
        "max_abs_error": float(np.max(np.abs(diff))) if sample_count else 0.0,
        "correlation_magnitude": corr_mag,
        "best_fit_gain_real": float(np.real(gain)),
        "best_fit_gain_imag": float(np.imag(gain)),
        "gain_aligned_relative_rmse": aligned_rrmse,
    }


def compare_metadata(
    python_md: dict,
    matlab_md: dict,
    rx_rate_hz: float,
    *,
    python_verify: dict,
    matlab_verify: dict,
) -> dict:
    py_signals, py_energies = flatten_boxes(python_md)
    ml_signals, ml_energies = flatten_boxes(matlab_md)
    ok = True
    reasons = []
    py_sources = flatten_sources(python_md)
    ml_sources = flatten_sources(matlab_md)
    if len(py_sources) != len(ml_sources):
        ok = False
        reasons.append(f"source count mismatch: python={len(py_sources)} matlab={len(ml_sources)}")
    if len(py_signals) != len(ml_signals):
        ok = False
        reasons.append(f"signal count mismatch: python={len(py_signals)} matlab={len(ml_signals)}")
    if len(py_energies) != len(ml_energies):
        ok = False
        reasons.append(f"energy count mismatch: python={len(py_energies)} matlab={len(ml_energies)}")

    tol_time = 1.0 / rx_rate_hz
    tol_freq = 1.0e5
    for label, py_boxes, ml_boxes in [("signal", py_signals, ml_signals), ("energy", py_energies, ml_energies)]:
        for idx, (py_box, ml_box) in enumerate(zip(py_boxes, ml_boxes), start=1):
            for key in ("time_start", "time_stop"):
                if abs(py_box[key] - ml_box[key]) > tol_time:
                    ok = False
                    reasons.append(f"{label}[{idx}] {key} mismatch: python={py_box[key]} matlab={ml_box[key]}")
            for key in ("freq_lo", "freq_hi"):
                if abs(py_box[key] - ml_box[key]) > max(tol_freq, 0.01 * (ml_box["freq_hi"] - ml_box["freq_lo"])):
                    ok = False
                    reasons.append(f"{label}[{idx}] {key} mismatch: python={py_box[key]} matlab={ml_box[key]}")
            py_bw = py_box["freq_hi"] - py_box["freq_lo"]
            ml_bw = ml_box["freq_hi"] - ml_box["freq_lo"]
            if abs(py_bw - ml_bw) > max(tol_freq, 0.01 * ml_bw):
                ok = False
                reasons.append(f"{label}[{idx}] bandwidth mismatch: python={py_bw} matlab={ml_bw}")

    if python_verify["signal_box_count"] != matlab_verify["signal_box_count"]:
        ok = False
        reasons.append(
            f"signal box count mismatch: python={python_verify['signal_box_count']} matlab={matlab_verify['signal_box_count']}"
        )
    if python_verify["energy_box_count"] != matlab_verify["energy_box_count"]:
        ok = False
        reasons.append(
            f"energy box count mismatch: python={python_verify['energy_box_count']} matlab={matlab_verify['energy_box_count']}"
        )
    if python_verify["verdict"] != matlab_verify["verdict"]:
        ok = False
        reasons.append(
            f"visual verification mismatch: python={python_verify['verdict']} matlab={matlab_verify['verdict']}"
        )

    return {
        "ok": ok,
        "reasons": reasons,
        "python_verify": python_verify,
        "matlab_verify": matlab_verify,
    }


def flatten_boxes(metadata: dict) -> tuple[list[dict], list[dict]]:
    signals = []
    energies = []
    sources = metadata["sourceArray"] if isinstance(metadata["sourceArray"], list) else [metadata["sourceArray"]]
    for source in sources:
        signal_array = source["signalArray"] if isinstance(source["signalArray"], list) else [source["signalArray"]]
        for signal in signal_array:
            signals.append(signal["requiredMetadata"])
            transmissions = signal.get("transmissionArray", [])
            if isinstance(transmissions, dict):
                transmissions = [transmissions]
            energies.extend(transmissions)
    return signals, energies


def flatten_sources(metadata: dict) -> list[dict]:
    sources = metadata["sourceArray"]
    return sources if isinstance(sources, list) else [sources]


if __name__ == "__main__":
    raise SystemExit(main())
