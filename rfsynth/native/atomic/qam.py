from __future__ import annotations

from rfsynth.native.atomic.common import qam_burst
from rfsynth.native.core import Scene, Signal


class QamSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return qam_burst(self.args, rng)
