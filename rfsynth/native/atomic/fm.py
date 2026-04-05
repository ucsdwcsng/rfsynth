from __future__ import annotations

from rfsynth.native.atomic.common import fm_burst
from rfsynth.native.core import Scene, Signal


class FmSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return fm_burst(self.args)
