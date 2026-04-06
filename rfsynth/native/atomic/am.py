"""AM atomic wrapper.

Call path:
`scene.build_signal(...) -> create_signal("Am") -> AmSignal.generate_transmission()`
`-> common.am_burst(args)`.
"""

from __future__ import annotations

from rfsynth.native.atomic.common import am_burst
from rfsynth.native.core import Scene, Signal


class AmSignal(Signal):
    """Thin wrapper that dispatches to `common.am_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return am_burst(self.args)
