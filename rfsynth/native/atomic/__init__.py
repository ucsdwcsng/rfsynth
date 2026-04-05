from __future__ import annotations

from rfsynth.native.core import Signal, Traffic

from .am import AmSignal
from .bluetooth import BluetoothSignal
from .cpfsk import CpfskSignal
from .ds3 import Ds3Signal
from .dummy_signal import DummySignal
from .fm import FmSignal
from .freq_hopping import FreqHoppingSignal
from .fsk import FskSignal
from .gfsk import GfskSignal
from .gmsk import GmskSignal
from .msk import MskSignal
from .ofdm import OfdmSignal
from .pam import PamSignal
from .psk import PskSignal
from .qam import QamSignal
from .random_symbol import RandomSymbolSignal
from .sine import SineSignal
from .ssb import SsbSignal
from .wideband_thermal_wgn import WidebandThermalWgnSignal
from .wlan_nonht80211g import WlanNonHT80211gSignal

REGISTRY: dict[str, type[Signal]] = {
    "Am": AmSignal,
    "Bluetooth": BluetoothSignal,
    "Cpfsk": CpfskSignal,
    "Ds3": Ds3Signal,
    "DummySignal": DummySignal,
    "Fm": FmSignal,
    "FreqHopping": FreqHoppingSignal,
    "Fsk": FskSignal,
    "Gfsk": GfskSignal,
    "Gmsk": GmskSignal,
    "Msk": MskSignal,
    "Ofdm": OfdmSignal,
    "Pam": PamSignal,
    "Psk": PskSignal,
    "Qam": QamSignal,
    "RandomSymbol": RandomSymbolSignal,
    "Sine": SineSignal,
    "Ssb": SsbSignal,
    "WidebandThermalWgn": WidebandThermalWgnSignal,
    "WlanNonHT80211g": WlanNonHT80211gSignal,
}


def create_signal(type_name: str, args: dict, traffic: Traffic | None = None) -> Signal:
    try:
        cls = REGISTRY[type_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported signal type for Python-native rendering: {type_name}") from exc
    return cls(type_name=type_name, args=args, traffic=traffic)
