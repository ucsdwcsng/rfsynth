#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "configs" / "matrices" / "lte_dl_fdd_matrix.json"

LTE_PRESET_RATES = {
    6: (1.4e6, 1.92e6),
    15: (3.0e6, 3.84e6),
    25: (5.0e6, 7.68e6),
    50: (10.0e6, 15.36e6),
    75: (15.0e6, 23.04e6),
    100: (20.0e6, 30.72e6),
}


def slug_center_freq(center_freq_hz: float) -> str:
    mhz = center_freq_hz / 1e6
    if abs(mhz - round(mhz)) < 1e-9:
        return f"{int(round(mhz))}mhz"
    return f"{mhz:.3f}mhz".replace(".", "p")


def profile_slug(ndlrb: int, cp: str, tot_subframes: int, modulation: str) -> str:
    return f"lte_dl_fdd_ndlrb{ndlrb}_{cp.lower()}cp_{tot_subframes}sf_{modulation.lower()}"


def profile_id(ndlrb: int, cp: str, tot_subframes: int, modulation: str) -> str:
    return f"LTE_DL_FDD_NDLRB{ndlrb}_{cp.upper()}CP_{tot_subframes}SF_{modulation.upper()}"


def config_slug(center_freq_hz: float, ndlrb: int, cp: str, tot_subframes: int, modulation: str) -> str:
    return f"lte_dl_fdd_{slug_center_freq(center_freq_hz)}_{ndlrb}rb_{cp.lower()}cp_{tot_subframes}sf_{modulation.lower()}"


def expand_matrix(spec: dict) -> dict:
    defaults = dict(spec.get("defaults", {}))
    waveform_axes = spec["waveform_axes"]
    placement_axes = spec["placement_axes"]

    waveforms = []
    for ndlrb, cp, tot_subframes, modulation in itertools.product(
        waveform_axes["NDLRB"],
        waveform_axes["CP"],
        waveform_axes["TotSubframes"],
        waveform_axes["modulation"],
    ):
        bandwidth_hz, transmission_rate_hz = LTE_PRESET_RATES[int(ndlrb)]
        base_slug = profile_slug(int(ndlrb), str(cp), int(tot_subframes), str(modulation))
        waveforms.append(
            {
                "instance_preset": profile_id(int(ndlrb), str(cp), int(tot_subframes), str(modulation)),
                "profile_slug": base_slug,
                "template_filename": f"{base_slug}_template.json",
                "message_filename": f"{base_slug}_message.json",
                "match": {
                    "NDLRB": int(ndlrb),
                    "CP": str(cp),
                    "TotSubframes": int(tot_subframes),
                    "modulation": str(modulation),
                    "bandwidth_Hz": bandwidth_hz,
                    "transmissionRate_Hz": transmission_rate_hz,
                    "centerFreq_Hz": 763e6,
                },
            }
        )

    configs = []
    for profile, center_freq_hz in itertools.product(waveforms, placement_axes["centerFreq_Hz"]):
        center_freq_hz = float(center_freq_hz)
        match = profile["match"]
        config_name = (
            f"{config_slug(center_freq_hz, match['NDLRB'], match['CP'], match['TotSubframes'], match['modulation'])}.json"
        )
        output_base = config_name.removesuffix(".json")
        configs.append(
            {
                "config_name": config_name,
                "output_base": output_base,
                "centerFreq_Hz": center_freq_hz,
                "profile_slug": profile["profile_slug"],
                "instance_preset": profile["instance_preset"],
                "signal_args": {
                    **defaults.get("trafficType", {}),
                },
            }
        )

    return {
        "name": spec.get("name", "lte_dl_fdd_matrix"),
        "defaults": defaults,
        "profiles": waveforms,
        "configs": configs,
    }


def config_payload(config_entry: dict, expanded: dict, profile_dir: Path) -> dict:
    defaults = expanded["defaults"]
    profile_lookup = {profile["profile_slug"]: profile for profile in expanded["profiles"]}
    profile = profile_lookup[config_entry["profile_slug"]]
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
            "centerFreq_Hz": float(config_entry["centerFreq_Hz"]),
            "location": [0, 0, 0],
        },
        "sources": [
            {
                "name": "Source1",
                "origin": "lte_dl_fdd_matrix",
                "location": [0, 0, 0],
                "channelModel": "IDENTITY",
                "freqOffset_Hz": 0,
                "iqImbalance": [0, 0],
                "dcOffset": [0, 0],
                "signals": [
                    {
                        "type": "LTE_DL_FDD",
                        "args": {
                            "trafficType": defaults["trafficType"],
                            "centerFreq_Hz": float(config_entry["centerFreq_Hz"]),
                            "txPower_db": float(defaults["txPower_db"]),
                            "nPacket": int(defaults["nPacket"]),
                            "idleTime": float(defaults["idleTime"]),
                            "TotSubframes": int(profile["match"]["TotSubframes"]),
                            "messagePath": str((profile_dir / profile["message_filename"]).resolve()),
                            "NDLRB": int(profile["match"]["NDLRB"]),
                            "CP": str(profile["match"]["CP"]),
                            "modulation": str(profile["match"]["modulation"]),
                            "bandwidth_Hz": float(profile["match"]["bandwidth_Hz"]),
                            "transmissionRate_Hz": float(profile["match"]["transmissionRate_Hz"]),
                        },
                    }
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--out", default="/tmp/rfsynth_lte_dl_fdd_matrix")
    parser.add_argument(
        "--profile-dir",
        default=None,
        help="Directory where template/message JSONs will live. Defaults to <out>/profiles.",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Directory for generated public configs. Defaults to <out>/configs.",
    )
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    expanded = expand_matrix(spec)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(args.profile_dir) if args.profile_dir else out_dir / "profiles"
    config_dir = Path(args.config_dir) if args.config_dir else out_dir / "configs"
    profile_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": expanded["name"],
        "profile_dir": str(profile_dir.resolve()),
        "profiles": expanded["profiles"],
    }
    manifest_path = out_dir / "lte_dl_fdd_profiles_expanded.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    for config_entry in expanded["configs"]:
        payload = config_payload(config_entry, expanded, profile_dir)
        (config_dir / config_entry["config_name"]).write_text(json.dumps(payload, indent=2) + "\n")

    summary = {
        "matrix_spec": str(Path(args.spec).resolve()),
        "out_dir": str(out_dir.resolve()),
        "profile_count": len(expanded["profiles"]),
        "config_count": len(expanded["configs"]),
        "manifest_path": str(manifest_path.resolve()),
        "runtime_manifest_path": str(manifest_path.resolve()),
        "config_dir": str(config_dir.resolve()),
        "profile_dir": str(profile_dir.resolve()),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
