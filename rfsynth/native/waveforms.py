from __future__ import annotations

from rfsynth.native.atomic import REGISTRY
from rfsynth.native.atomic.common import qam_constellation, rrc_taps
from rfsynth.native.core import GeneratedBurst, Scene, Signal, resample_if_needed


def generate_burst(signal_spec: Signal, scene: Scene, rng) -> GeneratedBurst:
    return signal_spec.generate_transmission(scene, rng)


def compute_transmission_windows(signal_spec: Signal, scene: Scene, duration_s_override: float | None = None):
    return signal_spec.compute_transmission_windows(scene, duration_s_override=duration_s_override)


def instance_name(signal_spec: Signal) -> str:
    return signal_spec.instance_name


__all__ = [
    "GeneratedBurst",
    "REGISTRY",
    "compute_transmission_windows",
    "generate_burst",
    "instance_name",
    "qam_constellation",
    "resample_if_needed",
    "rrc_taps",
]
