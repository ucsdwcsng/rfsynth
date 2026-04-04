#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")
DEFAULT_CONFIG_GLOBS = [
    REPO_ROOT / "configs" / "synthetic_atomic" / "*.json",
    REPO_ROOT / "configs" / "synthetic_examples" / "*.json",
]
DEFAULT_DEST = REPO_ROOT / "configs" / "test_outputs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Destination directory for exported test outputs",
    )
    args = parser.parse_args()

    dest_root = Path(args.dest)
    dest_root.mkdir(parents=True, exist_ok=True)

    exported = []
    for pattern in DEFAULT_CONFIG_GLOBS:
        for config_path in sorted(pattern.parent.glob(pattern.name)):
            exported.append(export_one(config_path, dest_root))

    manifest_path = dest_root / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump({"exports": exported}, f, indent=2)
        f.write("\n")

    print(json.dumps({"dest": str(dest_root), "count": len(exported), "manifest": str(manifest_path)}, indent=2))
    return 0


def export_one(config_path: Path, dest_root: Path) -> dict:
    with config_path.open() as f:
        cfg = json.load(f)

    generation_parameters = cfg.get("generationParameters", {})
    output_cfg = cfg.get("output", {})
    output_base = generation_parameters.get("outputBase", output_cfg.get("outputBase", config_path.stem))
    output_folder = Path(generation_parameters.get("outputFolder", output_cfg.get("outputFolder", "/tmp")))
    stem = config_path.stem
    dest_dir = dest_root / stem
    dest_dir.mkdir(parents=True, exist_ok=True)

    copy_file(config_path, dest_dir / "config.json")
    copy_file(output_folder / f"{output_base}.json", dest_dir / "metadata.json")
    copy_file(output_folder / f"{output_base}_scoring.json", dest_dir / "scoring.json")
    copy_file(output_folder / f"{output_base}_verify.json", dest_dir / "verify.json")

    image_suffixes = [
        "fullband_overlay.png",
        "fullband_occupancy.png",
        "zoom_overlay.png",
        "zoom_occupancy.png",
        "spectrogram.png",
        "occupancy.png",
        "psd.png",
        "time.png",
    ]
    for suffix in image_suffixes:
        copy_if_exists(output_folder / f"{output_base}_{suffix}", dest_dir / suffix)

    return {
        "name": stem,
        "config": str(config_path),
        "dest": str(dest_dir),
        "output_base": output_base,
    }


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing expected artifact: {src}")
    shutil.copy2(src, dst)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copy2(src, dst)


if __name__ == "__main__":
    raise SystemExit(main())
