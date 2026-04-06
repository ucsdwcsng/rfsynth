"""Thin entrypoint for the Python-native renderer.

`render_synthetic(...)` exists so the CLI, tests, and library callers all go
through the same `Scene -> VirtualSignalEngine.render()` path.
"""

from __future__ import annotations

from pathlib import Path

from rfsynth.native.core import Scene, VirtualSignalEngine
from rfsynth.native.models import ArtifactBundle
from rfsynth.native.scene import load_scene


def render_synthetic(scene: Scene | str | Path | dict, out_dir: str | Path | None = None, seed: int = 1234) -> ArtifactBundle:
    """Render a scene object or scene config into IQ plus metadata artifacts."""

    if not isinstance(scene, Scene):
        scene = load_scene(scene)
    return VirtualSignalEngine(scene).render(out_dir=out_dir, seed=seed)
