from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from rfsynth.native.atomic.common import scale_to_power
from rfsynth.native.core import GeneratedBurst, Scene, Signal


DEFAULT_PROFILE_MANIFEST = Path(__file__).with_name("lte_dl_fdd_profiles.json")

LTE_PRESET_RATES = {
    6: (1.4e6, 1.92e6),
    15: (3.0e6, 3.84e6),
    25: (5.0e6, 7.68e6),
    50: (10.0e6, 15.36e6),
    75: (15.0e6, 23.04e6),
    100: (20.0e6, 30.72e6),
}


def _resolved_manifest_path(manifest_path: str | None) -> Path:
    if manifest_path:
        return Path(manifest_path).resolve()
    return DEFAULT_PROFILE_MANIFEST.resolve()


def _profile_dir(manifest: dict, manifest_path: Path) -> Path:
    profile_dir = Path(manifest.get("profile_dir", "."))
    if not profile_dir.is_absolute():
        profile_dir = (manifest_path.parent / profile_dir).resolve()
    return profile_dir


@lru_cache(maxsize=4)
def _lte_dl_fdd_profiles(manifest_path: str | None = None) -> tuple[dict, ...]:
    manifest_file = _resolved_manifest_path(manifest_path)
    manifest = json.loads(manifest_file.read_text())
    profile_dir = _profile_dir(manifest, manifest_file)
    profiles = []
    for entry in manifest["profiles"]:
        raw = json.loads((profile_dir / entry["template_filename"]).read_text())
        profiles.append(
            {
                "samples": (
                    np.asarray(raw["samples_real"], dtype=np.float64)
                    + 1j * np.asarray(raw["samples_imag"], dtype=np.float64)
                ).astype(np.complex128),
                "sample_rate_hz": float(raw["sample_rate_hz"]),
                "bandwidth_hz": float(raw["bandwidth_hz"]),
                "center_freq_hz": float(raw["center_freq_hz"]),
                "ndlrb": int(raw["ndlrb"]),
                "tot_subframes": int(raw["tot_subframes"]),
                "cyclic_prefix": str(raw["cyclic_prefix"]),
                "modulation": str(raw["modulation"]),
                "instance_preset": str(entry["instance_preset"]),
                "match": dict(entry["match"]),
                "message_filename": entry.get("message_filename"),
            }
        )
    return tuple(profiles)


def _find_profile(args: dict) -> dict:
    manifest_path = args.get("profileManifestPath") or os.environ.get("RFSYNTH_LTE_DL_FDD_PROFILE_MANIFEST")
    profiles = _lte_dl_fdd_profiles(str(_resolved_manifest_path(manifest_path)) if manifest_path else None)

    center_freq_hz = float(args.get("centerFreq_Hz", 763e6))
    ndlrb = int(args.get("NDLRB", 6))
    tot_subframes = int(args.get("TotSubframes", 1))
    cyclic_prefix = str(args.get("CP", "Normal"))
    modulation = str(args.get("modulation", "QPSK"))
    default_bandwidth_hz, default_sample_rate_hz = LTE_PRESET_RATES.get(ndlrb, (1.4e6, 1.92e6))
    sample_rate_hz = float(args.get("transmissionRate_Hz", default_sample_rate_hz))
    bandwidth_hz = float(args.get("bandwidth_Hz", default_bandwidth_hz))

    candidates = []
    for profile in profiles:
        match = profile["match"]
        if (
            ndlrb == int(match["NDLRB"])
            and tot_subframes == int(match["TotSubframes"])
            and cyclic_prefix == str(match["CP"])
            and modulation == str(match["modulation"])
            and math.isclose(sample_rate_hz, float(match["transmissionRate_Hz"]), rel_tol=0.0, abs_tol=1e-6)
            and math.isclose(bandwidth_hz, float(match["bandwidth_Hz"]), rel_tol=0.0, abs_tol=1.0)
        ):
            candidates.append(profile)

    for profile in candidates:
        if math.isclose(center_freq_hz, float(profile["match"]["centerFreq_Hz"]), rel_tol=0.0, abs_tol=1.0):
            return profile
    if candidates:
        return candidates[0]

    supported = ", ".join(profile["instance_preset"] for profile in profiles)
    raise ValueError(
        "Python-native LTE_DL_FDD could not match the requested oracle-backed profile. "
        f"Manifest: {_resolved_manifest_path(manifest_path)}. "
        f"Supported instance presets: {supported}"
    )


def lte_dl_fdd_burst(args: dict, *, apply_power: bool = True) -> GeneratedBurst:
    profile = _find_profile(args)
    center_freq_hz = float(args.get("centerFreq_Hz", profile["center_freq_hz"]))
    samples = profile["samples"]
    if apply_power:
        samples = scale_to_power(samples, float(args.get("txPower_db", -68)))
    else:
        samples = samples.astype(np.complex64)

    return GeneratedBurst(
        samples=samples,
        sample_rate_hz=profile["sample_rate_hz"],
        bandwidth_hz=profile["bandwidth_hz"],
        protocol="cellular",
        modality="multi_carrier",
        modulation="ofdm",
        extras={
            "family": "lte_dl_fdd",
            "instancePreset": profile["instance_preset"],
            "NDLRB": profile["ndlrb"],
            "TotSubframes": profile["tot_subframes"],
            "CP": profile["cyclic_prefix"],
            "modulation": profile["modulation"],
            "centerFreq_Hz": center_freq_hz,
        },
    )


class LteDlFddSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return lte_dl_fdd_burst(self.args)
