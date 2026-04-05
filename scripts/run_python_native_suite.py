#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfsynth import plot_artifacts, render_synthetic, verify_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_roots",
        nargs="*",
        help="Config JSON files or directories. Defaults to the public atomic and mixed-scene config directories.",
    )
    parser.add_argument(
        "--out",
        default="/tmp/rfsynth_python_native_suite",
        help="Output directory for generated Python-native artifacts",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    roots = [Path(root) for root in args.config_roots] if args.config_roots else [
        REPO_ROOT / "configs" / "synthetic_atomic",
        REPO_ROOT / "configs" / "synthetic_examples",
    ]
    configs: list[Path] = []
    for root in roots:
        if root.is_dir():
            configs.extend(sorted(root.glob("*.json")))
        elif root.suffix == ".json":
            configs.append(root)
        else:
            raise ValueError(f"Unsupported config root: {root}")

    results = []
    for config in sorted(configs):
        bundle = render_synthetic(config, out_dir=out_dir)
        plot_artifacts(bundle)
        verify = verify_artifacts(bundle)
        results.append(
            {
                "config": str(config),
                "base": str(bundle.base_path),
                "verdict": verify["verdict"],
                "signal_box_count": verify["signal_box_count"],
                "energy_box_count": verify["energy_box_count"],
            }
        )

    summary_path = out_dir / "python_native_suite_summary.json"
    summary_path.write_text(json.dumps({"results": results}, indent=2) + "\n")
    print(json.dumps({"results": results, "summary_path": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
