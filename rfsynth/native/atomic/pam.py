from __future__ import annotations

from rfsynth.native.atomic.common import pam_burst
from rfsynth.native.core import Scene, Signal


class PamSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return pam_burst(self.args, rng)
