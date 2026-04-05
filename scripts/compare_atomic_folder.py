#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compare_python_to_matlab import DEFAULT_MATLAB, run_matlab
from rfsynth import render_synthetic, verify_artifacts
from rfsynth.native.atomic_compare import compare_iq, write_compare_plots
from rfsynth.native.plotting import read_cf32


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_dir",
        nargs="?",
        default="/Users/dineshb/repos/signal-processing/rfsynth/configs/synthetic_atomic",
    )
    parser.add_argument("--python-out", default="/tmp/rfsynth_python_atomic_folder")
    parser.add_argument("--matlab-out", default="/tmp/rfsynth_matlab_atomic_folder")
    parser.add_argument("--report-out", default="/tmp/rfsynth_atomic_folder_compare")
    parser.add_argument("--matlab", default=str(DEFAULT_MATLAB))
    parser.add_argument("--use-existing-matlab", action="store_true")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    config_dir = Path(args.config_dir).resolve()
    report_dir = Path(args.report_out).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for config in sorted(config_dir.glob("*.json")):
        stem = config.stem
        python_dir = Path(args.python_out).resolve() / stem
        matlab_dir = Path(args.matlab_out).resolve() / stem
        case_dir = report_dir / stem
        case_dir.mkdir(parents=True, exist_ok=True)

        try:
            python_bundle = render_synthetic(config, out_dir=python_dir, seed=args.seed)
            if args.use_existing_matlab:
                output_base = output_base_for_config(config)
                matlab_base = matlab_dir / output_base
            else:
                matlab_base = run_matlab(config, Path(args.matlab), matlab_dir, seed=args.seed)

            python_iq = read_cf32(python_bundle.iq_path)
            matlab_iq = read_cf32(Path(f"{matlab_base}.32cf"))
            metrics = compare_iq(python_iq, matlab_iq)
            plots = write_compare_plots(
                python_iq,
                matlab_iq,
                case_dir / stem,
                sample_rate_hz=python_bundle.scene.rx.sample_rate_hz,
                title=f"{stem} Python vs MATLAB",
            )

            python_verify = verify_artifacts(python_bundle)
            matlab_verify = verify_artifacts(matlab_base)
            case_summary = {
                "config": str(config),
                "seed": args.seed,
                "status": "ok",
                "python_base": str(python_bundle.base_path),
                "matlab_base": str(matlab_base),
                "metrics": metrics,
                "plots": plots,
                "python_verify": python_verify,
                "matlab_verify": matlab_verify,
            }
        except Exception as exc:
            case_summary = {
                "config": str(config),
                "seed": args.seed,
                "status": "error",
                "error": str(exc),
            }
        (case_dir / "compare.json").write_text(json.dumps(case_summary, indent=2) + "\n")
        summary.append(case_summary)

    aggregate = {
        "config_dir": str(config_dir),
        "seed": args.seed,
        "case_count": len(summary),
        "success_count": sum(1 for item in summary if item["status"] == "ok"),
        "error_count": sum(1 for item in summary if item["status"] == "error"),
        "exact_match_count": sum(1 for item in summary if item.get("metrics", {}).get("exact_match")),
        "allclose_count": sum(1 for item in summary if item.get("metrics", {}).get("allclose_atol_1e-6")),
        "cases": summary,
    }
    summary_path = report_dir / "summary.json"
    summary_path.write_text(json.dumps(aggregate, indent=2) + "\n")
    print(json.dumps({"summary": str(summary_path), "case_count": len(summary)}, indent=2))
    return 0


def output_base_for_config(config: Path) -> str:
    cfg = json.loads(config.read_text())
    generation = cfg.get("generationParameters", {})
    output = cfg.get("output", {})
    return generation.get("outputBase", output.get("outputBase", config.stem))


if __name__ == "__main__":
    raise SystemExit(main())
