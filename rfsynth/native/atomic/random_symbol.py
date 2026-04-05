from __future__ import annotations

from rfsynth.native.atomic.common import random_symbol_burst
from rfsynth.native.core import Scene, Signal


class RandomSymbolSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return random_symbol_burst(self.args, rng)
