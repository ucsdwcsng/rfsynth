"""Frequency-hopping atomic wrapper."""

from __future__ import annotations

from rfsynth.native.atomic.common import freq_hopping_burst
from rfsynth.native.core import Scene, Signal


class FreqHoppingSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.freq_hopping_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return freq_hopping_burst(self.args, rng)
