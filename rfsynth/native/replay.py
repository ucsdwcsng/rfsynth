"""Replay planning and backend scaffolding for rendered artifacts."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rfsynth.native.core import Scene
from rfsynth.native.models import ArtifactBundle, ReplayEvent, ReplayPlan, ReplayRunReport
from rfsynth.native.plotting import resolve_bundle
from rfsynth.native.render import render_synthetic
from rfsynth.native.scene import load_scene


def compile_replay(scene_or_bundle: Scene | ArtifactBundle | str | Path | dict) -> ReplayPlan:
    """Compile a replay plan from a scene, bundle, or existing artifact base."""

    if isinstance(scene_or_bundle, ArtifactBundle):
        bundle = scene_or_bundle
    elif isinstance(scene_or_bundle, Scene):
        bundle = render_synthetic(scene_or_bundle)
    elif isinstance(scene_or_bundle, dict):
        bundle = render_synthetic(load_scene(scene_or_bundle))
    else:
        path = Path(scene_or_bundle)
        if path.suffix == ".json" and not path.name.endswith("_scoring.json") and not path.name.endswith("_verify.json"):
            bundle = render_synthetic(load_scene(path))
        else:
            bundle = resolve_bundle(path)

    metadata = bundle.metadata if bundle.metadata else json.loads(bundle.metadata_path.read_text())
    events: list[ReplayEvent] = []
    sources = metadata["sourceArray"] if isinstance(metadata["sourceArray"], list) else [metadata["sourceArray"]]
    for source in sources:
        signals = source["signalArray"] if isinstance(source["signalArray"], list) else [source["signalArray"]]
        for signal in signals:
            required = signal["requiredMetadata"]
            transmissions = signal.get("transmissionArray", [])
            if isinstance(transmissions, dict):
                transmissions = [transmissions]
            for tx in transmissions:
                events.append(
                    ReplayEvent(
                        instance_name=str(tx["instance_name"]),
                        source_name=str(source["instance_name"]),
                        signal_name=str(required["instance_name"]),
                        time_start=float(tx["time_start"]),
                        time_stop=float(tx["time_stop"]),
                        center_freq_hz=0.5 * (float(tx["freq_lo"]) + float(tx["freq_hi"])),
                        bandwidth_hz=float(tx["freq_hi"]) - float(tx["freq_lo"]),
                        freq_lo_hz=float(tx["freq_lo"]),
                        freq_hi_hz=float(tx["freq_hi"]),
                    )
                )
    return ReplayPlan(
        scene_id=bundle.base_path.name,
        sample_rate_hz=float(metadata["rxObj"]["sampleRate_Hz"]),
        center_freq_hz=float(metadata["rxObj"]["freqCenter_Hz"]),
        events=sorted(events, key=lambda e: (e.time_start, e.instance_name)),
        base_path=bundle.base_path,
    )


def run_replay(plan: ReplayPlan, backend: str = "sim", radio_config: str | Path | None = None, out_dir: str | Path | None = None) -> ReplayRunReport:
    """Execute a replay plan using the requested backend."""

    out_root = Path(out_dir) if out_dir is not None else (plan.base_path.parent if plan.base_path is not None else Path("/tmp"))
    backend_obj: ReplayBackend
    if backend == "sim":
        backend_obj = SimReplayBackend(out_root)
    elif backend == "uhd":
        backend_obj = UhdReplayBackend(out_root, radio_config=radio_config)
    else:
        raise ValueError(f"Unsupported replay backend: {backend}")
    return backend_obj.run(plan)


class ReplayBackend(ABC):
    """Abstract base class for replay backends."""

    def __init__(self, out_root: Path):
        self.out_root = out_root
        self.out_root.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def run(self, plan: ReplayPlan) -> ReplayRunReport:
        raise NotImplementedError


class SimReplayBackend(ReplayBackend):
    """Dry-run backend that serializes the replay timeline to JSON."""

    def run(self, plan: ReplayPlan) -> ReplayRunReport:
        output_path = self.out_root / f"{plan.scene_id}_sim_replay.json"
        timeline = [
            {
                "instance_name": event.instance_name,
                "signal_name": event.signal_name,
                "source_name": event.source_name,
                "time_start": event.time_start,
                "time_stop": event.time_stop,
                "center_freq_hz": event.center_freq_hz,
                "bandwidth_hz": event.bandwidth_hz,
            }
            for event in plan.events
        ]
        output = {
            "scene_id": plan.scene_id,
            "backend": "sim",
            "sample_rate_hz": plan.sample_rate_hz,
            "center_freq_hz": plan.center_freq_hz,
            "event_count": len(plan.events),
            "timeline": timeline,
        }
        output_path.write_text(json.dumps(output, indent=2) + "\n")
        return ReplayRunReport(
            backend="sim",
            event_count=len(plan.events),
            output_path=output_path,
            details={"timeline_span_s": (plan.events[-1].time_stop - plan.events[0].time_start) if plan.events else 0.0},
        )


class UhdReplayBackend(ReplayBackend):
    """Placeholder backend boundary for direct UHD replay."""

    def __init__(self, out_root: Path, radio_config: str | Path | None = None):
        super().__init__(out_root)
        self.radio_config = None if radio_config is None else Path(radio_config)

    def run(self, plan: ReplayPlan) -> ReplayRunReport:
        try:
            import uhd  # type: ignore  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError("UHD Python bindings are not installed; use backend='sim' or install UHD") from exc
        raise NotImplementedError("Direct UHD replay is scaffolded but not implemented in milestone 1")
