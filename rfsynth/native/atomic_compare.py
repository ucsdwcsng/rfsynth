from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as scipy_signal

from rfsynth.native.core import Scene, Signal
from rfsynth.native.atomic.common import matlab_like_ofdm_params
from rfsynth.native.plotting import compute_spectrogram
from rfsynth.native.scene import load_scene
from rfsynth.native.waveforms import qam_constellation, rrc_taps


@dataclass(slots=True)
class AtomicBurst:
    signal_type: str
    sample_rate_hz: float
    samples: np.ndarray


def load_single_signal(path_or_dict: str | Path | dict[str, Any]) -> tuple[Scene, Signal]:
    scene = load_scene(path_or_dict)
    signals = [signal for source in scene.sources for signal in source.signals]
    if len(signals) != 1:
        raise ValueError("Atomic compare requires exactly one signal in the config")
    return scene, signals[0]


def mt19937(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.MT19937(seed))


def generate_test_vector(config: str | Path | dict[str, Any], out_path: str | Path, seed: int = 1234) -> Path:
    scene, signal_spec = load_single_signal(config)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rng = mt19937(seed)

    payload: dict[str, Any] = {}
    signal_type = signal_spec.type_name
    if signal_type == "Qam":
        n_sym = max(1, int(round(float(signal_spec.args.get("transmissionTotTime", 0.004)) * float(signal_spec.args.get("transmissionRate_Hz", 1e6)))))
        constellation = qam_constellation(int(signal_spec.args.get("modOrder", 16)))
        idx = rng.integers(0, len(constellation), size=n_sym)
        symbols = constellation[idx]
        payload = {
            "symbols_real": np.real(symbols).tolist(),
            "symbols_imag": np.imag(symbols).tolist(),
        }
    elif signal_type == "Ofdm":
        params = matlab_like_ofdm_params(int(signal_spec.args.get("Nfft", 256)))
        n_syms = max(
            1,
            int(
                math.floor(
                    float(signal_spec.args.get("transmissionTotTime", 0.004))
                    * float(signal_spec.args.get("transmissionRate_Hz", 10e6))
                    / (params["n_sc"] + params["cp_len"])
                )
            ),
        )
        mod_order = int(signal_spec.args.get("modOrder", 4))
        constellation = qam_constellation(mod_order if mod_order > 2 else 4)
        data_symbols = constellation[rng.integers(0, len(constellation), size=(len(params["data_idx"]), n_syms))]
        pilot_symbols = np.tile(params["pilots"][:, None], (1, n_syms))
        payload = {
            "data_symbols_real": np.real(data_symbols).tolist(),
            "data_symbols_imag": np.imag(data_symbols).tolist(),
            "pilot_symbols_real": np.real(pilot_symbols).tolist(),
            "pilot_symbols_imag": np.imag(pilot_symbols).tolist(),
        }
    elif signal_type in {"Pam", "Psk", "RandomSymbol", "Fsk", "Cpfsk", "Gfsk", "Msk"}:
        n_sym = max(1, int(round(float(signal_spec.args.get("transmissionTotTime", 0.004)) * float(signal_spec.args.get("transmissionRate_Hz", 1e6)))))
        payload = {
            "symbol_indices": rng.integers(0, int(signal_spec.args.get("modOrder", 4)), size=n_sym).tolist(),
        }
    elif signal_type == "Gmsk":
        n_bits = max(1, int(round(float(signal_spec.args.get("transmissionTotTime", 0.004)) * float(signal_spec.args.get("transmissionRate_Hz", 250e3)))))
        payload = {"bits": rng.integers(0, 2, size=n_bits).tolist()}
    elif signal_type == "Bluetooth":
        message = signal_spec.args.get("message")
        if message is None:
            message = rng.integers(0, 2, size=640).tolist()
        access_address = signal_spec.args.get("accessAddress")
        if access_address is None:
            access_address = [0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1]
        payload = {
            "message_bits": np.asarray(message, dtype=np.int64).tolist(),
            "access_address_bits": np.asarray(access_address, dtype=np.int64).tolist(),
        }
    elif signal_type == "WlanNonHT80211g":
        message = signal_spec.args.get("message")
        if message is None:
            psdu_length = int(signal_spec.args.get("psduLength", 66))
            message = rng.integers(0, 2, size=psdu_length * 8).tolist()
        payload = {
            "message_bits": np.asarray(message, dtype=np.int64).tolist(),
            "scrambler_initialization": [int(signal_spec.args.get("scramblerInitialization", 93))],
        }
    elif signal_type == "LTE_DL_FDD":
        message = signal_spec.args.get("message")
        if message is None:
            message_path = signal_spec.args.get("messagePath")
            if message_path:
                raw = json.loads(Path(message_path).read_text())
                if "message_bits" in raw:
                    message = raw["message_bits"]
                else:
                    message = raw.get("payload", {}).get("message_bits")
        if message is None:
            # Narrow one-shot LTE preset currently uses a fixed 672-bit payload.
            message = rng.integers(0, 2, size=672).tolist()
        payload = {
            "message_bits": np.asarray(message, dtype=np.int64).tolist(),
        }
    elif signal_type == "Ds3":
        symbol_rate = float(signal_spec.args["bandwidth_Hz"]) / (2.0 * float(signal_spec.args.get("chipsPerSymbol", 1024)))
        n_sym = max(1, int(round(float(signal_spec.args.get("transmissionTotTime", 0.001)) * symbol_rate)))
        chips_per_symbol = int(signal_spec.args.get("chipsPerSymbol", 1024))
        spread_type = int(signal_spec.args.get("spreadType", 1))
        if spread_type == 1:
            spread_code = rng.choice([-1, 1], size=chips_per_symbol)
        else:
            spread_code = rng.choice([-1, 1], size=(chips_per_symbol, n_sym))
        payload = {
            "symbol_indices": rng.integers(0, int(signal_spec.args.get("modOrder", 2)), size=n_sym).tolist(),
            "spread_code": np.asarray(spread_code, dtype=np.int64).tolist(),
        }
    elif signal_type == "FreqHopping":
        n_hops = int(signal_spec.args.get("nHops", 5))
        bw_total = float(signal_spec.args.get("bandwidth_Hz", 10e6))
        bw_hop = float(signal_spec.args.get("bandwidthPerHop_Hz", 500e3))
        hop_centers = np.linspace(-bw_total / 2 + bw_hop / 2, bw_total / 2 - bw_hop / 2, n_hops)
        rng.shuffle(hop_centers)
        payload = {"hop_centers_hz": hop_centers.tolist()}
    elif signal_type == "WidebandThermalWgn":
        n = max(1, int(round(scene.generation.total_time_s * float(signal_spec.args.get("bandwidth_Hz", scene.rx.sample_rate_hz)))))
        samples = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
        payload = {
            "samples_real": np.real(samples).tolist(),
            "samples_imag": np.imag(samples).tolist(),
        }

    output = {
        "format": "rfsynth.atomic_test_vector.v1",
        "seed": seed,
        "signal_type": signal_spec.type_name,
        "payload": payload,
    }
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    return out_path


def generate_python_atomic_burst(config: str | Path | dict[str, Any], seed: int = 1234) -> AtomicBurst:
    scene, signal_spec = load_single_signal(config)
    rng = mt19937(seed)
    burst = signal_spec.generate_transmission(scene, rng)
    return AtomicBurst(signal_type=signal_spec.type_name, sample_rate_hz=burst.sample_rate_hz, samples=np.asarray(burst.samples, dtype=np.complex64))


def raw_sine(signal_spec: Signal) -> tuple[np.ndarray, float]:
    args = signal_spec.args
    fs = float(args.get("transmissionRate_Hz", 1e6))
    n_samples = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * fs)))
    n = np.arange(n_samples, dtype=np.float64)
    tone_offset = float(args.get("toneOffset_Hz", 100e3))
    return np.exp(2j * np.pi * tone_offset / fs * n), fs


def raw_am(signal_spec: Signal) -> tuple[np.ndarray, float]:
    args = signal_spec.args
    fs = float(args.get("transmissionRate_Hz", 500e3))
    n_samples = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * fs)))
    t = np.arange(n_samples, dtype=np.float64) / fs
    msg = np.sin(2 * np.pi * float(args.get("messageFreq_Hz", 5e3)) * t)
    envelope = 1.0 + float(args.get("modulationIndex", 0.8)) * msg
    return envelope.astype(np.complex128), fs


def raw_qam(signal_spec: Signal, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    args = signal_spec.args
    symbol_rate = float(args.get("transmissionRate_Hz", 1e6))
    sps = int(args.get("samplesPerSymbol", 8))
    beta = float(args.get("beta", 0.35))
    span = int(args.get("span", 10))
    vector = maybe_load_test_vector(args)
    if vector and "symbols" in vector:
        symbols = vector["symbols"]
    else:
        n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
        constellation = qam_constellation(int(args.get("modOrder", 16)))
        symbols = constellation[rng.integers(0, len(constellation), size=n_sym)]
    up = np.zeros(len(symbols) * sps, dtype=np.complex128)
    up[::sps] = symbols
    taps = rrc_taps(beta, span, sps)
    return np.convolve(up, taps, mode="same"), symbol_rate * sps


def raw_ofdm(signal_spec: Signal, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    args = signal_spec.args
    nfft = int(args.get("Nfft", 256))
    sample_rate_hz = float(args.get("transmissionRate_Hz", 10e6))
    params = matlab_like_ofdm_params(nfft)
    vector = maybe_load_test_vector(args)
    n_syms = max(
        1,
        int(math.floor(float(args.get("transmissionTotTime", 0.004)) * sample_rate_hz / (nfft + params["cp_len"]))),
    )
    if vector and "data_symbols" in vector:
        data_symbols = vector["data_symbols"]
        pilot_symbols = vector["pilot_symbols"]
        n_syms = data_symbols.shape[1]
    else:
        mod_order = int(args.get("modOrder", 4))
        constellation = qam_constellation(mod_order if mod_order > 2 else 4)
        data_symbols = constellation[rng.integers(0, len(constellation), size=(len(params["data_idx"]), n_syms))]
        pilot_symbols = np.tile(params["pilots"][:, None], (1, n_syms))

    ifft_in = np.zeros((nfft, n_syms), dtype=np.complex128)
    ifft_in[params["data_idx"], :] = data_symbols
    ifft_in[params["pilot_idx"], :] = pilot_symbols
    payload = np.fft.ifft(ifft_in, axis=0)
    if params["cp_len"] > 0:
        payload = np.vstack([payload[-params["cp_len"] :, :], payload])
    payload_vec = payload.reshape(-1, order="F")
    preamble = np.concatenate([params["lts_t"][nfft // 2 :], params["lts_t"], params["lts_t"]])
    tx_vec = np.concatenate([preamble, payload_vec])
    tx_vec = tx_vec / np.max(np.abs(tx_vec))
    return tx_vec, sample_rate_hz


def maybe_load_test_vector(args: dict[str, Any]) -> dict[str, np.ndarray] | None:
    path = args.get("testVectorPath")
    if not path:
        return None
    payload = json.loads(Path(path).read_text()).get("payload", {})
    out: dict[str, np.ndarray] = {}
    if "symbols_real" in payload:
        out["symbols"] = np.asarray(payload["symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["symbols_imag"], dtype=np.float64)
    if "data_symbols_real" in payload:
        out["data_symbols"] = np.asarray(payload["data_symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["data_symbols_imag"], dtype=np.float64)
    if "pilot_symbols_real" in payload:
        out["pilot_symbols"] = np.asarray(payload["pilot_symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["pilot_symbols_imag"], dtype=np.float64)
    return out


def write_cf32(path: str | Path, samples: np.ndarray) -> Path:
    path = Path(path)
    raw = np.empty(samples.size * 2, dtype=np.float32)
    raw[0::2] = np.real(samples).astype(np.float32)
    raw[1::2] = np.imag(samples).astype(np.float32)
    raw.tofile(path)
    return path


def compare_iq(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    *,
    drop_first_samples: int = 100,
    xcorr_window_samples: int = 131072,
) -> dict[str, Any]:
    prepared = prepare_compare_inputs(
        python_samples,
        matlab_samples,
        drop_first_samples=drop_first_samples,
        xcorr_window_samples=xcorr_window_samples,
    )
    python_samples = prepared["python_aligned"]
    matlab_samples = prepared["matlab_aligned"]
    sample_count = min(len(python_samples), len(matlab_samples))
    python_samples = python_samples[:sample_count]
    matlab_samples = matlab_samples[:sample_count]
    diff = python_samples - matlab_samples
    denom = float(np.linalg.norm(matlab_samples))
    if denom == 0.0:
        denom = 1.0
    py_norm = float(np.linalg.norm(python_samples))
    ml_norm = float(np.linalg.norm(matlab_samples))
    corr_mag = 0.0 if py_norm == 0.0 or ml_norm == 0.0 else float(abs(np.vdot(python_samples, matlab_samples)) / (py_norm * ml_norm))
    gain = complex(np.vdot(python_samples, matlab_samples) / np.vdot(python_samples, python_samples)) if py_norm > 0.0 else 0.0j
    if sample_count == 0:
        rmse = 0.0
        rel_rmse = 0.0
        max_abs_error = 0.0
        gain_aligned_rel_rmse = 0.0
        exact_match = True
        allclose = True
    else:
        rmse = float(np.sqrt(np.mean(np.abs(diff) ** 2)))
        rel_rmse = float(np.linalg.norm(diff) / denom)
        max_abs_error = float(np.max(np.abs(diff)))
        gain_aligned_rel_rmse = float(np.linalg.norm(gain * python_samples - matlab_samples) / denom)
        exact_match = bool(np.array_equal(python_samples, matlab_samples))
        allclose = bool(np.allclose(python_samples, matlab_samples, atol=1e-6, rtol=1e-6))
    return {
        "drop_first_samples": int(drop_first_samples),
        "cross_correlation_window_samples": int(prepared["xcorr_window_samples"]),
        "cross_correlation_peak_magnitude": float(prepared["xcorr_peak_magnitude"]),
        "cross_correlation_peak_phase_rad": float(prepared["xcorr_peak_phase_rad"]),
        "cross_correlation_peak_lag_samples": int(prepared["xcorr_peak_lag_samples"]),
        "sample_count_compared": int(sample_count),
        "exact_match": exact_match,
        "allclose_atol_1e-6": allclose,
        "rmse": rmse,
        "relative_rmse": rel_rmse,
        "max_abs_error": max_abs_error,
        "correlation_magnitude": corr_mag,
        "best_fit_gain_real": float(np.real(gain)),
        "best_fit_gain_imag": float(np.imag(gain)),
        "gain_aligned_relative_rmse": gain_aligned_rel_rmse,
    }


def write_compare_plots(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    out_prefix: str | Path,
    *,
    sample_rate_hz: float,
    title: str,
    drop_first_samples: int = 100,
    xcorr_window_samples: int = 131072,
) -> dict[str, str]:
    out_prefix = Path(out_prefix)
    prepared = prepare_compare_inputs(
        python_samples,
        matlab_samples,
        drop_first_samples=drop_first_samples,
        xcorr_window_samples=xcorr_window_samples,
    )
    python_aligned = prepared["python_aligned"]
    matlab_aligned = prepared["matlab_aligned"]
    sample_count = min(len(python_aligned), len(matlab_aligned))
    python_aligned = python_aligned[:sample_count]
    matlab_aligned = matlab_aligned[:sample_count]
    diff = python_aligned - matlab_aligned

    time_path = Path(f"{out_prefix}_compare_time.png")
    psd_path = Path(f"{out_prefix}_compare_psd.png")
    spectrogram_path = Path(f"{out_prefix}_compare_spectrogram.png")

    plot_compare_time(python_aligned, matlab_aligned, diff, time_path, sample_rate_hz, title, prepared["xcorr_peak_lag_samples"])
    plot_compare_psd(python_aligned, matlab_aligned, diff, psd_path, sample_rate_hz, title, prepared["xcorr_peak_lag_samples"])
    plot_compare_spectrogram(python_aligned, matlab_aligned, diff, spectrogram_path, sample_rate_hz, title, prepared["xcorr_peak_lag_samples"])
    return {"time": str(time_path), "psd": str(psd_path), "spectrogram": str(spectrogram_path)}


def prepare_compare_inputs(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    *,
    drop_first_samples: int,
    xcorr_window_samples: int,
) -> dict[str, Any]:
    sample_count = min(len(python_samples), len(matlab_samples))
    python_samples = python_samples[:sample_count]
    matlab_samples = matlab_samples[:sample_count]
    if drop_first_samples > 0:
        python_samples = python_samples[drop_first_samples:]
        matlab_samples = matlab_samples[drop_first_samples:]

    xcorr = estimate_cross_correlation(python_samples, matlab_samples, xcorr_window_samples=xcorr_window_samples)
    python_aligned, matlab_aligned = align_by_lag(python_samples, matlab_samples, xcorr["peak_lag_samples"])
    return {
        "python_aligned": python_aligned,
        "matlab_aligned": matlab_aligned,
        "xcorr_peak_lag_samples": xcorr["peak_lag_samples"],
        "xcorr_peak_magnitude": xcorr["peak_magnitude"],
        "xcorr_peak_phase_rad": xcorr["peak_phase_rad"],
        "xcorr_window_samples": xcorr["window_samples"],
    }


def estimate_cross_correlation(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    *,
    xcorr_window_samples: int,
) -> dict[str, Any]:
    sample_count = min(len(python_samples), len(matlab_samples), xcorr_window_samples)
    if sample_count == 0:
        return {"peak_lag_samples": 0, "peak_magnitude": 0.0, "peak_phase_rad": 0.0, "window_samples": 0}

    python_view = python_samples[:sample_count]
    matlab_view = matlab_samples[:sample_count]
    py_norm = float(np.linalg.norm(python_view))
    ml_norm = float(np.linalg.norm(matlab_view))
    if py_norm == 0.0 or ml_norm == 0.0:
        return {"peak_lag_samples": 0, "peak_magnitude": 0.0, "peak_phase_rad": 0.0, "window_samples": sample_count}

    corr = scipy_signal.correlate(python_view, matlab_view, mode="full", method="fft")
    lags = scipy_signal.correlation_lags(len(python_view), len(matlab_view), mode="full")
    peak_index = int(np.argmax(np.abs(corr)))
    peak_value = corr[peak_index]
    peak_lag = int(lags[peak_index])
    peak_mag = float(np.abs(peak_value) / (py_norm * ml_norm))
    peak_phase = float(np.angle(peak_value))
    return {
        "peak_lag_samples": peak_lag,
        "peak_magnitude": peak_mag,
        "peak_phase_rad": peak_phase,
        "window_samples": sample_count,
    }


def align_by_lag(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    lag_samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    if lag_samples > 0:
        python_samples = python_samples[lag_samples:]
        matlab_samples = matlab_samples[: len(python_samples)]
    elif lag_samples < 0:
        matlab_samples = matlab_samples[-lag_samples:]
        python_samples = python_samples[: len(matlab_samples)]
    sample_count = min(len(python_samples), len(matlab_samples))
    return python_samples[:sample_count], matlab_samples[:sample_count]


def plot_compare_time(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    diff: np.ndarray,
    out_path: Path,
    sample_rate_hz: float,
    title: str,
    lag_samples: int,
) -> None:
    view_ms = min(2.0, 1000.0 * len(python_samples) / sample_rate_hz)
    sample_count = max(1, int(round(view_ms * 1e-3 * sample_rate_hz)))
    t_ms = np.arange(sample_count) / sample_rate_hz * 1e3

    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    axes[0].plot(t_ms, np.real(python_samples[:sample_count]), label="Python real", linewidth=0.9)
    axes[0].plot(t_ms, np.real(matlab_samples[:sample_count]), label="MATLAB real", linewidth=0.9, alpha=0.85)
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title(f"{title}: Real overlay (drop 100, aligned lag {lag_samples} samples)")
    axes[0].grid(True, alpha=0.2)
    axes[0].legend(loc="upper right")

    axes[1].plot(t_ms, np.imag(python_samples[:sample_count]), label="Python imag", linewidth=0.9)
    axes[1].plot(t_ms, np.imag(matlab_samples[:sample_count]), label="MATLAB imag", linewidth=0.9, alpha=0.85)
    axes[1].set_ylabel("Amplitude")
    axes[1].set_title(f"{title}: Imag overlay")
    axes[1].grid(True, alpha=0.2)
    axes[1].legend(loc="upper right")

    axes[2].plot(t_ms, np.real(diff[:sample_count]), label="Residual real", linewidth=0.8, color="#d62728")
    axes[2].set_ylabel("Amplitude")
    axes[2].set_title(f"{title}: Real residual")
    axes[2].grid(True, alpha=0.2)
    axes[2].legend(loc="upper right")

    axes[3].plot(t_ms, np.imag(diff[:sample_count]), label="Residual imag", linewidth=0.8, color="#9467bd")
    axes[3].set_xlabel("Time (ms)")
    axes[3].set_ylabel("Amplitude")
    axes[3].set_title(f"{title}: Imag residual")
    axes[3].grid(True, alpha=0.2)
    axes[3].legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_compare_psd(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    diff: np.ndarray,
    out_path: Path,
    sample_rate_hz: float,
    title: str,
    lag_samples: int,
) -> None:
    n = min(len(python_samples), 131072)
    if n == 0:
        raise ValueError("Cannot plot PSD for empty IQ")
    window = np.hanning(n)
    py_spec = np.fft.fftshift(np.fft.fft(python_samples[:n] * window, n=n))
    ml_spec = np.fft.fftshift(np.fft.fft(matlab_samples[:n] * window, n=n))
    diff_spec = np.fft.fftshift(np.fft.fft(diff[:n] * window, n=n))
    py_psd = 20.0 * np.log10(np.maximum(np.abs(py_spec), 1e-12))
    ml_psd = 20.0 * np.log10(np.maximum(np.abs(ml_spec), 1e-12))
    diff_psd = 20.0 * np.log10(np.maximum(np.abs(diff_spec), 1e-12))
    freq_mhz = np.linspace(-sample_rate_hz / 2.0, sample_rate_hz / 2.0, n, endpoint=False) / 1e6

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    axes[0].plot(freq_mhz, py_psd, linewidth=0.8)
    axes[0].set_ylabel("Magnitude (dBFS)")
    axes[0].set_title(f"{title}: Python PSD (aligned lag {lag_samples} samples)")
    axes[0].grid(True, alpha=0.2)

    axes[1].plot(freq_mhz, ml_psd, linewidth=0.8, color="#2ca02c")
    axes[1].set_ylabel("Magnitude (dBFS)")
    axes[1].set_title(f"{title}: MATLAB PSD")
    axes[1].grid(True, alpha=0.2)

    axes[2].plot(freq_mhz, diff_psd, linewidth=0.8, color="#d62728")
    axes[2].set_xlabel("Frequency offset (MHz)")
    axes[2].set_ylabel("Magnitude (dBFS)")
    axes[2].set_title(f"{title}: Residual PSD")
    axes[2].grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_compare_spectrogram(
    python_samples: np.ndarray,
    matlab_samples: np.ndarray,
    diff: np.ndarray,
    out_path: Path,
    sample_rate_hz: float,
    title: str,
    lag_samples: int,
) -> None:
    py_spec, py_time_s, py_freq_hz = compute_spectrogram(python_samples, sample_rate_hz, 0.0)
    ml_spec, ml_time_s, ml_freq_hz = compute_spectrogram(matlab_samples, sample_rate_hz, 0.0)
    diff_spec, diff_time_s, diff_freq_hz = compute_spectrogram(diff, sample_rate_hz, 0.0)

    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    datasets = [
        ("Python spectrogram", py_spec, py_time_s, py_freq_hz, axes[0]),
        ("MATLAB spectrogram", ml_spec, ml_time_s, ml_freq_hz, axes[1]),
        ("Residual spectrogram", diff_spec, diff_time_s, diff_freq_hz, axes[2]),
    ]
    for row_index, (row_title, spec_db, time_s, freq_hz, ax) in enumerate(datasets):
        extent = [time_s[0] * 1e3, time_s[-1] * 1e3, freq_hz[0] / 1e6, freq_hz[-1] / 1e6]
        image = ax.imshow(
            spec_db,
            origin="lower",
            aspect="auto",
            extent=extent,
            cmap="magma",
            vmin=np.percentile(spec_db, 15),
            vmax=np.percentile(spec_db, 99.7),
        )
        ax.set_ylabel("Freq (MHz)")
        ax.set_title(f"{title}: {row_title}" + (" (drop 100, aligned)" if row_index == 0 else ""))
        ax.grid(False)
        fig.colorbar(image, ax=ax, pad=0.01, label="Magnitude (dB)")
    axes[-1].set_xlabel(f"Time (ms), lag {lag_samples} samples")

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
