from __future__ import annotations

from rfsynth.native.atomic.common import sine_burst
from rfsynth.native.core import Scene, Signal


class SineSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return sine_burst(self.args)
