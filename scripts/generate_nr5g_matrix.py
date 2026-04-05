#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "configs" / "matrices" / "nr5g_matrix.json"


def config_name(prefix: str, num_subframes: int, modulation: str) -> str:
    return f"{prefix}_{num_subframes}sf_{modulation.lower()}.json"


def expand_matrix(spec: dict) -> dict:
    defaults = dict(spec.get("defaults", {}))
    profiles = list(spec["profiles"])
    num_subframes = [int(value) for value in spec["axes"]["numSubframes"]]

    configs: list[dict] = []
    for profile in profiles:
        for nsf in num_subframes:
            cfg_name = config_name(str(profile["configPrefix"]), nsf, str(profile["modulation"]))
            configs.append(
                {
                    "config_name": cfg_name,
                    "output_base": f"atomic_{cfg_name.removesuffix('.json')}",
                    "profile_slug": str(profile["profileSlug"]),
                    "numSubframes": nsf,
                }
            )

    return {
        "name": spec.get("name", "nr5g_matrix"),
        "defaults": defaults,
        "profiles": profiles,
        "configs": configs,
    }


def config_payload(config_entry: dict, expanded: dict) -> dict:
    defaults = expanded["defaults"]
    profiles = {profile["profileSlug"]: profile for profile in expanded["profiles"]}
    profile = profiles[config_entry["profile_slug"]]
    signal_args = {
        "trafficType": defaults["trafficType"],
        "centerFreq_Hz": float(profile["centerFreq_Hz"]),
        "txPower_db": float(defaults["txPower_db"]),
        "gridSize": int(profile["gridSize"]),
        "subCarrierSpacing_kHz": float(defaults["subCarrierSpacing_kHz"]),
        "numSubframes": int(config_entry["numSubframes"]),
        "cyclicPrefix": str(defaults["cyclicPrefix"]),
        "modulation": str(profile["modulation"]),
        "bandwidth_Hz": float(profile["bandwidth_Hz"]),
        "transmissionRate_Hz": float(defaults["transmissionRate_Hz"]),
    }
    if str(profile["waveformProfile"]) != "control":
        signal_args["waveformProfile"] = str(profile["waveformProfile"])

    return {
        "generationParameters": {
            "flagOutputIqSamples": True,
            "tot_time": float(defaults["tot_time"]),
            "outputFolder": "/tmp",
            "outputBase": config_entry["output_base"],
        },
        "rxConfig": {
            "name": "rx1",
            "rxSampleRate_Hz": float(defaults["rxSampleRate_Hz"]),
            "centerFreq_Hz": float(profile["centerFreq_Hz"]),
            "location": [0, 0, 0],
        },
        "sources": [
            {
                "name": "Source1",
                "origin": "nr5g_matrix",
                "location": [0, 0, 0],
                "channelModel": "IDENTITY",
                "freqOffset_Hz": 0,
                "iqImbalance": [0, 0],
                "dcOffset": [0, 0],
                "signals": [
                    {
                        "type": "nr5g",
                        "args": signal_args,
                    }
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--out", default="/tmp/rfsynth_nr5g_matrix")
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Directory for generated configs. Defaults to <out>/configs.",
    )
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    expanded = expand_matrix(spec)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    config_dir = Path(args.config_dir) if args.config_dir else out_dir / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": expanded["name"],
        "profiles": expanded["profiles"],
        "configs": expanded["configs"],
    }
    manifest_path = out_dir / "nr5g_profiles_expanded.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    for config_entry in expanded["configs"]:
        payload = config_payload(config_entry, expanded)
        (config_dir / config_entry["config_name"]).write_text(json.dumps(payload, indent=2) + "\n")

    summary = {
        "matrix_spec": str(Path(args.spec).resolve()),
        "out_dir": str(out_dir.resolve()),
        "profile_count": len(expanded["profiles"]),
        "config_count": len(expanded["configs"]),
        "manifest_path": str(manifest_path.resolve()),
        "config_dir": str(config_dir.resolve()),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
