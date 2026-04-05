from __future__ import annotations

from rfsynth.native.atomic.common import ssb_burst
from rfsynth.native.core import Scene, Signal


class SsbSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return ssb_burst(self.args)
