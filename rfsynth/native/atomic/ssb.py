"""SSB atomic wrapper.

Call path:
`scene.build_signal(...) -> create_signal("Ssb") -> SsbSignal.generate_transmission()`
`-> common.ssb_burst(args)`.
"""

from __future__ import annotations

from rfsynth.native.atomic.common import ssb_burst
from rfsynth.native.core import Scene, Signal


class SsbSignal(Signal):
    """Thin wrapper that dispatches to `common.ssb_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return ssb_burst(self.args)
