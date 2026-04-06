"""Plotting and visual verification for rendered Python-native artifacts."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-rfsynth")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

from rfsynth.native.models import ArtifactBundle, PlotBundle


@dataclass
class Box:
    """Time-frequency rectangle extracted from metadata for plotting."""

    time_start: float
    time_stop: float
    freq_lo: float
    freq_hi: float
    label: str
    family: str


def plot_artifacts(bundle_or_base: ArtifactBundle | str | Path) -> PlotBundle:
    """Generate the standard PNG plot bundle for one rendered scene."""

    bundle = resolve_bundle(bundle_or_base)
    with bundle.metadata_path.open() as f:
        metadata = json.load(f)
    iq = read_cf32(bundle.iq_path)
    fs = float(metadata["rxObj"]["sampleRate_Hz"])
    fc = float(metadata["rxObj"]["freqCenter_Hz"])
    signal_boxes, energy_boxes = extract_boxes(metadata)
    spec_db, time_s, freq_hz = compute_spectrogram(iq, fs, fc)

    paths = {
        "time": plot_time(bundle.base_path, iq, fs),
        "psd": plot_psd(bundle.base_path, iq, fs, fc),
        "spectrogram": plot_spectrogram(bundle.base_path, spec_db, time_s, freq_hz, fc, signal_boxes, energy_boxes, overlay=False),
        "occupancy": plot_occupancy(bundle.base_path, time_s, freq_hz, fc, signal_boxes, energy_boxes, overlay=False),
        "fullband_overlay": plot_spectrogram(bundle.base_path, spec_db, time_s, freq_hz, fc, signal_boxes, energy_boxes, overlay=True),
        "fullband_occupancy": plot_occupancy(bundle.base_path, time_s, freq_hz, fc, signal_boxes, energy_boxes, overlay=True),
    }
    xlim_ms, ylim_mhz = compute_zoom_limits(signal_boxes, fc, time_s, freq_hz)
    paths["zoom_overlay"] = plot_spectrogram(
        bundle.base_path,
        spec_db,
        time_s,
        freq_hz,
        fc,
        signal_boxes,
        energy_boxes,
        overlay=True,
        suffix="zoom_overlay",
        xlim_ms=xlim_ms,
        ylim_mhz=ylim_mhz,
    )
    paths["zoom_occupancy"] = plot_occupancy(
        bundle.base_path,
        time_s,
        freq_hz,
        fc,
        signal_boxes,
        energy_boxes,
        overlay=True,
        suffix="zoom_occupancy",
        xlim_ms=xlim_ms,
        ylim_mhz=ylim_mhz,
    )
    return PlotBundle(base_path=bundle.base_path, paths=paths)


def verify_artifacts(bundle_or_base: ArtifactBundle | str | Path) -> dict[str, Any]:
    """Run visual-alignment checks and write `<base>_verify.json`."""

    bundle = resolve_bundle(bundle_or_base)
    with bundle.metadata_path.open() as f:
        metadata = json.load(f)
    iq = read_cf32(bundle.iq_path)
    fs = float(metadata["rxObj"]["sampleRate_Hz"])
    fc = float(metadata["rxObj"]["freqCenter_Hz"])
    duration_s = len(iq) / fs
    signal_boxes, energy_boxes = extract_boxes(metadata)
    spec_db, time_s, freq_hz = compute_spectrogram(iq, fs, fc)

    verify = verify_alignment(iq, metadata, spec_db, time_s, freq_hz, signal_boxes, energy_boxes, duration_s)
    verify["base"] = str(bundle.base_path)
    verify["sample_rate_hz"] = fs
    verify["center_freq_hz"] = fc
    verify["duration_s"] = duration_s
    verify["signal_box_count"] = len(signal_boxes)
    verify["energy_box_count"] = len(energy_boxes)

    verify_path = Path(f"{bundle.base_path}_verify.json")
    verify_path.write_text(json.dumps(verify, indent=2) + "\n")
    return verify


def resolve_bundle(bundle_or_base: ArtifactBundle | str | Path) -> ArtifactBundle:
    """Accept either a full bundle or a base path and normalize to a bundle."""

    if isinstance(bundle_or_base, ArtifactBundle):
        return bundle_or_base
    base = Path(bundle_or_base)
    return ArtifactBundle(
        scene=None,  # type: ignore[arg-type]
        base_path=base,
        iq_path=base.with_suffix(".32cf"),
        metadata_path=base.with_suffix(".json"),
        scoring_path=Path(f"{base}_scoring.json"),
        metadata={},
        scoring={},
        signals=[],
        iq=np.array([], dtype=np.complex64),
    )


def read_cf32(path: Path) -> np.ndarray:
    """Read interleaved float32 IQIQ... data into a complex vector."""

    raw = np.fromfile(path, dtype=np.float32)
    if raw.size % 2 != 0:
        raise ValueError(f"{path} does not contain an even number of float32 values")
    return raw[0::2] + 1j * raw[1::2]


def extract_boxes(metadata: dict) -> tuple[list[Box], list[Box]]:
    """Extract signal and transmission boxes from metadata JSON."""

    signal_boxes: list[Box] = []
    energy_boxes: list[Box] = []

    sources = metadata["sourceArray"]
    if isinstance(sources, dict):
        sources = [sources]

    for source in sources:
        signals = source["signalArray"]
        if isinstance(signals, dict):
            signals = [signals]
        for signal_obj in signals:
            md = signal_obj["requiredMetadata"]
            family = metadata_family(md)
            signal_boxes.append(
                Box(
                    time_start=float(md["time_start"]),
                    time_stop=float(md["time_stop"]),
                    freq_lo=float(md["freq_lo"]),
                    freq_hi=float(md["freq_hi"]),
                    label=str(md["instance_name"]),
                    family=family,
                )
            )
            transmissions = signal_obj.get("transmissionArray", [])
            if isinstance(transmissions, dict):
                transmissions = [transmissions]
            for tx in transmissions:
                energy_boxes.append(
                    Box(
                        time_start=float(tx["time_start"]),
                        time_stop=float(tx["time_stop"]),
                        freq_lo=float(tx["freq_lo"]),
                        freq_hi=float(tx["freq_hi"]),
                        label=str(tx["instance_name"]),
                        family=family,
                    )
                )
    return signal_boxes, energy_boxes


def compute_spectrogram(iq: np.ndarray, fs: float, fc: float, nfft: int = 4096, hop: int = 1024) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the spectrogram grid used by plot and verify flows."""

    if len(iq) < nfft:
        padded = np.zeros(nfft, dtype=np.complex64)
        padded[: len(iq)] = iq
        iq = padded

    frames = np.lib.stride_tricks.sliding_window_view(iq, nfft)[::hop]
    if len(frames) == 0:
        frames = iq[:nfft][None, :]
    window = np.hanning(nfft).astype(np.float32)
    spectra = np.fft.fftshift(np.fft.fft(frames * window[None, :], axis=1), axes=1)
    spec_db = 20.0 * np.log10(np.maximum(np.abs(spectra), 1e-12))
    time_s = (np.arange(spec_db.shape[0]) * hop + nfft / 2.0) / fs
    freq_hz = np.linspace(fc - fs / 2.0, fc + fs / 2.0, nfft, endpoint=False)
    return spec_db.T, time_s, freq_hz


def plot_time(base: Path, iq: np.ndarray, fs: float) -> Path:
    duration_ms = min(2.0, 1000.0 * len(iq) / fs)
    sample_count = max(1, int(round(duration_ms * 1e-3 * fs)))
    t_ms = np.arange(sample_count) / fs * 1e3
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(t_ms, np.real(iq[:sample_count]), label="Real", linewidth=0.8)
    ax.plot(t_ms, np.abs(iq[:sample_count]), label="Magnitude", linewidth=0.8, alpha=0.8)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Synthetic IQ: first 2 ms")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    out = Path(f"{base}_time.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def plot_psd(base: Path, iq: np.ndarray, fs: float, fc: float, fft_len: int = 131072) -> Path:
    n = min(len(iq), fft_len)
    if n < 1024:
        n = len(iq)
    window = np.hanning(n)
    spectrum = np.fft.fftshift(np.fft.fft(iq[:n] * window, n=n))
    psd = 20.0 * np.log10(np.maximum(np.abs(spectrum), 1e-12))
    freq_mhz = np.linspace(-fs / 2.0, fs / 2.0, n, endpoint=False) / 1e6

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(freq_mhz, psd, linewidth=0.8)
    ax.set_xlabel(f"Frequency offset from {fc/1e9:.6f} GHz (MHz)")
    ax.set_ylabel("Magnitude (dBFS, uncalibrated)")
    ax.set_title("Full-band PSD")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    out = Path(f"{base}_psd.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def plot_spectrogram(base: Path, spec_db: np.ndarray, time_s: np.ndarray, freq_hz: np.ndarray, fc: float, signal_boxes: list[Box], energy_boxes: list[Box], overlay: bool, suffix: str | None = None, xlim_ms: tuple[float, float] | None = None, ylim_mhz: tuple[float, float] | None = None) -> Path:
    fig, ax = plt.subplots(figsize=(13, 6))
    extent = [time_s[0] * 1e3, time_s[-1] * 1e3, (freq_hz[0] - fc) / 1e6, (freq_hz[-1] - fc) / 1e6]
    im = ax.imshow(spec_db, origin="lower", aspect="auto", extent=extent, cmap="magma", vmin=np.percentile(spec_db, 15), vmax=np.percentile(spec_db, 99.7))
    fig.colorbar(im, ax=ax, pad=0.01, label="Magnitude (dB)")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel(f"Frequency offset from {fc/1e9:.6f} GHz (MHz)")
    ax.set_title("Zoomed spectrogram" if (xlim_ms is not None or ylim_mhz is not None) else "Full-band spectrogram")
    if overlay:
        color_map = family_color_map(signal_boxes + energy_boxes)
        add_boxes(ax, signal_boxes, fc, color_map, linestyle="--", linewidth=1.5, fill_alpha=0.0)
        add_boxes(ax, energy_boxes, fc, color_map, linestyle="-", linewidth=0.9, fill_alpha=0.0)
        add_family_legend(ax, color_map)
        suffix = suffix or "fullband_overlay"
    else:
        suffix = suffix or "spectrogram"
    if xlim_ms is not None:
        ax.set_xlim(*xlim_ms)
    if ylim_mhz is not None:
        ax.set_ylim(*ylim_mhz)
    fig.tight_layout()
    out = Path(f"{base}_{suffix}.png")
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_occupancy(base: Path, time_s: np.ndarray, freq_hz: np.ndarray, fc: float, signal_boxes: list[Box], energy_boxes: list[Box], overlay: bool, suffix: str | None = None, xlim_ms: tuple[float, float] | None = None, ylim_mhz: tuple[float, float] | None = None) -> Path:
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.set_xlim(time_s[0] * 1e3, time_s[-1] * 1e3)
    ax.set_ylim((freq_hz[0] - fc) / 1e6, (freq_hz[-1] - fc) / 1e6)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel(f"Frequency offset from {fc/1e9:.6f} GHz (MHz)")
    ax.set_title("Zoomed metadata occupancy" if (xlim_ms is not None or ylim_mhz is not None) else "Metadata occupancy")
    color_map = family_color_map(signal_boxes + energy_boxes)
    add_boxes(ax, signal_boxes, fc, color_map, linestyle="--", linewidth=1.2, fill_alpha=0.16)
    add_boxes(ax, energy_boxes, fc, color_map, linestyle="-", linewidth=0.9, fill_alpha=0.0)
    add_family_legend(ax, color_map)
    if xlim_ms is not None:
        ax.set_xlim(*xlim_ms)
    if ylim_mhz is not None:
        ax.set_ylim(*ylim_mhz)
    fig.tight_layout()
    suffix = suffix or ("fullband_occupancy" if overlay else "occupancy")
    out = Path(f"{base}_{suffix}.png")
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def add_boxes(ax, boxes: list[Box], fc: float, color_map: dict[str, str], linestyle: str, linewidth: float, fill_alpha: float) -> None:
    for box in boxes:
        rect = Rectangle(
            (box.time_start * 1e3, (box.freq_lo - fc) / 1e6),
            (box.time_stop - box.time_start) * 1e3,
            (box.freq_hi - box.freq_lo) / 1e6,
            edgecolor=color_map[box.family],
            linestyle=linestyle,
            linewidth=linewidth,
            facecolor=to_rgba(color_map[box.family], fill_alpha),
        )
        ax.add_patch(rect)


def add_family_legend(ax, color_map: dict[str, str]) -> None:
    handles = [Line2D([0], [0], color=color, lw=2, label=family_label(family)) for family, color in color_map.items()]
    if handles:
        ax.legend(handles=handles, loc="upper right", framealpha=0.85, fontsize=8)


def metadata_family(md: dict) -> str:
    for key in ("modulation", "protocol"):
        value = str(md.get(key, "")).strip().lower()
        if value and value not in {"unknown", "no_answer"}:
            return value
    return normalize_family(str(md.get("instance_name", ""))) or "unknown"


def family_color_map(boxes: list[Box]) -> dict[str, str]:
    preferred = {
        "am": "#ff4d4f",
        "ofdm": "#2f80ed",
        "fm": "#ff8c42",
        "ssb": "#b36bff",
        "sine": "#e84393",
        "fsk2": "#17a398",
        "fsk4": "#17a398",
        "gfsk": "#00a878",
        "gmsk": "#1b998b",
        "msk": "#2d9cdb",
        "cpfsk": "#16a085",
        "pam": "#9b59b6",
        "psk": "#00bcd4",
        "qpsk": "#00bcd4",
        "bpsk": "#00bcd4",
        "qam": "#f39c12",
        "qam16": "#f39c12",
        "wlan_non_ht_802_11_g": "#27ae60",
        "wlannonht80211g": "#27ae60",
        "gmsk": "#1b998b",
        "fh": "#8d6e63",
        "unknown": "#c0c0c0",
    }
    fallback = ["#2f80ed", "#ff4d4f", "#27ae60", "#f39c12", "#9b59b6", "#00bcd4", "#e67e22", "#17a398"]
    color_map: dict[str, str] = {}
    fallback_idx = 0
    for family in dict.fromkeys(box.family for box in boxes):
        if family in preferred:
            color_map[family] = preferred[family]
        else:
            color_map[family] = fallback[fallback_idx % len(fallback)]
            fallback_idx += 1
    return color_map


def to_rgba(hex_color: str, alpha: float) -> tuple[float, float, float, float]:
    hex_color = hex_color.lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return rgb + (alpha,)


def compute_zoom_limits(signal_boxes: list[Box], fc: float, time_s: np.ndarray, freq_hz: np.ndarray) -> tuple[tuple[float, float], tuple[float, float]]:
    min_time = min(box.time_start for box in signal_boxes)
    max_time = max(box.time_stop for box in signal_boxes)
    min_freq = min(box.freq_lo for box in signal_boxes)
    max_freq = max(box.freq_hi for box in signal_boxes)
    time_pad = max(0.5e-3, 0.1 * (max_time - min_time))
    freq_pad = max(0.25e6, 0.15 * (max_freq - min_freq))
    return (
        max(time_s[0] * 1e3, (min_time - time_pad) * 1e3),
        min(time_s[-1] * 1e3, (max_time + time_pad) * 1e3),
    ), (
        max((freq_hz[0] - fc) / 1e6, (min_freq - freq_pad - fc) / 1e6),
        min((freq_hz[-1] - fc) / 1e6, (max_freq + freq_pad - fc) / 1e6),
    )


def normalize_family(value: str) -> str:
    value = value.strip().lower()
    value = value.removeprefix("atomic.")
    value = re.sub(r"_[0-9a-f]+$", "", value)
    return value


def family_label(family: str) -> str:
    labels = {
        "am": "AM",
        "ofdm": "OFDM",
        "fm": "FM",
        "ssb": "SSB",
        "sine": "Tone",
        "fsk2": "FSK2",
        "fsk4": "FSK4",
        "gfsk": "GFSK",
        "gmsk": "GMSK",
        "msk": "MSK",
        "cpfsk": "CPFSK",
        "pam": "PAM",
        "psk": "PSK",
        "qpsk": "QPSK",
        "bpsk": "BPSK",
        "qam": "QAM",
        "qam16": "QAM16",
        "wlannonht80211g": "WLAN",
        "wlan_non_ht_802_11_g": "WLAN",
        "fh": "FH",
        "unknown": "Unknown",
    }
    return labels.get(family, family.upper())


def verify_alignment(iq: np.ndarray, metadata: dict, spec_db: np.ndarray, time_s: np.ndarray, freq_hz: np.ndarray, signal_boxes: list[Box], energy_boxes: list[Box], duration_s: float) -> dict[str, Any]:
    signal_mask = build_mask(time_s, freq_hz, signal_boxes)
    energy_mask = build_mask(time_s, freq_hz, energy_boxes)
    global_floor = float(np.median(spec_db))
    signal_empty = [box.label for box in signal_boxes if box_peak(spec_db, time_s, freq_hz, box) < global_floor + 6.0]
    energy_empty = [box.label for box in energy_boxes if box_peak(spec_db, time_s, freq_hz, box) < global_floor + 6.0]

    percentile_stats = {}
    for percentile in (99.0, 99.5, 99.9):
        threshold = np.percentile(spec_db, percentile)
        hot = spec_db >= threshold
        total = int(np.count_nonzero(hot))
        inside_signal = int(np.count_nonzero(hot & signal_mask))
        inside_energy = int(np.count_nonzero(hot & energy_mask))
        percentile_stats[f"top_{100.0 - percentile:.1f}_percent"] = {
            "threshold_db": float(threshold),
            "total_pixels": total,
            "inside_signal_boxes": inside_signal,
            "inside_energy_boxes": inside_energy,
            "outside_signal_boxes": int(total - inside_signal),
            "signal_coverage_ratio": float(inside_signal / total) if total else math.nan,
            "energy_coverage_ratio": float(inside_energy / total) if total else math.nan,
        }

    full_span_signal = any(is_nearly_full_span(box, duration_s, freq_hz) for box in signal_boxes)
    ratios = energy_inband_ratios(iq, metadata, energy_boxes)
    finite = [x for x in ratios if np.isfinite(x)]
    min_ratio = float(min(finite)) if finite else math.nan
    top_half = percentile_stats["top_0.5_percent"]
    top_tenth = percentile_stats["top_0.1_percent"]

    if full_span_signal:
        verdict = "Visual pass" if not signal_empty else "Inconclusive"
    elif signal_empty or energy_empty:
        verdict = "Visual fail"
    elif finite and min_ratio >= 0.9:
        verdict = "Visual pass"
    elif top_tenth["signal_coverage_ratio"] >= 0.99 and top_tenth["energy_coverage_ratio"] >= 0.95:
        verdict = "Visual pass"
    elif top_half["signal_coverage_ratio"] >= 0.95 and top_half["energy_coverage_ratio"] >= 0.9:
        verdict = "Visual pass"
    else:
        verdict = "Inconclusive"
    return {
        "verdict": verdict,
        "empty_signal_boxes": signal_empty,
        "empty_energy_boxes": energy_empty,
        "per_energy_inband_ratios": ratios,
        "min_energy_inband_ratio": min_ratio,
        "percentile_stats": percentile_stats,
    }


def build_mask(time_s: np.ndarray, freq_hz: np.ndarray, boxes: list[Box]) -> np.ndarray:
    mask = np.zeros((len(freq_hz), len(time_s)), dtype=bool)
    for box in boxes:
        t_sel = (time_s >= box.time_start) & (time_s <= box.time_stop)
        f_sel = (freq_hz >= box.freq_lo) & (freq_hz <= box.freq_hi)
        if np.any(t_sel) and np.any(f_sel):
            mask[np.ix_(f_sel, t_sel)] = True
    return mask


def box_peak(spec_db: np.ndarray, time_s: np.ndarray, freq_hz: np.ndarray, box: Box) -> float:
    t_sel = (time_s >= box.time_start) & (time_s <= box.time_stop)
    f_sel = (freq_hz >= box.freq_lo) & (freq_hz <= box.freq_hi)
    if not np.any(t_sel) or not np.any(f_sel):
        return float("-inf")
    return float(np.max(spec_db[np.ix_(f_sel, t_sel)]))


def is_nearly_full_span(box: Box, duration_s: float, freq_hz: np.ndarray) -> bool:
    total_bw = float(freq_hz[-1] - freq_hz[0])
    return (box.time_stop - box.time_start) >= 0.95 * duration_s and (box.freq_hi - box.freq_lo) >= 0.95 * total_bw


def energy_inband_ratios(iq: np.ndarray, metadata: dict, energy_boxes: list[Box]) -> list[float]:
    fs = float(metadata["rxObj"]["sampleRate_Hz"])
    fc = float(metadata["rxObj"]["freqCenter_Hz"])
    ratios: list[float] = []
    for box in energy_boxes:
        start = max(0, int(round(box.time_start * fs)))
        stop = min(len(iq), int(round(box.time_stop * fs)))
        if stop <= start:
            ratios.append(math.nan)
            continue
        chunk = iq[start:stop]
        if not np.any(chunk):
            ratios.append(math.nan)
            continue
        n = max(16384, 1 << (len(chunk) - 1).bit_length())
        spectrum = np.fft.fftshift(np.fft.fft(chunk * np.hanning(len(chunk)), n=n))
        power = np.abs(spectrum) ** 2
        freqs = np.linspace(fc - fs / 2.0, fc + fs / 2.0, n, endpoint=False)
        guard = (freqs >= box.freq_lo) & (freqs <= box.freq_hi)
        ratios.append(float(power[guard].sum() / power.sum()))
    return ratios
