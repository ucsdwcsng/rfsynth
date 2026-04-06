# Python-Native Runtime

This document explains how the current Python-native synthetic path is executed in code.

Scope:

- covers the Python-native runtime under `rfsynth/native/`
- covers the current non-LTE atomic registry and dispatch path
- covers plotting, verification, replay, and compare sidecars that are part of the Python-native workflow
- intentionally does not document `rfsynth/native/atomic/lte_dl_fdd.py`, which is under active revision

## 1. Public entrypoints

The Python-native path is exposed in two equivalent ways.

### Library API

- `rfsynth.load_scene(...)`
- `rfsynth.render_synthetic(...)`
- `rfsynth.plot_artifacts(...)`
- `rfsynth.verify_artifacts(...)`
- `rfsynth.compile_replay(...)`
- `rfsynth.run_replay(...)`

These are re-exported from:

- [`rfsynth/__init__.py`](./rfsynth/__init__.py)
- [`rfsynth/native/__init__.py`](./rfsynth/native/__init__.py)

### CLI

The CLI is in [`rfsynth/cli.py`](./rfsynth/cli.py):

- `rfsynth check`
- `rfsynth generate`
- `rfsynth plot`
- `rfsynth verify`
- `rfsynth replay simulate`
- `rfsynth replay usrp`

## 2. Exact render call order

For `rfsynth generate`, the call chain is:

```text
cli.main()
  -> render_synthetic(scene_or_path, out_dir, seed)
    -> load_scene(...)                     if the input is not already a Scene
      -> normalize_generation(...)
      -> normalize_rx(...)
      -> normalize_sources(...)
        -> normalize_source(...)           for each source, or auto-wrap top-level signals
          -> build_signal(...)
            -> normalize_signal_args(...)
            -> parse_traffic(...)
            -> create_signal(type_name, args, traffic)
              -> REGISTRY[type_name](...)
    -> VirtualSignalEngine(scene).render(...)
      -> VirtualSignalEngine.generate_samples(seed)
        -> Source.generate_samples(...)    for each source
          -> signal.generate_transmission(scene, rng)
          -> resample_if_needed(...)
          -> frequency_shift(...)
          -> Source.apply_nonideal_transform(...)
          -> Source.apply_channel(...)
          -> signal.compute_transmission_windows(...)
          -> place_burst(...)              for each transmission window
          -> signal.build_render_result(...)
      -> VirtualSignalEngine.build_metadata(...)
      -> VirtualSignalEngine.build_scoring(...)
      -> write_cf32(...)
      -> write metadata JSON
      -> write scoring JSON
```

The main files involved are:

- [`rfsynth/cli.py`](./rfsynth/cli.py)
- [`rfsynth/native/render.py`](./rfsynth/native/render.py)
- [`rfsynth/native/scene.py`](./rfsynth/native/scene.py)
- [`rfsynth/native/core.py`](./rfsynth/native/core.py)
- [`rfsynth/native/atomic/__init__.py`](./rfsynth/native/atomic/__init__.py)

## 3. Scene loading and signal construction

Scene loading happens in [`rfsynth/native/scene.py`](./rfsynth/native/scene.py).

The current sequence is:

1. `load_scene(...)` accepts a JSON path or a Python dict.
2. `normalize_generation(...)` converts `generationParameters` or `output` into `GenerationSpec`.
3. `normalize_rx(...)` converts `rxConfig` or `rx` into `Rx`.
4. `normalize_sources(...)` does one of:
   - normalize explicit `sources`
   - or auto-wrap each top-level `signals[]` entry into its own default `Source`
5. `build_signal(...)` normalizes `args`, parses `trafficType`, and calls `create_signal(...)`.
6. `create_signal(...)` looks up the atomic class in `rfsynth/native/atomic/REGISTRY`.

That means the runtime never uses reflection or file-name scanning at render time. Atomic dispatch is a direct registry lookup in:

- [`rfsynth/native/atomic/__init__.py`](./rfsynth/native/atomic/__init__.py)

## 4. Render loop responsibilities

The current runtime split is:

- `Traffic.transmission_start_times(...)`
  - computes when transmissions start
- `Signal.generate_transmission(...)`
  - generates one burst at the atomic's own sample rate
- `Source.generate_samples(...)`
  - handles resample, center-frequency placement, impairments, channel, and composite placement
- `VirtualSignalEngine.render(...)`
  - writes IQ and metadata artifacts

Important detail:

- The atomic class returns one burst, not the full scene.
- The source loop places the same burst at every transmission window returned by `Traffic`.
- Placement into the final scene always happens at the receiver sample rate.

## 5. Non-LTE atomic dispatch table

Every non-LTE atomic follows the same registry pattern:

- `scene.py -> create_signal(...) -> REGISTRY[type_name] -> <AtomicSignal>`
- later, `Source.generate_samples(...)` calls `<AtomicSignal>.generate_transmission(scene, rng)`

The implementation behind that call depends on the atomic family.

| Signal type | Registry class | Main implementation called from `generate_transmission(...)` | Notes |
| --- | --- | --- | --- |
| `Am` | `AmSignal` | `common.am_burst(args)` | Thin wrapper over shared analog helper |
| `Bluetooth` | `BluetoothSignal` | `bluetooth.bluetooth_burst(args, rng)` | Standalone protocol implementation |
| `Cpfsk` | `CpfskSignal` | `common.fsk_like_burst(...)` | Parameterized FSK-family helper |
| `Ds3` | `Ds3Signal` | `common.ds3_burst(args, rng)` | Shared spread-spectrum helper |
| `DummySignal` | `DummySignal` | `common.dummy_burst(args)` | Deterministic placeholder burst |
| `Fm` | `FmSignal` | `common.fm_burst(args)` | Thin wrapper over shared analog helper |
| `FreqHopping` | `FreqHoppingSignal` | `common.freq_hopping_burst(args, rng)` | Shared hopping helper |
| `Fsk` | `FskSignal` | `common.fsk_like_burst(...)` | Parameterized FSK-family helper |
| `Gfsk` | `GfskSignal` | `common.fsk_like_burst(...)` | Parameterized FSK-family helper |
| `Gmsk` | `GmskSignal` | `common.fsk_like_burst(...)` | Parameterized FSK-family helper |
| `Msk` | `MskSignal` | `common.fsk_like_burst(...)` | Parameterized FSK-family helper |
| `nr5g` | `Nr5gSignal` | `nr5g.nr5g_burst(args, rng)` | Standalone NR builder plus helper constants |
| `Ofdm` | `OfdmSignal` | `common.ofdm_burst(args, rng)` | Shared OFDM helper |
| `Pam` | `PamSignal` | `common.pam_burst(args, rng)` | Shared pulse-shaped symbol helper |
| `Psk` | `PskSignal` | `common.psk_burst(args, rng)` | Shared pulse-shaped symbol helper |
| `Qam` | `QamSignal` | `common.qam_burst(args, rng)` | Shared pulse-shaped symbol helper |
| `RandomSymbol` | `RandomSymbolSignal` | `common.random_symbol_burst(args, rng)` | Shared symbol-repeat helper |
| `Sine` | `SineSignal` | `common.sine_burst(args)` | Thin wrapper over tone helper |
| `Ssb` | `SsbSignal` | `common.ssb_burst(args)` | Thin wrapper over analog helper |
| `WidebandThermalWgn` | `WidebandThermalWgnSignal` | `common.noise_burst(args, total_time_s, rx_sample_rate_hz, rng)` | Uses scene duration and Rx rate |
| `WlanNonHT80211g` | `WlanNonHT80211gSignal` | `wlan_nonht80211g.wlan_nonht_burst(args, rng)` | Standalone protocol implementation |

### Thin-wrapper atomics

These files exist mainly so the registry can return a `Signal` subclass with the right type name:

- [`rfsynth/native/atomic/am.py`](./rfsynth/native/atomic/am.py)
- [`rfsynth/native/atomic/fm.py`](./rfsynth/native/atomic/fm.py)
- [`rfsynth/native/atomic/ssb.py`](./rfsynth/native/atomic/ssb.py)
- [`rfsynth/native/atomic/sine.py`](./rfsynth/native/atomic/sine.py)
- [`rfsynth/native/atomic/dummy_signal.py`](./rfsynth/native/atomic/dummy_signal.py)
- [`rfsynth/native/atomic/ds3.py`](./rfsynth/native/atomic/ds3.py)
- [`rfsynth/native/atomic/freq_hopping.py`](./rfsynth/native/atomic/freq_hopping.py)
- [`rfsynth/native/atomic/ofdm.py`](./rfsynth/native/atomic/ofdm.py)
- [`rfsynth/native/atomic/pam.py`](./rfsynth/native/atomic/pam.py)
- [`rfsynth/native/atomic/psk.py`](./rfsynth/native/atomic/psk.py)
- [`rfsynth/native/atomic/qam.py`](./rfsynth/native/atomic/qam.py)
- [`rfsynth/native/atomic/random_symbol.py`](./rfsynth/native/atomic/random_symbol.py)

### Parameterized FSK-family wrappers

These all share one underlying helper and differ by the arguments they pass:

- [`rfsynth/native/atomic/cpfsk.py`](./rfsynth/native/atomic/cpfsk.py)
- [`rfsynth/native/atomic/fsk.py`](./rfsynth/native/atomic/fsk.py)
- [`rfsynth/native/atomic/gfsk.py`](./rfsynth/native/atomic/gfsk.py)
- [`rfsynth/native/atomic/gmsk.py`](./rfsynth/native/atomic/gmsk.py)
- [`rfsynth/native/atomic/msk.py`](./rfsynth/native/atomic/msk.py)

The shared helper is:

- [`rfsynth/native/atomic/common.py`](./rfsynth/native/atomic/common.py)

### Standalone protocol builders

These modules implement their own burst builder locally because the waveform logic is protocol-specific:

- [`rfsynth/native/atomic/bluetooth.py`](./rfsynth/native/atomic/bluetooth.py)
- [`rfsynth/native/atomic/wlan_nonht80211g.py`](./rfsynth/native/atomic/wlan_nonht80211g.py)
- [`rfsynth/native/atomic/nr5g.py`](./rfsynth/native/atomic/nr5g.py)

## 6. Post-render call order

### Plot

`rfsynth plot` calls:

```text
cli.main()
  -> plot_artifacts(base)
    -> resolve_bundle(...)
    -> read_cf32(...)
    -> extract_boxes(...)
    -> compute_spectrogram(...)
    -> plot_time(...)
    -> plot_psd(...)
    -> plot_spectrogram(...)
    -> plot_occupancy(...)
```

All of that lives in:

- [`rfsynth/native/plotting.py`](./rfsynth/native/plotting.py)

### Verify

`rfsynth verify` calls:

```text
cli.main()
  -> verify_artifacts(base)
    -> resolve_bundle(...)
    -> read_cf32(...)
    -> extract_boxes(...)
    -> compute_spectrogram(...)
    -> verify_alignment(...)
    -> write <base>_verify.json
```

### Replay

`rfsynth replay simulate` calls:

```text
cli.main()
  -> compile_replay(target)
    -> render_synthetic(...) or resolve_bundle(...)
    -> read metadata
    -> flatten source/signal/transmission metadata into ReplayEvent[]
  -> run_replay(plan, backend="sim")
    -> SimReplayBackend.run(...)
    -> write <base>_sim_replay.json
```

This lives in:

- [`rfsynth/native/replay.py`](./rfsynth/native/replay.py)

## 7. Sidecar modules that are not in the hot render path

### `rfsynth/native/waveforms.py`

This is a thin compatibility layer used by tests and compare helpers. It is not the main render loop.

Current uses:

- `compute_transmission_windows(...)`
- `generate_burst(...)`
- re-exported helpers such as `rrc_taps` and `qam_constellation`

### `rfsynth/native/atomic_compare.py`

This is the raw compare/test-vector sidecar. It:

- loads a single-signal scene
- generates shared test vectors when possible
- compares Python and MATLAB burst-level outputs

It is useful for parity and debugging, but it is not used during ordinary scene rendering.

## 8. Current design boundaries

The main runtime boundary to keep in mind is:

- `scene.py` builds objects
- `atomic/*.py` generates one burst
- `core.py` turns bursts into a scene and writes artifacts
- `plotting.py` and `replay.py` consume written artifacts

That means a tiny atomic wrapper file is normal. Many atomics are intentionally only:

1. registry adapter
2. argument-to-helper translator
3. `GeneratedBurst` producer

Most of the scene semantics are not in the atomic file. They happen later in:

- `Signal.compute_transmission_windows(...)`
- `Source.generate_samples(...)`
- `VirtualSignalEngine.render(...)`
