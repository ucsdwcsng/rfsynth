from __future__ import annotations

import math
from typing import Any

import numpy as np

from rfsynth.native.atomic.common import load_test_vector_payload, scale_to_power
from rfsynth.native.core import GeneratedBurst, Scene, Signal


DEFAULT_ACCESS_ADDRESS_BITS = np.array(
    [0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1],
    dtype=np.int8,
)
VALID_MODES = {"LE1M", "LE2M", "LE500K", "LE125K"}
VALID_DF_PACKET_TYPES = {"Disabled", "ConnectionCTE", "ConnectionlessCTE"}
VALID_WHITEN_STATUS = {"On", "Off"}


def _bit_array(value: Any, *, fallback_length: int, rng: np.random.Generator) -> np.ndarray:
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        return rng.integers(0, 2, size=fallback_length, dtype=np.int8)
    bits = np.asarray(value, dtype=np.int8).reshape(-1)
    return np.bitwise_and(bits, 1).astype(np.int8)


def _int_to_bits(value: int, width: int, *, msb_first: bool) -> np.ndarray:
    bits = np.array([(int(value) >> idx) & 1 for idx in range(width)], dtype=np.int8)
    if msb_first:
        bits = bits[::-1]
    return bits


def _bits_to_int(bits: np.ndarray, *, lsb_first: bool) -> int:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    if not lsb_first:
        bits = bits[::-1]
    value = 0
    for idx, bit in enumerate(bits):
        value |= (int(bit) & 1) << idx
    return value


def _resolve_ble_fields(args: dict[str, Any], rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    vector = load_test_vector_payload(args)
    message = None
    access_address = None
    if vector is not None:
        message = vector.get("message_bits")
        access_address = vector.get("access_address_bits")
    if message is None:
        message = args.get("message")
    if access_address is None:
        access_address = args.get("accessAddress")
    message_bits = _bit_array(message, fallback_length=640, rng=rng)
    access_address_bits = _bit_array(access_address, fallback_length=32, rng=rng)
    if access_address is None and message is not None:
        access_address_bits = DEFAULT_ACCESS_ADDRESS_BITS.copy()
    return message_bits, access_address_bits


def _validate_args(
    message_bits: np.ndarray,
    mode: str,
    channel_index: int,
    samples_per_symbol: int,
    access_address_bits: np.ndarray,
    df_packet_type: str,
    whiten_status: str,
    modulation_index: float,
    pulse_length: int,
) -> None:
    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported Bluetooth mode {mode}; expected one of {sorted(VALID_MODES)}")
    if not 0 <= channel_index <= 39:
        raise ValueError("Bluetooth channelIndex must be in [0, 39]")
    if samples_per_symbol <= 0:
        raise ValueError("Bluetooth samplesPerSymbol must be positive")
    if access_address_bits.size != 32:
        raise ValueError("Bluetooth accessAddress must contain exactly 32 bits")
    if df_packet_type not in VALID_DF_PACKET_TYPES:
        raise ValueError(f"Unsupported Bluetooth DFPacketType {df_packet_type}")
    if whiten_status not in VALID_WHITEN_STATUS:
        raise ValueError(f"Unsupported Bluetooth WhitenStatus {whiten_status}")
    if not (0.45 <= modulation_index <= 0.55):
        raise ValueError("Bluetooth modulationIndex must be in [0.45, 0.55]")
    if abs(round(modulation_index / 0.005) * 0.005 - modulation_index) > 1e-9:
        raise ValueError("Bluetooth modulationIndex must be quantized in 0.005 steps")
    if not 1 <= pulse_length <= 4:
        raise ValueError("Bluetooth pulseLength must be in [1, 4]")
    if message_bits.size > 2088:
        raise ValueError("Bluetooth message length must be <= 2088 bits")
    if df_packet_type == "ConnectionCTE" and mode in {"LE500K", "LE125K"}:
        raise ValueError("ConnectionCTE is valid only for LE1M and LE2M")
    if df_packet_type == "ConnectionlessCTE" and mode != "LE1M":
        raise ValueError("ConnectionlessCTE is valid only for LE1M")
    if df_packet_type == "ConnectionCTE" and message_bits.size < 24:
        raise ValueError("Bluetooth ConnectionCTE requires at least 24 message bits")
    if df_packet_type == "ConnectionlessCTE" and message_bits.size < 40:
        raise ValueError("Bluetooth ConnectionlessCTE requires at least 40 message bits")


def _preamble_generator(mode: str, access_address_bits: np.ndarray) -> np.ndarray:
    first_bit = int(access_address_bits[0])
    if mode == "LE1M":
        return np.bitwise_xor(first_bit, np.array([0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int8))
    if mode == "LE2M":
        return np.bitwise_xor(first_bit, np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int8))
    return np.tile(np.array([0, 0, 1, 1, 1, 1, 0, 0], dtype=np.int8), 10)


def _ble_whiten(bits: np.ndarray, channel_index: int) -> np.ndarray:
    init = np.concatenate([np.array([1], dtype=np.int8), _int_to_bits(channel_index, 6, msb_first=True)])
    seq = np.zeros(127, dtype=np.int8)
    state = init.copy()
    for idx in range(127):
        past_state_7 = state[6]
        past_state_4 = state[3]
        seq[idx] = state[6]
        state = np.roll(state, 1)
        state[4] = past_state_4 ^ past_state_7
    reps = int(math.ceil(bits.size / seq.size))
    return np.bitwise_xor(bits.astype(np.int8), np.tile(seq, reps)[: bits.size])


def _cte_info_extract(bits: np.ndarray, df_packet_type: str) -> tuple[int, int]:
    if df_packet_type == "ConnectionCTE":
        cte_time_field = bits[16:21]
        cte_type_field = bits[22:24]
    else:
        cte_time_field = bits[32:37]
        cte_type_field = bits[38:40]
    return _bits_to_int(cte_time_field, lsb_first=True), _bits_to_int(cte_type_field, lsb_first=True)


def _conv_encode_17_13(bits: np.ndarray) -> np.ndarray:
    # poly2trellis(4,[17 13]) from MATLAB source.
    g0 = np.array([1, 1, 1, 1], dtype=np.int8)
    g1 = np.array([1, 0, 1, 1], dtype=np.int8)
    state = np.zeros(3, dtype=np.int8)
    out = np.zeros(bits.size * 2, dtype=np.int8)
    for idx, bit in enumerate(bits.astype(np.int8)):
        reg = np.concatenate([np.array([bit], dtype=np.int8), state])
        out[2 * idx] = int(np.sum(reg * g0) & 1)
        out[2 * idx + 1] = int(np.sum(reg * g1) & 1)
        state = reg[:-1]
    return out


def _ble_encode_coded(bits: np.ndarray, access_address_bits: np.ndarray, coding_indicator: np.ndarray) -> np.ndarray:
    term_field = np.array([0, 0, 0], dtype=np.int8)
    fec_block = np.concatenate([access_address_bits, coding_indicator, term_field, bits, term_field]).astype(np.int8)
    fec_output = _conv_encode_17_13(fec_block)
    block1_len = access_address_bits.size + coding_indicator.size + term_field.size
    fec_block1 = fec_output[: block1_len * 2]
    fec_block2 = fec_output[block1_len * 2 :]
    pattern = np.array([1, 1, 0, 0], dtype=np.int8)
    if int(coding_indicator[1]) == 0:
        rep_block = np.repeat(fec_output, pattern.size)
        rep_pattern = np.tile(pattern, fec_output.size)
        return np.bitwise_xor(rep_block, rep_pattern) ^ 1
    rep_block1 = np.repeat(fec_block1, pattern.size)
    rep_pattern = np.tile(pattern, fec_block1.size)
    mapped_block1 = np.bitwise_xor(rep_block1, rep_pattern) ^ 1
    return np.concatenate([mapped_block1.astype(np.int8), fec_block2.astype(np.int8)])


def _qfun(x: np.ndarray) -> np.ndarray:
    return 0.5 * np.vectorize(math.erfc)(x / math.sqrt(2.0))


def _gmskmodparams(bt_prod: float, pulse_length: int, sps: int) -> np.ndarray:
    min_os_ratio = 64
    upsample_ratio = int(math.ceil(min_os_ratio / sps))
    ts = 1.0 / (sps * upsample_ratio)
    offset = ts / 2.0
    t = np.arange(offset, pulse_length - ts + offset + 0.5 * ts, ts, dtype=np.float64)
    k = 2.0 * math.pi * bt_prod / math.sqrt(math.log(2.0))
    t = t - (pulse_length / 2.0)
    g = 0.5 * (_qfun(k * (t - 0.5)) - _qfun(k * (t + 0.5)))
    q = ts * np.cumsum(g)
    g = g * (0.5 / q[-1])
    g_wrap = g.reshape((upsample_ratio, -1), order="F").mean(axis=0)
    g = ts * upsample_ratio * g_wrap
    q = np.concatenate([np.array([0.0]), np.cumsum(g[:-1])])
    return q.astype(np.float64)


def _ble_gmskmod(bits: np.ndarray, sps: int, modulation_index: float, pulse_length: int) -> np.ndarray:
    q = _gmskmodparams(0.5, pulse_length, sps)
    n_sym = bits.size
    if pulse_length > 1:
        symb_pre_hist = modulation_index * np.ones(sps * (pulse_length - 1), dtype=np.float64)
        phvec = (modulation_index * q[sps:]).reshape((sps, pulse_length - 1), order="F").sum(axis=1)
        pre_hist_phase = 2.0 * math.pi * phvec[0]
    else:
        symb_pre_hist = np.zeros(0, dtype=np.float64)
        pre_hist_phase = 0.0
    data = np.repeat(bits.astype(np.float64), sps)
    scaled_data = np.concatenate([symb_pre_hist, modulation_index * (2.0 * data - 1.0)])
    filt_idx = np.arange(pulse_length * sps - 1, -1, -1, dtype=np.int64)
    phi = np.zeros(n_sym * sps, dtype=np.float64)
    phase_state = 0.0
    for sym_idx in range(n_sym):
        filt_data = scaled_data[filt_idx + sym_idx * sps] * q
        filt_phase = filt_data.reshape((sps, pulse_length), order="F").sum(axis=1)
        phi[sym_idx * sps : (sym_idx + 1) * sps] = phase_state + filt_phase
        phase_state = phase_state + 0.5 * scaled_data[sym_idx * sps]
    cpm_phase = 2.0 * math.pi * phi - pre_hist_phase
    return np.exp(1j * cpm_phase).astype(np.complex128)


def _effective_symbol_rate_hz(mode: str) -> float:
    if mode == "LE2M":
        return 2e6
    return 1e6


def _default_bandwidth_hz(mode: str) -> float:
    if mode == "LE2M":
        return 2.51e6
    return 1.255e6


def bluetooth_burst(args: dict[str, Any], rng: np.random.Generator, *, apply_power: bool = True) -> GeneratedBurst:
    mode = str(args.get("mode", "LE1M"))
    channel_index = int(args.get("channelIndex", 37))
    samples_per_symbol = int(args.get("samplesPerSymbol", 8))
    df_packet_type = str(args.get("DFPacketType", "Disabled"))
    whiten_status = str(args.get("WhitenStatus", "Off"))
    modulation_index = float(args.get("modulationIndex", 0.5))
    pulse_length = int(args.get("pulseLength", 1))

    message_bits, access_address_bits = _resolve_ble_fields(args, rng)
    _validate_args(
        message_bits,
        mode,
        channel_index,
        samples_per_symbol,
        access_address_bits,
        df_packet_type,
        whiten_status,
        modulation_index,
        pulse_length,
    )

    preamble = _preamble_generator(mode, access_address_bits)
    if whiten_status == "On":
        whitened_message = _ble_whiten(message_bits, channel_index)
    else:
        whitened_message = message_bits.copy()

    if df_packet_type != "Disabled":
        cte_time, _ = _cte_info_extract(message_bits, df_packet_type)
        cte_num_bits = cte_time * 8 * (2 if mode == "LE2M" else 1)
        pdu_cte = np.concatenate([whitened_message, np.ones(cte_num_bits, dtype=np.int8)])
    else:
        pdu_cte = whitened_message

    if mode in {"LE500K", "LE125K"}:
        coding_indicator = np.array([0, 1] if mode == "LE500K" else [0, 0], dtype=np.int8)
        phy_frame = np.concatenate([preamble, _ble_encode_coded(pdu_cte, access_address_bits, coding_indicator)])
    else:
        phy_frame = np.concatenate([preamble, access_address_bits, pdu_cte]).astype(np.int8)

    samples = _ble_gmskmod(phy_frame, samples_per_symbol, modulation_index, pulse_length)
    if apply_power:
        samples = scale_to_power(samples, float(args.get("txPower_db", -79)))

    return GeneratedBurst(
        samples=samples.astype(np.complex64),
        sample_rate_hz=_effective_symbol_rate_hz(mode) * samples_per_symbol,
        bandwidth_hz=float(args.get("bandwidth_Hz", _default_bandwidth_hz(mode))),
        protocol="bluetooth",
        modality="single_carrier",
        modulation="gmsk",
        extras={
            "mode": mode,
            "samplesPerSymbol": samples_per_symbol,
            "channelIndex": channel_index,
            "accessAddress": access_address_bits.tolist(),
            "message": message_bits.tolist(),
            "DFPacketType": df_packet_type,
            "WhitenStatus": whiten_status,
            "modulationIndex": modulation_index,
            "pulseLength": pulse_length,
        },
    )


class BluetoothSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return bluetooth_burst(self.args, rng)
