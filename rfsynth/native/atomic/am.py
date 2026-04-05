from __future__ import annotations

from rfsynth.native.atomic.common import am_burst
from rfsynth.native.core import Scene, Signal


class AmSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return am_burst(self.args)
