"""QAM atomic wrapper."""

from __future__ import annotations

from rfsynth.native.atomic.common import qam_burst
from rfsynth.native.core import Scene, Signal


class QamSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.qam_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return qam_burst(self.args, rng)
