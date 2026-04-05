from __future__ import annotations

from rfsynth.native.atomic.common import ds3_burst
from rfsynth.native.core import Scene, Signal


class Ds3Signal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return ds3_burst(self.args, rng)
