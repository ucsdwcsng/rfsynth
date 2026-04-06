"""Scene normalization for the Python-native runtime.

This module translates either the short JSON schema or the legacy verbose JSON
schema into the runtime object model used by `VirtualSignalEngine`. Atomic
construction always goes through `build_signal(...) -> create_signal(...)`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rfsynth.native.atomic import create_signal
from rfsynth.native.core import Rx, Scene, Source, Traffic
from rfsynth.native.models import GenerationSpec


DEFAULT_REPO_OUTPUT = Path("/tmp")


def load_scene(path_or_dict: str | Path | dict[str, Any]) -> Scene:
    """Load JSON or a dict and normalize it into a `Scene`."""

    if isinstance(path_or_dict, (str, Path)):
        path = Path(path_or_dict)
        with path.open() as f:
            cfg = json.load(f)
    else:
        path = None
        cfg = dict(path_or_dict)

    generation = normalize_generation(cfg, path)
    rx = normalize_rx(cfg)
    sources = normalize_sources(cfg, generation.total_time_s)
    return Scene(generation=generation, rx=rx, sources=sources, raw_config=cfg)


def validate_scene(scene: Scene) -> dict[str, Any]:
    """Run lightweight structural checks on a normalized scene."""

    errors: list[str] = []
    if scene.generation.total_time_s <= 0:
        errors.append("generation.total_time_s must be positive")
    if scene.rx.sample_rate_hz <= 0:
        errors.append("rx.sample_rate_hz must be positive")
    if not scene.sources:
        errors.append("scene must contain at least one source")
    for source in scene.sources:
        if not source.signals:
            errors.append(f"source {source.name} must contain at least one signal")
        for signal in source.signals:
            if "centerFreq_Hz" not in signal.args:
                errors.append(f"{source.name}/{signal.type_name}: centerFreq_Hz is required")
    return {"ok": not errors, "errors": errors}


def normalize_generation(cfg: dict[str, Any], path: Path | None) -> GenerationSpec:
    """Normalize generation/output settings from either accepted JSON schema."""

    generation = dict(cfg.get("generationParameters", {}))
    output = dict(cfg.get("output", {}))
    output_base = generation.get("outputBase", output.get("outputBase"))
    if output_base is None:
        output_base = path.stem if path is not None else "scene"
    output_folder = Path(generation.get("outputFolder", output.get("outputFolder", DEFAULT_REPO_OUTPUT)))
    total_time_s = float(generation.get("tot_time", output.get("tot_time", 0.02)))
    flag_output = bool(generation.get("flagOutputIqSamples", output.get("flagOutputIqSamples", True)))
    return GenerationSpec(
        total_time_s=total_time_s,
        output_folder=output_folder,
        output_base=str(output_base),
        flag_output_iq_samples=flag_output,
    )


def normalize_rx(cfg: dict[str, Any]) -> Rx:
    """Normalize receiver fields into the runtime `Rx` object."""

    rx_cfg = dict(cfg.get("rxConfig", {}))
    short_rx = dict(cfg.get("rx", {}))
    sample_rate = rx_cfg.get("rxSampleRate_Hz", short_rx.get("rxSampleRate_Hz", short_rx.get("sampleRate_Hz")))
    center_freq = rx_cfg.get("centerFreq_Hz", short_rx.get("centerFreq_Hz"))
    location = tuple(float(x) for x in rx_cfg.get("location", short_rx.get("location", [0, 0, 0])))
    return Rx(
        name=str(rx_cfg.get("name", short_rx.get("name", "rx1"))),
        sample_rate_hz=float(sample_rate),
        center_freq_hz=float(center_freq),
        location=(location[0], location[1], location[2]),
    )


def normalize_sources(cfg: dict[str, Any], total_time_s: float) -> list[Source]:
    """Build runtime sources, auto-wrapping top-level signals when needed."""

    if "sources" in cfg:
        return [normalize_source(source, total_time_s) for source in cfg["sources"]]

    sources: list[Source] = []
    for idx, signal in enumerate(cfg.get("signals", []), start=1):
        source = Source(
            name=f"Source{idx}",
            origin="synthetic_json",
            location=(0.0, 0.0, 0.0),
            channel_model="IDENTITY",
            freq_offset_hz=0.0,
            iq_imbalance=(0.0, 0.0),
            dc_offset=(0.0, 0.0),
        )
        source.add_signal(build_signal(signal, total_time_s))
        sources.append(source)
    return sources


def normalize_source(source: dict[str, Any], total_time_s: float) -> Source:
    """Normalize one explicit source entry and attach its signals."""

    location = tuple(float(x) for x in source.get("location", [0, 0, 0]))
    spec = Source(
        name=str(source.get("name", "Source")),
        origin=str(source.get("origin", "synthetic_json")),
        location=(location[0], location[1], location[2]),
        channel_model=str(source.get("channelModel", "IDENTITY")),
        freq_offset_hz=float(source.get("freqOffset_Hz", 0.0)),
        iq_imbalance=tuple(float(x) for x in source.get("iqImbalance", [0, 0])),
        dc_offset=tuple(float(x) for x in source.get("dcOffset", [0, 0])),
    )
    for signal in source.get("signals", []):
        spec.add_signal(build_signal(signal, total_time_s))
    return spec


def normalize_signal_args(signal: dict[str, Any]) -> dict[str, Any]:
    """Extract the atomic argument dict from short or verbose signal syntax."""

    args = dict(signal.get("args", {}))
    if not args:
        args = {k: v for k, v in signal.items() if k != "type"}
    if "trafficType" not in args and str(signal["type"]) != "WidebandThermalWgn":
        args["trafficType"] = {"type": "periodic", "transmissionPerSec": 100}
    return args


def parse_traffic(spec: dict[str, Any] | str | None, total_time_s: float) -> Traffic:
    """Normalize traffic config into the runtime `Traffic` model."""

    if spec is None:
        return Traffic(traffic_type="periodic", transmission_per_sec=100.0)
    if isinstance(spec, str):
        return Traffic(traffic_type=spec)
    traffic_type = str(spec.get("type", "periodic"))
    time_on = spec.get("timeOn")
    return Traffic(
        traffic_type=traffic_type,
        start_time=float(spec.get("startTime", 0.0)),
        stop_time=float(spec.get("stopTime", total_time_s if time_on is None else spec.get("stopTime", total_time_s))),
        transmission_per_sec=(
            None
            if spec.get("transmissionPerSec") is None
            else float(spec.get("transmissionPerSec"))
        ),
        arrival_array=tuple(float(x) for x in spec.get("arrivalArray", [])),
        time_on=None if time_on is None else float(time_on),
    )


def build_signal(signal: dict[str, Any], total_time_s: float):
    """Construct one runtime atomic via the registry-backed factory."""

    args = normalize_signal_args(signal)
    traffic = parse_traffic(args.get("trafficType"), total_time_s)
    return create_signal(str(signal["type"]), args=args, traffic=traffic)
