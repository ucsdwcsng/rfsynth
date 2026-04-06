"""Shared burst builders used by many Python-native atomics.

Most thin wrapper atomics only override `Signal.generate_transmission(...)` and
delegate here. Protocol-specific builders that need more bespoke logic live in
their own modules, such as `bluetooth.py`, `wlan_nonht80211g.py`, and
`nr5g.py`.
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal

from rfsynth.native.core import GeneratedBurst


def scale_to_power(samples: np.ndarray, tx_power_db: float) -> np.ndarray:
    """Normalize a burst to the requested amplitude scale."""

    rms = np.sqrt(np.mean(np.abs(samples) ** 2))
    if not np.isfinite(rms) or rms == 0:
        return samples.astype(np.complex64)
    target = 10.0 ** (float(tx_power_db) / 20.0)
    return (samples / rms * target).astype(np.complex64)


def samples_for_duration(duration_s: float, sample_rate_hz: float) -> int:
    """Convert a duration to a positive integer sample count."""

    return max(1, int(round(duration_s * sample_rate_hz)))


def rrc_taps(beta: float, span: int, sps: int) -> np.ndarray:
    """Build root-raised-cosine taps for pulse-shaped symbol families."""

    n = np.arange(-span * sps / 2, span * sps / 2 + 1, dtype=np.float64)
    taps = np.zeros_like(n)
    for idx, x in enumerate(n):
        t = x / sps
        if abs(t) < 1e-12:
            taps[idx] = 1.0 + beta * (4 / math.pi - 1)
        elif beta > 0 and abs(abs(4 * beta * t) - 1.0) < 1e-12:
            taps[idx] = (
                beta
                / math.sqrt(2)
                * (
                    (1 + 2 / math.pi) * math.sin(math.pi / (4 * beta))
                    + (1 - 2 / math.pi) * math.cos(math.pi / (4 * beta))
                )
            )
        else:
            num = math.sin(math.pi * t * (1 - beta)) + 4 * beta * t * math.cos(math.pi * t * (1 + beta))
            den = math.pi * t * (1 - (4 * beta * t) ** 2)
            taps[idx] = num / den
    taps /= np.sqrt(np.mean(taps**2))
    return taps


def gaussian_taps(bt: float, sps: int, span: int = 4) -> np.ndarray:
    t = np.arange(-span * sps, span * sps + 1, dtype=np.float64) / sps
    alpha = math.sqrt(math.log(2)) / (2 * math.pi * bt)
    taps = np.exp(-(t**2) / (2 * alpha**2))
    taps /= np.sum(taps)
    return taps


def shaped_symbol_stream(symbols: np.ndarray, sps: int, beta: float, span: int) -> np.ndarray:
    up = np.zeros(len(symbols) * sps, dtype=np.complex128)
    up[::sps] = symbols
    taps = rrc_taps(beta, span, sps)
    return np.convolve(up, taps, mode="same")


def qam_constellation(mod_order: int) -> np.ndarray:
    """Return a unit-power square QAM constellation."""

    if mod_order == 2:
        return np.array([-1, 1], dtype=np.complex128)
    side = int(round(math.sqrt(mod_order)))
    if side * side != mod_order:
        raise ValueError(f"QAM modOrder must be square, got {mod_order}")
    axis = np.arange(-(side - 1), side, 2)
    const = np.array([x + 1j * y for y in axis[::-1] for x in axis], dtype=np.complex128)
    const /= np.sqrt(np.mean(np.abs(const) ** 2))
    return const


def psk_symbols(mod_order: int, count: int, rng: np.random.Generator) -> np.ndarray:
    idx = rng.integers(0, mod_order, size=count)
    phase0 = math.pi / mod_order
    return np.exp(1j * (2 * math.pi * idx / mod_order + phase0))


def pam_symbols(mod_order: int, count: int, rng: np.random.Generator) -> np.ndarray:
    idx = rng.integers(0, mod_order, size=count)
    axis = np.arange(-(mod_order - 1), mod_order, 2)
    symbols = axis[idx].astype(np.float64)
    symbols /= np.sqrt(np.mean(symbols**2))
    return symbols.astype(np.complex128)


def qam_symbols(mod_order: int, count: int, rng: np.random.Generator) -> np.ndarray:
    const = qam_constellation(mod_order)
    idx = rng.integers(0, len(const), size=count)
    return const[idx]


def psk_symbols_from_indices(mod_order: int, indices: np.ndarray) -> np.ndarray:
    indices = np.asarray(indices, dtype=np.int64).reshape(-1)
    phase0 = math.pi / mod_order
    return np.exp(1j * (2 * math.pi * indices / mod_order + phase0)).astype(np.complex128)


def pam_symbols_from_indices(mod_order: int, indices: np.ndarray) -> np.ndarray:
    indices = np.asarray(indices, dtype=np.int64).reshape(-1)
    axis = np.arange(-(mod_order - 1), mod_order, 2)
    symbols = axis[indices].astype(np.float64)
    symbols /= np.sqrt(np.mean(symbols**2))
    return symbols.astype(np.complex128)


def qam_symbols_from_indices(mod_order: int, indices: np.ndarray) -> np.ndarray:
    const = qam_constellation(mod_order)
    indices = np.asarray(indices, dtype=np.int64).reshape(-1)
    return const[indices]


def load_test_vector_payload(args: dict[str, Any]) -> dict[str, Any] | None:
    """Load optional compare/test payload overrides from `testVectorPath`."""

    path = args.get("testVectorPath")
    if not path:
        return None
    raw = json.loads(Path(path).read_text())
    payload = raw.get("payload", {})
    out: dict[str, Any] = {}
    if "symbols_real" in payload:
        out["symbols"] = np.asarray(payload["symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["symbols_imag"], dtype=np.float64)
    if "data_symbols_real" in payload:
        out["data_symbols"] = np.asarray(payload["data_symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["data_symbols_imag"], dtype=np.float64)
    if "pilot_symbols_real" in payload:
        out["pilot_symbols"] = np.asarray(payload["pilot_symbols_real"], dtype=np.float64) + 1j * np.asarray(payload["pilot_symbols_imag"], dtype=np.float64)
    if "samples_real" in payload:
        out["samples"] = np.asarray(payload["samples_real"], dtype=np.float64) + 1j * np.asarray(payload["samples_imag"], dtype=np.float64)
    if "message_real" in payload:
        out["message"] = np.asarray(payload["message_real"], dtype=np.float64) + 1j * np.asarray(payload["message_imag"], dtype=np.float64)
    for key in (
        "symbol_indices",
        "bits",
        "message_bits",
        "access_address_bits",
        "hop_centers_hz",
        "spread_code",
        "scrambler_initialization",
    ):
        if key in payload:
            out[key] = np.asarray(payload[key])
    return out


def matlab_like_ofdm_params(n_sc: int) -> dict[str, Any]:
    """Return the OFDM indexing/pilot layout used by compare helpers."""

    cp_len = 16
    num_filled = round(n_sc * 52 / 64)
    num_filled += num_filled % 2
    num_pilots = round(num_filled / 13)
    num_pilots += num_pilots % 2

    filled = np.concatenate(
        [
            np.arange(2, num_filled // 2 + 2),
            np.arange(n_sc - num_filled // 2 + 1, n_sc + 1),
        ]
    )
    left_cut = np.linspace(2, num_filled / 2 + 1, num_pilots // 2 + 1)
    right_cut = np.linspace(n_sc - num_filled / 2 + 1, n_sc, num_pilots // 2 + 1)
    left_mean = np.round((left_cut[:-1] + left_cut[1:]) / 2).astype(int)
    right_mean = np.round((right_cut[:-1] + right_cut[1:]) / 2).astype(int)
    pilot_idx_1b = np.concatenate([left_mean, right_mean])
    data_idx_1b = np.array(sorted(set(filled.tolist()) - set(pilot_idx_1b.tolist())), dtype=int)

    pilot_screw = np.array(
        [
            1,1,1,1,-1,-1,-1,1,-1,-1,-1,-1,1,1,-1,1,-1,-1,1,1,-1,1,1,-1,1,1,1,1,1,1,-1,1,1,1,-1,1,1,-1,-1,1,1,1,-1,1,-1,-1,-1,1,-1,1,-1,-1,1,-1,-1,1,1,1,1,1,-1,-1,1,1,-1,-1,1,-1,1,-1,1,1,-1,-1,-1,1,1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,1,1,-1,1,-1,1,1,-1,-1,1,1,-1,1,-1,-1,1,1,-1,-1,-1,-1,-1,-1,-1
        ],
        dtype=np.float64,
    )
    pilots = pilot_screw[:num_pilots].astype(np.complex128)

    if n_sc == 64:
        lts_f = np.array(
            [0, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1],
            dtype=np.complex128,
        )
    elif n_sc == 256:
        lts_256 = np.array(
            [-1,-1,-1,1,-1,-1,-1,-1,-1,1,1,-1,1,-1,1,-1,-1,1,-1,-1,-1,1,-1,-1,-1,-1,1,-1,1,-1,-1,1,1,1,-1,1,-1,1,1,1,1,1,1,-1,-1,-1,1,1,-1,-1,-1,-1,1,-1,1,1,1,1,-1,-1,-1,-1,-1,1,-1,-1,-1,1,1,-1,-1,1,-1,1,-1,1,1,1,1,-1,1,-1,-1,-1,1,-1,1,-1,1,-1,1,-1,-1,1,1,-1,1,-1,1,-1,1,-1,1,1,-1,1,1,-1,-1,-1,-1,1,-1,1,-1,1,-1,-1,1,-1,-1,-1,1,-1,-1,1,-1,1,1,-1,-1,1,1,1,-1,-1,1,-1,1,-1,1,1,-1,1,1,-1,1,-1,-1,1,1,1,-1,1,-1,1,1,-1,-1,-1,-1,-1,1,1,1,1,1,-1,1,-1,-1,-1,-1,-1,-1,-1,-1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,1,-1,-1,-1,1,1,-1,-1,1,1,-1,1,-1,1,-1,-1,-1,-1,1,-1,-1,-1,-1,1,1,1,1,1,-1,1,-1,-1,-1,1,1,1,1,-1,1,-1,-1,-1,1,1,1,1,1,-1,-1,-1,-1,1,1,1,-1,-1,-1,1,-1,1,1,-1,1],
            dtype=np.complex128,
        )
        lts_f = np.zeros(n_sc, dtype=np.complex128)
        lts_f[filled - 1] = lts_256[:num_filled]
    else:
        raise ValueError(f"Atomic OFDM compare currently supports Nfft 64 or 256, not {n_sc}")

    lts_t = np.fft.ifft(lts_f)
    return {
        "n_sc": n_sc,
        "cp_len": cp_len,
        "filled_idx": filled - 1,
        "pilot_idx": pilot_idx_1b - 1,
        "data_idx": data_idx_1b - 1,
        "pilots": pilots,
        "lts_t": lts_t.astype(np.complex128),
    }


def am_burst(args: dict[str, Any]) -> GeneratedBurst:
    """Generate the AM burst used by `AmSignal.generate_transmission(...)`."""

    fs = float(args.get("transmissionRate_Hz", 500e3))
    duration = float(args.get("transmissionTotTime", 0.004))
    n = samples_for_duration(duration, fs)
    t = np.arange(n, dtype=np.float64) / fs
    msg = np.sin(2 * math.pi * float(args.get("messageFreq_Hz", 5e3)) * t)
    envelope = 1.0 + float(args.get("modulationIndex", 0.8)) * msg
    return GeneratedBurst(
        samples=scale_to_power(envelope.astype(np.complex128), float(args.get("txPower_db", -70))),
        sample_rate_hz=fs,
        bandwidth_hz=float(args.get("bandwidth_Hz", 100e3)),
        protocol="unknown",
        modality="single_carrier",
        modulation="am",
    )


def fm_burst(args: dict[str, Any]) -> GeneratedBurst:
    """Generate the FM burst used by `FmSignal.generate_transmission(...)`."""

    fs = float(args.get("transmissionRate_Hz", 500e3))
    duration = float(args.get("transmissionTotTime", 0.004))
    n = samples_for_duration(duration, fs)
    t = np.arange(n, dtype=np.float64) / fs
    msg = np.sin(2 * math.pi * float(args.get("messageFreq_Hz", 5e3)) * t)
    phase = 2 * math.pi * float(args.get("freqDeviation_Hz", 20e3)) * np.cumsum(msg) / fs
    burst = np.exp(1j * phase)
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=fs,
        bandwidth_hz=float(args.get("bandwidth_Hz", 100e3)),
        protocol="unknown",
        modality="single_carrier",
        modulation="fm",
    )


def ssb_burst(args: dict[str, Any]) -> GeneratedBurst:
    """Generate the SSB burst used by `SsbSignal.generate_transmission(...)`."""

    fs = float(args.get("transmissionRate_Hz", 500e3))
    duration = float(args.get("transmissionTotTime", 0.004))
    n = samples_for_duration(duration, fs)
    t = np.arange(n, dtype=np.float64) / fs
    base = np.sin(2 * math.pi * float(args.get("messageFreq_Hz", 5e3)) * t)
    base += 0.5 * np.sin(4 * math.pi * float(args.get("messageFreq_Hz", 5e3)) * t)
    burst = signal.hilbert(base)
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=fs,
        bandwidth_hz=float(args.get("bandwidth_Hz", 50e3)),
        protocol="unknown",
        modality="single_carrier",
        modulation="ssb",
    )


def sine_burst(args: dict[str, Any]) -> GeneratedBurst:
    """Generate the tone burst used by `SineSignal.generate_transmission(...)`."""

    fs = float(args.get("transmissionRate_Hz", 1e6))
    duration = float(args.get("transmissionTotTime", 0.004))
    n = samples_for_duration(duration, fs)
    tone = float(args.get("toneOffset_Hz", 100e3))
    burst = np.exp(2j * math.pi * tone / fs * np.arange(n, dtype=np.float64))
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=fs,
        bandwidth_hz=float(args.get("bandwidth_Hz", 200e3)),
        protocol="unknown",
        modality="single_carrier",
        modulation="no_answer",
    )


def noise_burst(args: dict[str, Any], *, total_time_s: float, rx_sample_rate_hz: float, rng: np.random.Generator) -> GeneratedBurst:
    """Generate wideband noise for `WidebandThermalWgnSignal`."""

    fs = float(args.get("bandwidth_Hz", rx_sample_rate_hz))
    vector = load_test_vector_payload(args)
    if vector and "samples" in vector:
        burst = np.asarray(vector["samples"], dtype=np.complex128).reshape(-1)
    else:
        n = samples_for_duration(total_time_s, fs)
        burst = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    return GeneratedBurst(
        samples=0.02 * burst.astype(np.complex64),
        sample_rate_hz=fs,
        bandwidth_hz=float(args.get("bandwidth_Hz", fs)),
        protocol="unknown",
        modality="unknown",
        modulation="unknown",
    )


def pam_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate a pulse-shaped PAM burst for `PamSignal`."""

    symbol_rate = float(args.get("transmissionRate_Hz", 1e6))
    sps = int(args.get("samplesPerSymbol", 8))
    beta = float(args.get("beta", 0.35))
    span = int(args.get("span", 10))
    mod_order = int(args.get("modOrder", 4))
    vector = load_test_vector_payload(args)
    if vector and "symbols" in vector:
        symbols = np.asarray(vector["symbols"], dtype=np.complex128).reshape(-1)
    elif vector and "symbol_indices" in vector:
        symbols = pam_symbols_from_indices(mod_order, vector["symbol_indices"])
    else:
        n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
        symbols = pam_symbols(mod_order, n_sym, rng)
    burst = shaped_symbol_stream(symbols, sps, beta, span)
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=symbol_rate * sps,
        bandwidth_hz=float(args.get("bandwidth_Hz", symbol_rate * (1 + beta))),
        protocol="unknown",
        modality="single_carrier",
        modulation="pam",
    )


def psk_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate a pulse-shaped PSK burst for `PskSignal`."""

    symbol_rate = float(args.get("transmissionRate_Hz", 1e6))
    sps = int(args.get("samplesPerSymbol", 8))
    beta = float(args.get("beta", 0.35))
    span = int(args.get("span", 10))
    mod_order = int(args.get("modOrder", 4))
    vector = load_test_vector_payload(args)
    if vector and "symbols" in vector:
        symbols = np.asarray(vector["symbols"], dtype=np.complex128).reshape(-1)
    elif vector and "symbol_indices" in vector:
        symbols = psk_symbols_from_indices(mod_order, vector["symbol_indices"])
    else:
        n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
        symbols = psk_symbols(mod_order, n_sym, rng)
    burst = shaped_symbol_stream(symbols, sps, beta, span)
    modulation = {2: "bpsk", 4: "qpsk", 8: "psk8", 16: "psk16", 32: "psk32"}.get(mod_order, "psk")
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=symbol_rate * sps,
        bandwidth_hz=symbol_rate * (1 + beta),
        protocol="unknown",
        modality="single_carrier",
        modulation=modulation,
    )


def qam_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate a pulse-shaped QAM burst for `QamSignal`."""

    symbol_rate = float(args.get("transmissionRate_Hz", 1e6))
    sps = int(args.get("samplesPerSymbol", 8))
    beta = float(args.get("beta", 0.35))
    span = int(args.get("span", 10))
    mod_order = int(args.get("modOrder", 16))
    vector = load_test_vector_payload(args)
    if vector and "symbols" in vector:
        symbols = np.asarray(vector["symbols"], dtype=np.complex128).reshape(-1)
    elif vector and "symbol_indices" in vector:
        symbols = qam_symbols_from_indices(mod_order, vector["symbol_indices"])
    else:
        n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
        symbols = qam_symbols(mod_order, n_sym, rng)
    burst = shaped_symbol_stream(symbols, sps, beta, span)
    modulation = {
        2: "bpsk",
        4: "qpsk",
        8: "qam8",
        16: "qam16",
        32: "qam32",
        64: "qam64",
        128: "qam128",
        256: "qam256",
        1024: "qam1024",
    }.get(mod_order, "qam")
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=symbol_rate * sps,
        bandwidth_hz=symbol_rate * (1 + beta),
        protocol="unknown",
        modality="single_carrier",
        modulation=modulation,
    )


def fsk_like_burst(
    args: dict[str, Any],
    rng: np.random.Generator,
    *,
    continuous: bool,
    gaussian_bt: float | None = None,
    modulation_index: float | None = None,
    bandwidth_hz: float,
    modulation: str,
) -> GeneratedBurst:
    """Shared FSK-family implementation for FSK/CPFSK/GFSK/GMSK/MSK wrappers."""

    symbol_rate = float(args.get("transmissionRate_Hz", 250e3))
    sps = int(args.get("samplesPerSymbol", 8))
    mod_order = int(args.get("modOrder", 2))
    vector = load_test_vector_payload(args)
    if vector and "symbol_indices" in vector:
        levels = np.asarray(vector["symbol_indices"], dtype=np.float64).reshape(-1)
    elif vector and "bits" in vector:
        levels = np.asarray(vector["bits"], dtype=np.float64).reshape(-1)
    else:
        n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
        levels = rng.integers(0, mod_order, size=n_sym).astype(np.float64)
    centered = levels - np.mean(np.arange(mod_order, dtype=np.float64))
    symbols = np.repeat(centered, sps)
    if gaussian_bt is not None:
        taps = gaussian_taps(gaussian_bt, sps)
        symbols = np.convolve(symbols, taps, mode="same")
    elif continuous and modulation_index is not None:
        taps = np.ones(sps, dtype=np.float64) / sps
        symbols = np.convolve(symbols, taps, mode="same")
    sample_rate_hz = symbol_rate * sps
    if modulation_index is None:
        freq_sep = float(args.get("freqDev", 0.25)) * sample_rate_hz / max(mod_order - 1, 1)
        inst_freq = symbols * freq_sep
    else:
        inst_freq = symbols * (modulation_index * symbol_rate / 2.0)
    if not continuous and gaussian_bt is None:
        phase = np.concatenate([[0.0], 2 * math.pi * np.cumsum(inst_freq[:-1]) / sample_rate_hz])
    else:
        phase = 2 * math.pi * np.cumsum(inst_freq) / sample_rate_hz
    burst = np.exp(1j * phase)
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=sample_rate_hz,
        bandwidth_hz=bandwidth_hz,
        protocol="unknown",
        modality="single_carrier",
        modulation=modulation,
    )


def random_symbol_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate a repeated random-symbol burst for `RandomSymbolSignal`."""

    symbol_rate = float(args.get("transmissionRate_Hz", 1e6))
    sps = int(args.get("samplesPerSymbol", 4))
    mod_order = int(args.get("modOrder", 4))
    vector = load_test_vector_payload(args)
    if vector and "symbols" in vector:
        symbols = np.asarray(vector["symbols"], dtype=np.complex128).reshape(-1)
    else:
        if vector and "symbol_indices" in vector:
            idx = np.asarray(vector["symbol_indices"], dtype=np.int64).reshape(-1)
        else:
            n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.004)) * symbol_rate)))
            idx = rng.integers(0, mod_order, size=n_sym)
        symbols = np.exp(2j * math.pi * idx / mod_order)
    burst = np.repeat(symbols, sps)
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=symbol_rate * sps,
        bandwidth_hz=float(args.get("bandwidth_Hz", 1e6)),
        protocol="unknown",
        modality="single_carrier",
        modulation="unknown",
    )


def ofdm_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate the generic OFDM burst used by `OfdmSignal`."""

    nfft = int(args.get("Nfft", 256))
    sample_rate = float(args.get("transmissionRate_Hz", 10e6))
    cp_len = int(round(float(args.get("cpTime_s", 16 / sample_rate)) * sample_rate))
    symbol_time_s = float(args.get("symbolTime_s", nfft / sample_rate))
    if not math.isclose(symbol_time_s, nfft / sample_rate, rel_tol=1e-6, abs_tol=1e-12):
        raise ValueError("symbolTime_s does not match Nfft/transmissionRate_Hz")
    if not math.isclose(float(args.get("cpTime_s", cp_len / sample_rate)), cp_len / sample_rate, rel_tol=1e-6, abs_tol=1e-12):
        raise ValueError("cpTime_s does not match derived CP time")
    num_filled = round(nfft * 52 / 64)
    num_filled += num_filled % 2
    filled = np.concatenate([np.arange(1, num_filled // 2 + 1), np.arange(nfft - num_filled // 2, nfft)])
    mod_order = int(args.get("modOrder", 4))
    duration = float(args.get("transmissionTotTime", 0.004))
    n_syms = max(1, int(math.floor((duration * sample_rate) / (nfft + cp_len))))
    constellation = qam_constellation(mod_order if mod_order > 2 else 4)
    vector = load_test_vector_payload(args)
    pilots = np.ones(len(filled), dtype=np.complex128)
    lts_freq = np.zeros(nfft, dtype=np.complex128)
    lts_freq[filled] = pilots
    lts_time = np.fft.ifft(lts_freq)
    preamble = np.concatenate([lts_time[nfft // 2 :], lts_time, lts_time])
    if vector and "data_symbols" in vector:
        data_symbols = np.asarray(vector["data_symbols"], dtype=np.complex128)
        pilot_symbols = np.asarray(vector.get("pilot_symbols", np.ones((0, data_symbols.shape[1]), dtype=np.complex128)), dtype=np.complex128)
        symbols = []
        pilot_idx = np.array([], dtype=np.int64)
        data_idx = filled
        if nfft in {64, 256}:
            params = matlab_like_ofdm_params(nfft)
            pilot_idx = params["pilot_idx"]
            data_idx = params["data_idx"]
        for sym_idx in range(data_symbols.shape[1]):
            freq_bins = np.zeros(nfft, dtype=np.complex128)
            freq_bins[data_idx] = data_symbols[:, sym_idx]
            if pilot_symbols.size and pilot_idx.size:
                freq_bins[pilot_idx] = pilot_symbols[:, sym_idx]
            time = np.fft.ifft(freq_bins)
            symbols.append(np.concatenate([time[-cp_len:], time]))
    else:
        symbols = []
        for _ in range(n_syms):
            freq_bins = np.zeros(nfft, dtype=np.complex128)
            idx = rng.integers(0, len(constellation), size=len(filled))
            freq_bins[filled] = constellation[idx]
            time = np.fft.ifft(freq_bins)
            with_cp = np.concatenate([time[-cp_len:], time])
            symbols.append(with_cp)
    burst = np.concatenate([preamble, *symbols]).astype(np.complex128)
    bandwidth_hz = float(args.get("bandwidth_Hz", ((len(filled) + 1) / nfft) * sample_rate))
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=sample_rate,
        bandwidth_hz=bandwidth_hz,
        protocol="unknown",
        modality="multi_carrier",
        modulation="ofdm",
        extras={
            "Nfft": nfft,
            "ofdm_params": {
                "N_SC": nfft,
                "CP_LEN": cp_len,
                "N_OFDM_SYMS": n_syms,
                "MOD_ORDER": mod_order,
                "SYMBOL_TIME_S": nfft / sample_rate,
                "CP_TIME_S": cp_len / sample_rate,
                "TOTAL_SYMBOL_TIME_S": (nfft + cp_len) / sample_rate,
                "FILLED_SC_IND": (filled + 1).tolist(),
            },
        },
    )


def bluetooth_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Legacy simplified Bluetooth helper kept for compare-oriented callers."""

    clone = dict(args)
    clone.setdefault("transmissionRate_Hz", 1e6)
    clone.setdefault("samplesPerSymbol", 8)
    clone.setdefault("bandwidthTimeProduct", 0.35)
    clone.setdefault("bandwidth_Hz", 1.255e6)
    clone.setdefault("transmissionTotTime", 680e-6)
    clone.setdefault("txPower_db", -79)
    burst = fsk_like_burst(
        clone,
        rng,
        continuous=True,
        gaussian_bt=float(clone.get("bandwidthTimeProduct", 0.35)),
        modulation_index=0.5,
        bandwidth_hz=float(clone.get("bandwidth_Hz", 1.255e6)),
        modulation="gmsk",
    )
    return GeneratedBurst(
        samples=burst.samples,
        sample_rate_hz=1e6 * float(clone.get("samplesPerSymbol", 8)),
        bandwidth_hz=float(clone.get("bandwidth_Hz", 1.255e6)),
        protocol="unknown",
        modality="single_carrier",
        modulation="gmsk",
        extras=burst.extras,
    )


def wlan_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Legacy simplified WLAN helper kept for compare-oriented callers."""

    clone = dict(args)
    clone.setdefault("transmissionRate_Hz", 20e6)
    clone.setdefault("Nfft", 64)
    clone.setdefault("modOrder", 4)
    clone.setdefault("cpTime_s", 16 / 20e6)
    clone.setdefault("symbolTime_s", 64 / 20e6)
    clone.setdefault("transmissionTotTime", 112e-6)
    clone.setdefault("txPower_db", -74)
    clone.setdefault("bandwidth_Hz", 16.8e6)
    burst = ofdm_burst(clone, rng)
    burst.bandwidth_hz = 16.8e6
    burst.modulation = "wlan_non_ht_802_11_g"
    return burst


def ds3_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate the spread-spectrum DS3 burst used by `Ds3Signal`."""

    chips_per_symbol = int(args.get("chipsPerSymbol", 64))
    mod_order = int(args.get("modOrder", 2))
    bandwidth_hz = float(args["bandwidth_Hz"])
    samples_per_chip = int(args.get("samplesPerChip", 2))
    symbol_rate = bandwidth_hz / (2.0 * chips_per_symbol)
    n_sym = max(1, int(round(float(args.get("transmissionTotTime", 0.001)) * symbol_rate)))
    vector = load_test_vector_payload(args)
    if vector and "spread_code" in vector:
        spread_code = np.asarray(vector["spread_code"], dtype=np.float64)
    else:
        spread_code = rng.choice([-1.0, 1.0], size=chips_per_symbol)
    if vector and "symbols" in vector:
        syms = np.asarray(vector["symbols"], dtype=np.complex128).reshape(-1)
    elif vector and "symbol_indices" in vector:
        syms = psk_symbols_from_indices(mod_order, vector["symbol_indices"])
    else:
        syms = rng.choice([-1.0, 1.0], size=n_sym) if mod_order == 2 else psk_symbols(mod_order, n_sym, rng)
    if spread_code.ndim == 1:
        chips = np.kron(syms, spread_code)
    else:
        chips = syms.reshape(1, -1) * spread_code[:, : syms.size]
        chips = chips.T.reshape(-1)
    burst = np.repeat(chips, samples_per_chip).astype(np.complex128)
    modulation = "bpsk" if mod_order == 2 else "qpsk"
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -80))),
        sample_rate_hz=symbol_rate * chips_per_symbol * samples_per_chip,
        bandwidth_hz=bandwidth_hz,
        protocol="unknown",
        modality="direct_sequence",
        modulation=modulation,
    )


def freq_hopping_burst(args: dict[str, Any], rng: np.random.Generator) -> GeneratedBurst:
    """Generate the hopping burst used by `FreqHoppingSignal`."""

    fs = float(args.get("transmissionRate_Hz", 10e6))
    total_time = float(args.get("transmissionTotTime", 0.004))
    total_samples = samples_for_duration(total_time, fs)
    n_hops = int(args.get("nHops", 5))
    bw_total = float(args.get("bandwidth_Hz", 10e6))
    bw_hop = float(args.get("bandwidthPerHop_Hz", 500e3))
    guard_samples = samples_for_duration(float(args.get("guardTime_s", 50e-6)), fs)
    payload_samples = max(1, total_samples - guard_samples * max(n_hops - 1, 0))
    hop_samples = max(1, payload_samples // n_hops)
    vector = load_test_vector_payload(args)
    if vector and "hop_centers_hz" in vector:
        centers = np.asarray(vector["hop_centers_hz"], dtype=np.float64).reshape(-1)
    else:
        centers = np.linspace(-bw_total / 2 + bw_hop / 2, bw_total / 2 - bw_hop / 2, n_hops)
        rng.shuffle(centers)
    chunks = []
    for hop_center in centers:
        n = np.arange(hop_samples, dtype=np.float64)
        chunks.append(np.exp(2j * math.pi * hop_center / fs * n))
    burst = chunks[0]
    for chunk in chunks[1:]:
        burst = np.concatenate([burst, np.zeros(guard_samples, dtype=np.complex128), chunk])
    if len(burst) < total_samples:
        burst = np.pad(burst, (0, total_samples - len(burst)))
    else:
        burst = burst[:total_samples]
    return GeneratedBurst(
        samples=scale_to_power(burst, float(args.get("txPower_db", -70))),
        sample_rate_hz=fs,
        bandwidth_hz=bw_total,
        protocol="unknown",
        modality="frequency_agile",
        modulation="fh",
    )


def dummy_burst(args: dict[str, Any]) -> GeneratedBurst:
    """Generate a zero-valued placeholder burst for `DummySignal`."""

    bw = float(args.get("bandwidth_Hz", 1e6))
    duration = float(args.get("transmissionTotTime", 0.004))
    n = samples_for_duration(duration, bw)
    return GeneratedBurst(
        samples=np.zeros(n, dtype=np.complex64),
        sample_rate_hz=bw,
        bandwidth_hz=bw,
        protocol="unknown",
        modality="unknown",
        modulation="unknown",
    )
