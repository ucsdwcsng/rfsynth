from __future__ import annotations

import argparse
import json
from pathlib import Path

from rfsynth import compile_replay, load_scene, plot_artifacts, render_synthetic, run_replay, verify_artifacts
from rfsynth.native.scene import validate_scene


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rfsynth")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("scene")

    gen = sub.add_parser("generate")
    gen.add_argument("scene")
    gen.add_argument("--out", default=None)
    gen.add_argument("--seed", type=int, default=1234)

    plot = sub.add_parser("plot")
    plot.add_argument("base")

    verify = sub.add_parser("verify")
    verify.add_argument("base")

    replay = sub.add_parser("replay")
    replay_sub = replay.add_subparsers(dest="replay_cmd", required=True)
    sim = replay_sub.add_parser("simulate")
    sim.add_argument("target")
    sim.add_argument("--out", default=None)
    usrp = replay_sub.add_parser("usrp")
    usrp.add_argument("target")
    usrp.add_argument("--radio-config", required=True)
    usrp.add_argument("--out", default=None)

    args = parser.parse_args(argv)

    if args.command == "check":
        scene = load_scene(args.scene)
        result = validate_scene(scene)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1

    if args.command == "generate":
        bundle = render_synthetic(args.scene, out_dir=args.out, seed=args.seed)
        print(
            json.dumps(
                {
                    "base": str(bundle.base_path),
                    "iq_path": str(bundle.iq_path),
                    "metadata_path": str(bundle.metadata_path),
                    "scoring_path": str(bundle.scoring_path),
                    "signal_count": len(bundle.signals),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "plot":
        plots = plot_artifacts(Path(args.base))
        print(json.dumps({"base": str(plots.base_path), "paths": {k: str(v) for k, v in plots.paths.items()}}, indent=2))
        return 0

    if args.command == "verify":
        report = verify_artifacts(Path(args.base))
        print(json.dumps(report, indent=2))
        return 0 if report["verdict"] != "Visual fail" else 1

    if args.command == "replay" and args.replay_cmd == "simulate":
        plan = compile_replay(Path(args.target))
        report = run_replay(plan, backend="sim", out_dir=args.out)
        print(json.dumps({"backend": report.backend, "event_count": report.event_count, "output_path": str(report.output_path)}, indent=2))
        return 0

    if args.command == "replay" and args.replay_cmd == "usrp":
        plan = compile_replay(Path(args.target))
        report = run_replay(plan, backend="uhd", radio_config=args.radio_config, out_dir=args.out)
        print(json.dumps({"backend": report.backend, "event_count": report.event_count, "output_path": str(report.output_path)}, indent=2))
        return 0

    raise AssertionError("Unhandled command")
