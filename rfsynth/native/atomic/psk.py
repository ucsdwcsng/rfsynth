from __future__ import annotations

from rfsynth.native.atomic.common import psk_burst
from rfsynth.native.core import Scene, Signal


class PskSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return psk_burst(self.args, rng)
