"""Random-symbol atomic wrapper."""

from __future__ import annotations

from rfsynth.native.atomic.common import random_symbol_burst
from rfsynth.native.core import Scene, Signal


class RandomSymbolSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.random_symbol_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return random_symbol_burst(self.args, rng)
