"""FM atomic wrapper.

Call path:
`scene.build_signal(...) -> create_signal("Fm") -> FmSignal.generate_transmission()`
`-> common.fm_burst(args)`.
"""

from __future__ import annotations

from rfsynth.native.atomic.common import fm_burst
from rfsynth.native.core import Scene, Signal


class FmSignal(Signal):
    """Thin wrapper that dispatches to `common.fm_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return fm_burst(self.args)
