from __future__ import annotations

import math
from typing import Any

import numpy as np

from rfsynth.native.atomic.common import load_test_vector_payload, scale_to_power
from rfsynth.native.core import GeneratedBurst, Scene, Signal


FFT_LEN = 64
CP_LEN = 16
SAMPLE_RATE_HZ = 20e6

NONHT_MCS_TABLE: dict[int, dict[str, Any]] = {
    0: {"nbpsc": 1, "ncbps": 48, "ndbps": 24, "rate_bits": np.array([1, 1, 0, 1], dtype=np.int8), "puncture": np.array([1, 1], dtype=np.int8)},
    1: {"nbpsc": 1, "ncbps": 48, "ndbps": 36, "rate_bits": np.array([1, 1, 1, 1], dtype=np.int8), "puncture": np.array([1, 1, 1, 0, 0, 1], dtype=np.int8)},
    2: {"nbpsc": 2, "ncbps": 96, "ndbps": 48, "rate_bits": np.array([0, 1, 0, 1], dtype=np.int8), "puncture": np.array([1, 1], dtype=np.int8)},
    3: {"nbpsc": 2, "ncbps": 96, "ndbps": 72, "rate_bits": np.array([0, 1, 1, 1], dtype=np.int8), "puncture": np.array([1, 1, 1, 0, 0, 1], dtype=np.int8)},
    4: {"nbpsc": 4, "ncbps": 192, "ndbps": 96, "rate_bits": np.array([1, 0, 0, 1], dtype=np.int8), "puncture": np.array([1, 1], dtype=np.int8)},
    5: {"nbpsc": 4, "ncbps": 192, "ndbps": 144, "rate_bits": np.array([1, 0, 1, 1], dtype=np.int8), "puncture": np.array([1, 1, 1, 0, 0, 1], dtype=np.int8)},
    6: {"nbpsc": 6, "ncbps": 288, "ndbps": 192, "rate_bits": np.array([0, 0, 0, 1], dtype=np.int8), "puncture": np.array([1, 1, 1, 0], dtype=np.int8)},
    7: {"nbpsc": 6, "ncbps": 288, "ndbps": 216, "rate_bits": np.array([0, 0, 1, 1], dtype=np.int8), "puncture": np.array([1, 1, 1, 0, 0, 1], dtype=np.int8)},
}

PILOT_SUBCARRIERS = np.array([-21, -7, 7, 21], dtype=np.int64)
DATA_SUBCARRIERS = np.array(
    [
        -26, -25, -24, -23, -22,
        -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10, -9, -8,
        -6, -5, -4, -3, -2, -1,
        1, 2, 3, 4, 5, 6,
        8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        22, 23, 24, 25, 26,
    ],
    dtype=np.int64,
)

PILOT_POLARITY = np.array(
    [
        1,1,1,1,-1,-1,-1,1,-1,-1,-1,-1,1,1,-1,1,-1,-1,1,1,-1,1,1,-1,1,1,1,1,1,1,-1,1,
        1,1,-1,1,1,-1,-1,1,1,1,-1,1,-1,-1,-1,1,-1,1,-1,-1,1,-1,-1,1,1,1,1,1,-1,-1,1,1,
        -1,-1,1,-1,1,-1,1,1,-1,-1,-1,1,1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,1,1,-1,1,-1,1,1,-1,
        -1,1,1,-1,1,-1,-1,1,1,-1,-1,-1,-1,-1,-1,-1,1,-1,1,-1,1,1,1,-1,-1,1,-1,-1,-1,1,1,1,-1
    ],
    dtype=np.int8,
)


def _subcarrier_to_bin(subcarrier: int) -> int:
    return subcarrier % FFT_LEN


def _bit_array(value: Any, *, fallback_length: int, rng: np.random.Generator) -> np.ndarray:
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        return rng.integers(0, 2, size=fallback_length, dtype=np.int8)
    bits = np.asarray(value, dtype=np.int8).reshape(-1)
    return np.bitwise_and(bits, 1).astype(np.int8)


def _default_psdu_bit_count(args: dict[str, Any]) -> int:
    if "psduLength" in args:
        return int(args["psduLength"]) * 8
    mcs = _resolve_mcs(args)
    n_dbps = int(NONHT_MCS_TABLE[mcs]["ndbps"])
    duration_s = float(args.get("transmissionTotTime", 112e-6))
    nsym = max(1, int(round((duration_s * SAMPLE_RATE_HZ - 400) / 80)))
    usable_bits = max(8, nsym * n_dbps - 22)
    return int(8 * max(1, usable_bits // 8))


def _resolve_mcs(args: dict[str, Any]) -> int:
    if "mcs" in args:
        mcs = int(args["mcs"])
    elif "MCS" in args:
        mcs = int(args["MCS"])
    else:
        mcs = 0
    if mcs not in NONHT_MCS_TABLE:
        raise ValueError(f"Unsupported WLAN Non-HT MCS {mcs}; expected 0..7")
    return mcs


def _scramble(bits: np.ndarray, scrambler_initialization: int) -> np.ndarray:
    state = np.array([(scrambler_initialization >> (6 - i)) & 1 for i in range(7)], dtype=np.int8)
    if not np.any(state):
        state[-1] = 1
    out = np.zeros(bits.size, dtype=np.int8)
    for idx, bit in enumerate(bits.astype(np.int8)):
        feedback = state[0] ^ state[3]
        out[idx] = bit ^ feedback
        state[:-1] = state[1:]
        state[-1] = feedback
    return out


def _conv_encode(bits: np.ndarray) -> np.ndarray:
    g0 = np.array([1, 0, 1, 1, 0, 1, 1], dtype=np.int8)
    g1 = np.array([1, 1, 1, 1, 0, 0, 1], dtype=np.int8)
    reg = np.zeros(7, dtype=np.int8)
    out = np.zeros(bits.size * 2, dtype=np.int8)
    for idx, bit in enumerate(bits.astype(np.int8)):
        reg[1:] = reg[:-1]
        reg[0] = bit
        out[2 * idx] = int(np.sum(reg * g0) & 1)
        out[2 * idx + 1] = int(np.sum(reg * g1) & 1)
    return out


def _interleave(bits: np.ndarray, *, n_cbps: int, n_bpsc: int) -> np.ndarray:
    s = max(n_bpsc // 2, 1)
    k = np.arange(n_cbps)
    i = (n_cbps // 16) * (k % 16) + (k // 16)
    j = s * (i // s) + ((i + n_cbps - ((16 * i) // n_cbps)) % s)
    out = np.zeros(n_cbps, dtype=np.int8)
    out[j] = bits[k]
    return out


def _bpsk_map(bits: np.ndarray) -> np.ndarray:
    return (-1.0 + 2.0 * bits.astype(np.float64)).astype(np.complex128)


def _modulate_data_bits(bits: np.ndarray, n_bpsc: int) -> np.ndarray:
    bit_sign = (-1.0 + 2.0 * bits.astype(np.float64))
    if n_bpsc == 1:
        return bit_sign.astype(np.complex128)
    if n_bpsc == 2:
        i = bit_sign[0::2]
        q = bit_sign[1::2]
        return ((i + 1j * q) / math.sqrt(2.0)).astype(np.complex128)
    if n_bpsc == 4:
        b0 = bit_sign[0::4]
        b1 = bit_sign[1::4]
        b2 = bit_sign[2::4]
        b3 = bit_sign[3::4]
        i = b0 * (2.0 - b1)
        q = b2 * (2.0 - b3)
        return ((i + 1j * q) / math.sqrt(10.0)).astype(np.complex128)
    if n_bpsc == 6:
        b0 = bit_sign[0::6]
        b1 = bit_sign[1::6]
        b2 = bit_sign[2::6]
        b3 = bit_sign[3::6]
        b4 = bit_sign[4::6]
        b5 = bit_sign[5::6]
        i = b0 * (4.0 - b1 * (2.0 - b2))
        q = b3 * (4.0 - b4 * (2.0 - b5))
        return ((i + 1j * q) / math.sqrt(42.0)).astype(np.complex128)
    raise ValueError(f"Unsupported N_BPSC {n_bpsc}")


def _l_sig_bits(length_bytes: int, rate_bits: np.ndarray) -> np.ndarray:
    reserved = np.array([0], dtype=np.int8)
    length_bits = np.array([(length_bytes >> i) & 1 for i in range(12)], dtype=np.int8)
    body = np.concatenate([rate_bits, reserved, length_bits])
    parity = np.array([int(np.sum(body) & 1)], dtype=np.int8)
    tail = np.zeros(6, dtype=np.int8)
    return np.concatenate([body, parity, tail])


def _lts_frequency() -> np.ndarray:
    lts_f = np.array(
        [0, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1],
        dtype=np.complex128,
    )
    return lts_f


def _stf_frequency() -> np.ndarray:
    stf = np.zeros(FFT_LEN, dtype=np.complex128)
    values = {
        -24: 1 + 1j,
        -20: -1 - 1j,
        -16: 1 + 1j,
        -12: -1 - 1j,
        -8: -1 - 1j,
        -4: 1 + 1j,
        4: -1 - 1j,
        8: -1 - 1j,
        12: 1 + 1j,
        16: 1 + 1j,
        20: 1 + 1j,
        24: 1 + 1j,
    }
    scale = math.sqrt(13.0 / 6.0)
    for subcarrier, value in values.items():
        stf[_subcarrier_to_bin(subcarrier)] = scale * value
    return stf


def _ifft_symbol(freq_bins: np.ndarray) -> np.ndarray:
    return np.fft.ifft(freq_bins).astype(np.complex128)


def _apply_boundary_average(prev: np.ndarray, curr: np.ndarray, prev_suffix_idx: int) -> np.ndarray:
    out = curr.copy()
    out[0] = 0.5 * (prev[prev_suffix_idx] + curr[0])
    return out


def _build_l_stf() -> np.ndarray:
    short_symbol = _ifft_symbol(_stf_frequency())
    return np.tile(short_symbol[:16], 10)


def _build_l_ltf() -> np.ndarray:
    ltf = _ifft_symbol(_lts_frequency())
    return np.concatenate([ltf[-32:], ltf, ltf])


def _ofdm_symbol(data_values: np.ndarray, pilot_values: np.ndarray) -> np.ndarray:
    freq = np.zeros(FFT_LEN, dtype=np.complex128)
    for carrier, value in zip(DATA_SUBCARRIERS, data_values, strict=True):
        freq[_subcarrier_to_bin(int(carrier))] = value
    for carrier, value in zip(PILOT_SUBCARRIERS, pilot_values, strict=True):
        freq[_subcarrier_to_bin(int(carrier))] = value
    time = _ifft_symbol(freq)
    return np.concatenate([time[-CP_LEN:], time])


def _build_l_sig(length_bytes: int, mcs: int) -> np.ndarray:
    bits = _l_sig_bits(length_bytes, NONHT_MCS_TABLE[mcs]["rate_bits"])
    coded = _conv_encode(bits)
    interleaved = _interleave(coded, n_cbps=48, n_bpsc=1)
    data_values = _bpsk_map(interleaved)
    pilot_values = np.array([1, 1, 1, -1], dtype=np.complex128)
    return _ofdm_symbol(data_values, pilot_values)


def _resolve_psdu_bits(args: dict[str, Any], rng: np.random.Generator) -> tuple[np.ndarray, int]:
    vector = load_test_vector_payload(args)
    message = None
    scrambler_initialization = int(args.get("scramblerInitialization", 93))
    if vector is not None:
        message = vector.get("message_bits")
        if "scrambler_initialization" in vector:
            scrambler_initialization = int(np.asarray(vector["scrambler_initialization"]).reshape(-1)[0])
    if message is None:
        message = args.get("message")
    default_bit_count = _default_psdu_bit_count(args)
    psdu_bits = _bit_array(message, fallback_length=default_bit_count, rng=rng)
    return psdu_bits, scrambler_initialization


def _puncture(bits: np.ndarray, pattern: np.ndarray) -> np.ndarray:
    pattern = np.asarray(pattern, dtype=np.int8).reshape(-1)
    reps = int(math.ceil(bits.size / pattern.size))
    mask = np.tile(pattern, reps)[: bits.size].astype(bool)
    return bits[mask]


def _build_data_symbols(psdu_bits: np.ndarray, scrambler_initialization: int, mcs: int) -> list[np.ndarray]:
    params = NONHT_MCS_TABLE[mcs]
    n_bpsc = int(params["nbpsc"])
    n_cbps = int(params["ncbps"])
    n_dbps = int(params["ndbps"])
    puncture_pattern = np.asarray(params["puncture"], dtype=np.int8)

    service = np.zeros(16, dtype=np.int8)
    base_bits = np.concatenate([service, psdu_bits])
    n_sym = int(math.ceil((base_bits.size + 6) / n_dbps))
    pad_len = n_sym * n_dbps - (base_bits.size + 6)
    tail = np.zeros(6, dtype=np.int8)
    pad = np.zeros(pad_len, dtype=np.int8)
    data_bits = np.concatenate([base_bits, tail, pad])
    scrambled = _scramble(data_bits, scrambler_initialization)
    tail_start = base_bits.size
    scrambled[tail_start : tail_start + tail.size] = 0
    coded = _puncture(_conv_encode(scrambled), puncture_pattern)
    symbols: list[np.ndarray] = []
    for sym_idx in range(n_sym):
        block = coded[sym_idx * n_cbps : (sym_idx + 1) * n_cbps]
        interleaved = _interleave(block, n_cbps=n_cbps, n_bpsc=n_bpsc)
        data_values = _modulate_data_bits(interleaved, n_bpsc)
        polarity = PILOT_POLARITY[(sym_idx + 1) % PILOT_POLARITY.size]
        pilot_values = polarity * np.array([1, 1, 1, -1], dtype=np.complex128)
        symbols.append(_ofdm_symbol(data_values, pilot_values))
    return symbols


def _build_data_field(psdu_bits: np.ndarray, scrambler_initialization: int, mcs: int) -> np.ndarray:
    symbols = _build_data_symbols(psdu_bits, scrambler_initialization, mcs)
    return np.concatenate(symbols)


def wlan_nonht_burst(args: dict[str, Any], rng: np.random.Generator, *, apply_power: bool = True) -> GeneratedBurst:
    mcs = _resolve_mcs(args)
    psdu_bits, scrambler_initialization = _resolve_psdu_bits(args, rng)
    length_bytes = psdu_bits.size // 8
    lstf = _build_l_stf()
    lltf = _apply_boundary_average(lstf, _build_l_ltf(), 0)
    lsig = _apply_boundary_average(lltf, _build_l_sig(length_bytes, mcs), -FFT_LEN)
    data_symbols = _build_data_symbols(psdu_bits, scrambler_initialization, mcs)
    windowed_data: list[np.ndarray] = []
    prev = lsig
    prev_suffix_idx = CP_LEN
    for symbol in data_symbols:
        symbol_w = _apply_boundary_average(prev, symbol, prev_suffix_idx)
        windowed_data.append(symbol_w)
        prev = symbol_w
        prev_suffix_idx = CP_LEN
    samples = np.concatenate([lstf, lltf, lsig, *windowed_data]).astype(np.complex128)
    if apply_power:
        samples = scale_to_power(samples, float(args.get("txPower_db", -74)))

    return GeneratedBurst(
        samples=samples.astype(np.complex64),
        sample_rate_hz=SAMPLE_RATE_HZ,
        bandwidth_hz=float(args.get("bandwidth_Hz", 16.8e6)),
        protocol="wifi",
        modality="multi_carrier",
        modulation="wlan_non_ht_802_11_g",
        extras={
            "mcs": mcs,
            "scramblerInitialization": scrambler_initialization,
            "message": psdu_bits.tolist(),
            "psduLength": length_bytes,
        },
    )


class WlanNonHT80211gSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return wlan_nonht_burst(self.args, rng)
