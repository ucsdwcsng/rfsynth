"""Core runtime object model and render loop for the Python-native path.

The call chain that matters most is:

`Scene -> VirtualSignalEngine.generate_samples() -> Source.generate_samples()`
`-> Signal.generate_transmission() -> resample/frequency shift/place_burst`.

Atomic-specific waveform logic lives outside this file; this module owns scene
assembly, burst placement, metadata generation, and artifact writing.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal as scipy_signal

from rfsynth.native.models import ArtifactBundle, GenerationSpec, SignalRenderResult, TransmissionWindow


@dataclass(slots=True)
class GeneratedBurst:
    """One atomic burst produced at the atomic's native sample rate."""

    samples: np.ndarray
    sample_rate_hz: float
    bandwidth_hz: float
    protocol: str
    modality: str
    modulation: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Rx:
    """Receiver viewpoint that defines the final composite output rate and LO."""

    name: str
    sample_rate_hz: float
    center_freq_hz: float
    location: tuple[float, float, float]


@dataclass(slots=True)
class Traffic:
    """Timing policy for a signal's repeated transmissions."""

    traffic_type: str
    start_time: float = 0.0
    stop_time: float = float("inf")
    transmission_per_sec: float | None = None
    arrival_array: tuple[float, ...] = ()
    time_on: float | None = None

    def transmission_start_times(self, total_time_s: float) -> list[float]:
        """Expand the traffic spec into transmission start times."""

        stop_time = min(total_time_s, self.stop_time)
        if self.traffic_type == "customArray":
            return [t for t in self.arrival_array if self.start_time <= t <= stop_time]
        if self.traffic_type == "constant":
            return [self.start_time] if self.start_time <= stop_time else []
        if self.traffic_type != "periodic":
            raise ValueError(f"Unsupported traffic type in Python-native renderer: {self.traffic_type}")
        if self.transmission_per_sec is None or self.transmission_per_sec <= 0:
            raise ValueError("periodic traffic requires transmissionPerSec > 0")
        span = max(0.0, stop_time - self.start_time)
        n_tx = int(math.ceil(span * self.transmission_per_sec))
        starts = [self.start_time + (i / self.transmission_per_sec) for i in range(max(0, n_tx))]
        return [t for t in starts if self.start_time <= t <= stop_time]


class Signal:
    """Base class for all Python-native atomics.

    Each atomic subclass implements `generate_transmission(...)` and returns one
    `GeneratedBurst`. The source loop later reuses that burst for every traffic
    window in the scene.
    """

    def __init__(self, type_name: str, args: dict[str, Any], traffic: Traffic | None = None):
        self.type_name = type_name
        self.args = args
        self.traffic = traffic if traffic is not None else Traffic(traffic_type="periodic", transmission_per_sec=100.0)
        self.source: Source | None = None

    def attach_source(self, source: Source) -> None:
        """Back-reference the source that owns this signal."""

        self.source = source

    @property
    def source_name(self) -> str:
        """Human-readable source name used in metadata output."""

        return self.source.name if self.source is not None else "Source"

    @property
    def instance_name(self) -> str:
        """Stable instance identifier derived from the type, source, and args."""

        payload = {
            "type": self.type_name,
            "source": self.source_name,
            "args": canonicalize(self.args),
        }
        digest = hashlib.md5(repr(payload).encode("utf-8")).hexdigest()[:8]
        return f"atomic.{self.type_name}_{digest}"

    def burst_duration_s(self) -> float:
        """Best-effort burst duration used when an atomic does not override it."""

        if self.type_name == "WidebandThermalWgn":
            raise ValueError("WidebandThermalWgn duration depends on scene total time")
        if "transmissionTotTime" in self.args:
            return float(self.args["transmissionTotTime"])
        if self.type_name == "Bluetooth":
            return 680e-6
        if self.type_name == "WlanNonHT80211g":
            return 112e-6
        return 4e-3

    def compute_transmission_windows(self, scene: Scene, duration_s_override: float | None = None) -> list[TransmissionWindow]:
        """Convert traffic settings into concrete placement windows."""

        if self.type_name == "WidebandThermalWgn":
            return [TransmissionWindow(start_time=0.0, stop_time=scene.generation.total_time_s)]
        starts = self.traffic.transmission_start_times(scene.generation.total_time_s)
        duration_s = duration_s_override if duration_s_override is not None else self.burst_duration_s()
        return [
            TransmissionWindow(
                start_time=start,
                stop_time=min(scene.generation.total_time_s, start + duration_s),
            )
            for start in starts
        ]

    def generate_transmission(self, scene: Scene, rng: np.random.Generator) -> GeneratedBurst:
        """Generate one native-rate burst for this atomic."""

        raise NotImplementedError

    def build_render_result(
        self,
        scene: Scene,
        source: Source,
        burst: GeneratedBurst,
        windows: list[TransmissionWindow],
    ) -> SignalRenderResult:
        """Assemble per-signal metadata after placement decisions are known."""

        transmission_reports = [
            {
                "report_type": "energy",
                "instance_name": f"{self.instance_name} T_{idx}",
                "time_start": window.start_time,
                "time_stop": window.stop_time,
                "freq_lo": float(self.args["centerFreq_Hz"]) - burst.bandwidth_hz / 2.0,
                "freq_hi": float(self.args["centerFreq_Hz"]) + burst.bandwidth_hz / 2.0,
            }
            for idx, window in enumerate(windows, start=1)
        ]
        required_metadata = {
            "report_type": "signal",
            "instance_name": self.instance_name,
            "protocol": burst.protocol,
            "modality": burst.modality,
            "modulation": burst.modulation,
            "activity_type": "overt_baseline",
            "time_start": min(window.start_time for window in windows),
            "time_stop": max(window.stop_time for window in windows),
            "freq_lo": float(self.args["centerFreq_Hz"]) - burst.bandwidth_hz / 2.0,
            "freq_hi": float(self.args["centerFreq_Hz"]) + burst.bandwidth_hz / 2.0,
            "rx_center_freq": {scene.rx.name: scene.rx.center_freq_hz},
            "rx_sample_rate": {scene.rx.name: scene.rx.sample_rate_hz},
            "rx_input_snr": {scene.rx.name: 1000},
        }
        return SignalRenderResult(
            instance_name=self.instance_name,
            source_name=source.name,
            source_origin=source.origin,
            source_location=source.location,
            channel_model=source.channel_model,
            signal_type=self.type_name,
            protocol=burst.protocol,
            modality=burst.modality,
            modulation=burst.modulation,
            center_freq_hz=float(self.args["centerFreq_Hz"]),
            bandwidth_hz=burst.bandwidth_hz,
            tx_power_db=float(self.args.get("txPower_db", -70)),
            burst_sample_rate_hz=burst.sample_rate_hz,
            transmissions=windows,
            required_metadata=required_metadata,
            transmission_reports=transmission_reports,
            extras=dict(burst.extras),
        )


@dataclass(slots=True)
class Source:
    """Emitter-level container for signals plus source-side impairments."""

    name: str
    origin: str
    location: tuple[float, float, float]
    channel_model: str
    freq_offset_hz: float
    iq_imbalance: tuple[float, float]
    dc_offset: tuple[float, float]
    signals: list[Signal] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Attach this source to any signals provided at construction time."""

        for signal in self.signals:
            signal.attach_source(self)

    def add_signal(self, signal: Signal) -> None:
        """Attach and store one additional signal on this source."""

        signal.attach_source(self)
        self.signals.append(signal)

    def apply_nonideal_transform(self, samples: np.ndarray) -> np.ndarray:
        """Apply simple IQ imbalance and DC offsets after resampling."""

        i_gain = 1.0 + float(self.iq_imbalance[0])
        q_gain = 1.0 + float(self.iq_imbalance[1])
        i = np.real(samples) * i_gain + float(self.dc_offset[0])
        q = np.imag(samples) * q_gain + float(self.dc_offset[1])
        return (i + 1j * q).astype(np.complex64)

    def apply_channel(self, samples: np.ndarray, signal: Signal, rx: Rx) -> np.ndarray:
        """Apply the source channel model.

        Milestone 1 keeps this as identity, but the call boundary mirrors the
        MATLAB source path so channel logic can be inserted without changing the
        render loop.
        """

        del signal, rx
        return samples

    def generate_samples(self, scene: Scene, composite: np.ndarray, rng: np.random.Generator) -> list[SignalRenderResult]:
        """Render every signal on this source into the shared Rx composite.

        This is the main Python-native hot path after scene normalization:

        1. call `signal.generate_transmission(...)`
        2. resample to the receiver sample rate when needed
        3. frequency-shift into the receiver-centered band
        4. apply source impairments and channel
        5. compute traffic windows and place the burst for each window
        6. assemble metadata for the rendered signal
        """

        rendered: list[SignalRenderResult] = []
        for signal in self.signals:
            burst = signal.generate_transmission(scene, rng)
            burst_rs = resample_if_needed(burst.samples, burst.sample_rate_hz, scene.rx.sample_rate_hz)
            freq_offset = float(signal.args["centerFreq_Hz"]) - scene.rx.center_freq_hz + self.freq_offset_hz
            if abs(freq_offset) > 1e-6:
                burst_rs = frequency_shift(burst_rs, scene.rx.sample_rate_hz, freq_offset)
            burst_rs = self.apply_nonideal_transform(burst_rs)
            burst_rs = self.apply_channel(burst_rs, signal, scene.rx)
            windows = signal.compute_transmission_windows(
                scene,
                duration_s_override=len(burst.samples) / burst.sample_rate_hz,
            )
            for window in windows:
                place_burst(composite, burst_rs, window, scene.rx.sample_rate_hz)
            rendered.append(signal.build_render_result(scene, self, burst, windows))
        return rendered


@dataclass(slots=True)
class Scene:
    """Fully normalized runtime scene consumed by `VirtualSignalEngine`."""

    generation: GenerationSpec
    rx: Rx
    sources: list[Source]
    raw_config: dict[str, Any]

    def all_signals(self) -> list[Signal]:
        """Return every signal across every source."""

        return [signal for source in self.sources for signal in source.signals]


class VirtualSignalEngine:
    """Top-level renderer for one normalized scene."""

    def __init__(self, scene: Scene):
        self.scene = scene

    def generate_samples(self, seed: int = 1234) -> tuple[np.ndarray, list[SignalRenderResult]]:
        """Build the composite IQ vector and per-signal render results."""

        total_samples = int(round(self.scene.generation.total_time_s * self.scene.rx.sample_rate_hz))
        composite = np.zeros(total_samples, dtype=np.complex64)
        rng = np.random.Generator(np.random.MT19937(seed))
        rendered_signals: list[SignalRenderResult] = []
        for source in self.scene.sources:
            rendered_signals.extend(source.generate_samples(self.scene, composite, rng))
        return composite, rendered_signals

    def build_metadata(self, rendered_signals: list[SignalRenderResult]) -> dict[str, Any]:
        """Assemble MATLAB-shaped metadata JSON from rendered signals."""

        source_map: dict[str, dict[str, Any]] = {}
        for rendered in rendered_signals:
            source = source_map.setdefault(
                rendered.source_name,
                {
                    "report_type": "source",
                    "device_origin": rendered.source_origin,
                    "instance_name": rendered.source_name,
                    "locationXYZ_m": list(rendered.source_location),
                    "channelModel": rendered.channel_model,
                    "signalArray": [],
                },
            )
            source["signalArray"].append(
                {
                    **rendered.extras,
                    "requiredMetadata": rendered.required_metadata,
                    "transmissionArray": rendered.transmission_reports,
                }
            )
        return {
            "sourceArray": list(source_map.values()),
            "rxObj": {
                "instance_name": self.scene.rx.name,
                "sampleRate_Hz": self.scene.rx.sample_rate_hz,
                "freqCenter_Hz": self.scene.rx.center_freq_hz,
                "location": list(self.scene.rx.location),
            },
        }

    def build_scoring(self, rendered_signals: list[SignalRenderResult]) -> dict[str, Any]:
        """Assemble the reduced scoring-oriented report JSON."""

        reports: list[dict[str, Any]] = []
        for rendered in rendered_signals:
            for tx in rendered.transmission_reports:
                reports.append(
                    {
                        "report_type": "energy",
                        "instance_name": tx["instance_name"],
                        "time_start": tx["time_start"],
                        "time_stop": tx["time_stop"],
                        "freq_lo": tx["freq_lo"] / 1e6,
                        "freq_hi": tx["freq_hi"] / 1e6,
                        "timeLength_s": tx["time_stop"] - tx["time_start"],
                        "bandwidth_Hz": (tx["freq_hi"] - tx["freq_lo"]) / 1e6,
                    }
                )
            reports.append(
                {
                    "report_type": "signal",
                    "instance_name": rendered.instance_name,
                    "protocol": rendered.protocol,
                    "modality": rendered.modality,
                    "modulation": rendered.modulation,
                    "activity_type": "overt_baseline",
                    "time_start": rendered.required_metadata["time_start"],
                    "time_stop": rendered.required_metadata["time_stop"],
                    "freq_lo": rendered.required_metadata["freq_lo"] / 1e6,
                    "freq_hi": rendered.required_metadata["freq_hi"] / 1e6,
                    "rx_center_freq": {self.scene.rx.name: self.scene.rx.center_freq_hz},
                    "rx_sample_rate": {self.scene.rx.name: self.scene.rx.sample_rate_hz},
                    "rx_input_snr": {self.scene.rx.name: 1000},
                    "reference_time": 0.5
                    * (rendered.required_metadata["time_start"] + rendered.required_metadata["time_stop"]),
                    "reference_freq": rendered.center_freq_hz / 1e6,
                    "timeLength_s": rendered.required_metadata["time_stop"] - rendered.required_metadata["time_start"],
                    "bandwidth_Hz": rendered.bandwidth_hz / 1e6,
                    "energy_set": [tx["instance_name"] for tx in rendered.transmission_reports],
                }
            )
        seen_sources: set[str] = set()
        for rendered in rendered_signals:
            if rendered.source_name in seen_sources:
                continue
            seen_sources.add(rendered.source_name)
            signal_set = [signal.instance_name for signal in rendered_signals if signal.source_name == rendered.source_name]
            reports.append(
                {
                    "report_type": "source",
                    "device_origin": rendered.source_origin,
                    "instance_name": rendered.source_name,
                    "tx": [],
                    "locationXYZ_m": list(rendered.source_location),
                    "outputSamplingRate_Hz": self.scene.rx.sample_rate_hz,
                    "channelModel": rendered.channel_model,
                    "nSignal": len(signal_set),
                    "signal_set": signal_set,
                }
            )
        reports.append(
            {
                "report_type": "receiver",
                "instance_name": self.scene.rx.name,
                "sampleRate_Hz": self.scene.rx.sample_rate_hz / 1e6,
                "freqCenter_Hz": self.scene.rx.center_freq_hz / 1e6,
                "location": list(self.scene.rx.location),
                "noiseProfile": [],
                "isOn": False,
            }
        )
        return {"reports": reports}

    def render(self, out_dir: str | Path | None = None, seed: int = 1234) -> ArtifactBundle:
        """Execute the full render and write `.32cf`, metadata, and scoring."""

        output_folder = Path(out_dir) if out_dir is not None else self.scene.generation.output_folder
        output_folder.mkdir(parents=True, exist_ok=True)
        base_path = output_folder / self.scene.generation.output_base
        composite, rendered_signals = self.generate_samples(seed=seed)
        iq_path = base_path.with_suffix(".32cf")
        write_cf32(iq_path, composite)
        metadata = self.build_metadata(rendered_signals)
        scoring = self.build_scoring(rendered_signals)
        metadata_path = base_path.with_suffix(".json")
        scoring_path = Path(f"{base_path}_scoring.json")
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        scoring_path.write_text(json.dumps(scoring, indent=2) + "\n")
        return ArtifactBundle(
            scene=self.scene,
            base_path=base_path,
            iq_path=iq_path,
            metadata_path=metadata_path,
            scoring_path=scoring_path,
            metadata=metadata,
            scoring=scoring,
            signals=rendered_signals,
            iq=composite,
        )


def canonicalize(value: Any) -> Any:
    """Recursively sort JSON-like values for stable hashing."""

    if isinstance(value, dict):
        return {k: canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [canonicalize(v) for v in value]
    return value


def frequency_shift(samples: np.ndarray, sample_rate_hz: float, freq_offset_hz: float) -> np.ndarray:
    """Mix a burst to a new center frequency inside the Rx passband."""

    n = np.arange(len(samples), dtype=np.float64)
    return (samples * np.exp(2j * np.pi * freq_offset_hz / sample_rate_hz * n)).astype(np.complex64)


def place_burst(composite: np.ndarray, burst: np.ndarray, window: TransmissionWindow, sample_rate_hz: float) -> None:
    """Add one burst into the shared composite buffer at the given window."""

    start = int(round(window.start_time * sample_rate_hz))
    stop = min(len(composite), start + len(burst))
    n = max(0, stop - start)
    if n:
        composite[start:stop] += burst[:n]


def resample_if_needed(samples: np.ndarray, fs_in: float, fs_out: float) -> np.ndarray:
    """Resample with a rational polyphase converter when rates differ."""

    if abs(fs_in - fs_out) < 1e-6:
        return samples.astype(np.complex64)
    ratio = Fraction(int(round(fs_out)), int(round(fs_in))).limit_denominator(10000)
    out = scipy_signal.resample_poly(samples, ratio.numerator, ratio.denominator)
    return out.astype(np.complex64)


def write_cf32(path: Path, iq: np.ndarray) -> None:
    """Write complex64 IQ as interleaved float32 IQIQ... samples."""

    raw = np.empty(iq.size * 2, dtype=np.float32)
    raw[0::2] = np.real(iq).astype(np.float32)
    raw[1::2] = np.imag(iq).astype(np.float32)
    raw.tofile(path)
