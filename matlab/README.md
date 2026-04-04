# `matlab` signal generator for `rfsynth`

The MATLAB tree is the core generation engine for `rfsynth`. It owns:

- synthetic IQ generation
- compressed artifact generation for OTA replay
- waveform classes
- traffic expansion
- source/channel effects
- metadata generation

Related docs:

- [README.md](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [CONFIG_FORMAT.md](../CONFIG_FORMAT.md)

## Directory structure

```text
lib/        core engines, atomics, metadata utilities, helpers
examples/   user-facing entrypoints and example scripts
```

## Requirements

- MATLAB `R2021b` or later
- Communications Toolbox
- Bluetooth Toolbox
- WLAN Toolbox

Some code paths also rely on MATLAB functionality referenced in the codebase such as `winner2.*`, `comm.*`, and `fixed.Interval`.

## Entry points

### Synthetic generation from YAML

Use [auto_siggen.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/auto_siggen.m):

```matlab
auto_siggen('matlab/examples/config.yml');
```

This reads a YAML config, builds the scene, and writes:

- `<base>.32cf`
- `<base>.json`
- `<base>_scoring.json`

### Synthetic generation from JSON

Use [run_synthetic_json.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/run_synthetic_json.m):

```matlab
run_synthetic_json('configs/synthetic_examples/ofdm_am_adjacent_simple.json');
```

This is the JSON counterpart to `auto_siggen`. It supports:

- the verbose JSON format
- the short human-authored JSON format documented in [CONFIG_FORMAT.md](../CONFIG_FORMAT.md)

### Compressed generation for OTA replay

Use [auto_compressed_siggen.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/auto_compressed_siggen.m):

```matlab
auto_compressed_siggen('matlab/examples/compressed_config.yml');
```

This writes replay-oriented artifacts rather than one final composite synthetic IQ output.

## Main MATLAB components

| Path | Responsibility |
| --- | --- |
| `lib/VirtualSignalEngine.m` | full-scene synthetic engine |
| `lib/CompressedEngine.m` | compressed artifact engine |
| `lib/+atomic/Signal.m` | waveform base class |
| `lib/+atomic/Source.m` | source-level effects and composition |
| `lib/+atomic/Traffic.m` | timing expansion |
| `lib/metadata_utils/+report/` | metadata model and JSON serialization |

## Current atomics

Concrete waveform classes under `lib/+atomic/` currently include:

- `Am`
- `Bluetooth`
- `Cpfsk`
- `Ds3`
- `DummySignal`
- `Fm`
- `FreqHopping`
- `Fsk`
- `Gfsk`
- `Gmsk`
- `Msk`
- `Ofdm`
- `Pam`
- `Psk`
- `Qam`
- `RandomSymbol`
- `Sine`
- `Ssb`
- `WidebandThermalWgn`
- `WlanNonHT80211g`

## Programmatic API

[siggen_api.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/siggen_api.m) is the simplest example of direct programmatic use. Use that path when you want explicit MATLAB object construction rather than config-driven generation.
