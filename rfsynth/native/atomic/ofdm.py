from __future__ import annotations

from rfsynth.native.atomic.common import ofdm_burst
from rfsynth.native.core import Scene, Signal


class OfdmSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return ofdm_burst(self.args, rng)
