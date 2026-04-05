from __future__ import annotations

from rfsynth.native.atomic.common import dummy_burst
from rfsynth.native.core import Scene, Signal


class DummySignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return dummy_burst(self.args)
