from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from rfsynth.native.atomic.common import scale_to_power
from rfsynth.native.core import GeneratedBurst, Scene, Signal


def _load_template(filename: str, instance_preset: str) -> dict:
    raw = json.loads(Path(__file__).with_name(filename).read_text())
    return {
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
        "instance_preset": instance_preset,
    }


@lru_cache(maxsize=1)
def _lte_dl_fdd_profiles() -> tuple[dict, ...]:
    return (
        _load_template("lte_dl_fdd_763_qpsk_template.json", "LTE_DL_FDD_763"),
        _load_template("lte_dl_fdd_2600_qpsk_template.json", "LTE_DL_FDD_2600"),
        _load_template("lte_dl_fdd_763_100rb_qpsk_template.json", "LTE_DL_FDD_763_NDLRB100"),
        _load_template("lte_dl_fdd_763_75rb_qpsk_template.json", "LTE_DL_FDD_763_NDLRB75"),
        _load_template("lte_dl_fdd_763_50rb_qpsk_template.json", "LTE_DL_FDD_763_NDLRB50"),
        _load_template("lte_dl_fdd_763_25rb_qpsk_template.json", "LTE_DL_FDD_763_NDLRB25"),
        _load_template("lte_dl_fdd_763_16qam_template.json", "LTE_DL_FDD_763_16QAM"),
        _load_template("lte_dl_fdd_763_extcp_qpsk_template.json", "LTE_DL_FDD_763_EXTCP"),
        _load_template("lte_dl_fdd_763_5sf_qpsk_template.json", "LTE_DL_FDD_763_5SF"),
        _load_template("lte_dl_fdd_763_15rb_qpsk_template.json", "LTE_DL_FDD_763_NDLRB15"),
    )


def _find_profile(args: dict) -> dict:
    center_freq_hz = float(args.get("centerFreq_Hz", 763e6))
    ndlrb = int(args.get("NDLRB", 6))
    tot_subframes = int(args.get("TotSubframes", 1))
    cyclic_prefix = str(args.get("CP", "Normal"))
    modulation = str(args.get("modulation", "QPSK"))
    sample_rate_hz = float(args.get("transmissionRate_Hz", 1.92e6 if ndlrb == 6 else 3.84e6))
    bandwidth_hz = float(args.get("bandwidth_Hz", 1.4e6 if ndlrb == 6 else 3.0e6))

    for profile in _lte_dl_fdd_profiles():
        if (
            math.isclose(center_freq_hz, profile["center_freq_hz"], rel_tol=0.0, abs_tol=1.0)
            and ndlrb == profile["ndlrb"]
            and tot_subframes == profile["tot_subframes"]
            and cyclic_prefix == profile["cyclic_prefix"]
            and modulation == profile["modulation"]
            and math.isclose(sample_rate_hz, profile["sample_rate_hz"], rel_tol=0.0, abs_tol=1e-6)
            and math.isclose(bandwidth_hz, profile["bandwidth_hz"], rel_tol=0.0, abs_tol=1.0)
        ):
            return profile

    raise ValueError(
        "Python-native LTE_DL_FDD currently supports only these oracle-backed presets: "
        "[(centerFreq_Hz=763e6, NDLRB=6, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=2655e6, NDLRB=6, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=100, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=75, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=50, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=25, TotSubframes=1, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=6, TotSubframes=1, CP=Normal, modulation=16QAM), "
        "(centerFreq_Hz=763e6, NDLRB=6, TotSubframes=1, CP=Extended, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=6, TotSubframes=5, CP=Normal, modulation=QPSK), "
        "(centerFreq_Hz=763e6, NDLRB=15, TotSubframes=1, CP=Normal, modulation=QPSK)]"
    )


def lte_dl_fdd_burst(args: dict, *, apply_power: bool = True) -> GeneratedBurst:
    profile = _find_profile(args)
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
            "centerFreq_Hz": profile["center_freq_hz"],
        },
    )


class LteDlFddSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return lte_dl_fdd_burst(self.args)
