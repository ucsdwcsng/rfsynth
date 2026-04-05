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

from compare_atomic_iq import MATLAB, MATLAB_EXAMPLES, build_compare_config
from rfsynth.native.atomic_compare import (
    compare_iq,
    generate_python_atomic_burst,
    generate_test_vector,
    load_single_signal,
    write_cf32,
    write_compare_plots,
)
from rfsynth.native.plotting import read_cf32


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config_dir", nargs="?", default="/tmp/rfsynth_lte_dl_fdd_matrix/configs")
    parser.add_argument("--out", default="/tmp/rfsynth_lte_dl_fdd_matrix_raw_compare")
    parser.add_argument("--matlab-out", default=None)
    parser.add_argument("--matlab", default=str(MATLAB))
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--use-existing-matlab", action="store_true")
    args = parser.parse_args()

    config_dir = Path(args.config_dir).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    matlab_out_dir = Path(args.matlab_out).resolve() if args.matlab_out else out_dir / "matlab_batch"
    compare_config_dir = out_dir / "compare_configs"
    compare_config_dir.mkdir(parents=True, exist_ok=True)

    compare_cfg_map: dict[str, Path] = {}
    for config_path in sorted(config_dir.glob("*.json")):
        case_dir = out_dir / config_path.stem
        case_dir.mkdir(parents=True, exist_ok=True)
        vector_path = generate_test_vector(config_path, case_dir / f"{config_path.stem}_test_vector.json", seed=args.seed)
        compare_cfg = build_compare_config(config_path, case_dir, vector_path, args.seed)
        named_compare_cfg = compare_config_dir / config_path.name
        named_compare_cfg.write_text(compare_cfg.read_text())
        compare_cfg_map[config_path.name] = named_compare_cfg

    if not args.use_existing_matlab:
        run_matlab_folder(compare_config_dir, matlab_out_dir, Path(args.matlab), args.seed)

    cases: list[dict] = []
    for config_path in sorted(config_dir.glob("*.json")):
        case_dir = out_dir / config_path.stem
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            _, signal_spec = load_single_signal(config_path)
            compare_cfg = compare_cfg_map[config_path.name]
            vector_path = case_dir / f"{config_path.stem}_test_vector.json"
            python_burst = generate_python_atomic_burst(compare_cfg, seed=args.seed)
            python_path = write_cf32(case_dir / f"{config_path.stem}_python.32cf", python_burst.samples)
            matlab_path = matlab_output_for_config(config_path, matlab_out_dir)
            python_iq = read_cf32(python_path)
            matlab_iq = read_cf32(matlab_path)
            metrics = compare_iq(python_iq, matlab_iq)
            plots = write_compare_plots(
                python_iq,
                matlab_iq,
                case_dir / config_path.stem,
                sample_rate_hz=python_burst.sample_rate_hz,
                title=f"{config_path.stem} raw Python vs MATLAB",
            )
            case = {
                "config": str(config_path),
                "signal_type": signal_spec.type_name,
                "seed": args.seed,
                "status": "ok",
                "compare_config": str(compare_cfg),
                "test_vector_path": None if vector_path is None else str(vector_path),
                "python_iq_path": str(python_path),
                "matlab_iq_path": str(matlab_path),
                "metrics": metrics,
                "plots": plots,
            }
        except Exception as exc:
            case = {
                "config": str(config_path),
                "seed": args.seed,
                "status": "error",
                "error": str(exc),
            }
        (case_dir / "compare.json").write_text(json.dumps(case, indent=2) + "\n")
        cases.append(case)

    success_cases = [case for case in cases if case["status"] == "ok"]
    summary = {
        "config_dir": str(config_dir),
        "seed": args.seed,
        "case_count": len(cases),
        "success_count": len(success_cases),
        "error_count": sum(1 for case in cases if case["status"] == "error"),
        "exact_match_count": sum(1 for case in success_cases if case["metrics"]["exact_match"]),
        "allclose_count": sum(1 for case in success_cases if case["metrics"]["allclose_atol_1e-6"]),
        "min_cross_correlation_peak_magnitude": None
        if not success_cases
        else min(case["metrics"]["cross_correlation_peak_magnitude"] for case in success_cases),
        "max_gain_aligned_relative_rmse": None
        if not success_cases
        else max(case["metrics"]["gain_aligned_relative_rmse"] for case in success_cases),
        "cases": cases,
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"summary": str(summary_path), "case_count": len(cases)}, indent=2))
    return 0


def run_matlab_folder(config_dir: Path, matlab_out_dir: Path, matlab: Path, seed: int) -> None:
    matlab_out_dir.mkdir(parents=True, exist_ok=True)
    expr = (
        f"addpath('{MATLAB_EXAMPLES}'); "
        f"run_atomic_test_vector_folder('{config_dir}', '{matlab_out_dir}', {seed});"
    )
    proc = subprocess.run([str(matlab), "-batch", expr], check=False, env=dict(os.environ))
    summary_path = matlab_out_dir / "summary.json"
    if not summary_path.exists():
        raise RuntimeError(f"MATLAB raw batch run failed for {config_dir}")


def matlab_output_for_config(config_path: Path, matlab_out_dir: Path) -> Path:
    stem = config_path.stem
    matlab_path = matlab_out_dir / stem / f"{stem}_matlab.32cf"
    if not matlab_path.exists():
        raise FileNotFoundError(f"Expected MATLAB raw burst not found: {matlab_path}")
    return matlab_path


if __name__ == "__main__":
    raise SystemExit(main())
