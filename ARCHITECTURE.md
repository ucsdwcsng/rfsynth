# Architecture

This document describes the current `rfsynth` flow end to end, including config ingestion, synthetic IQ generation, plotting and verification, compressed artifact generation, and OTA replay.

## 1. System split

`rfsynth` is intentionally split into two subsystems:

- MATLAB: waveform semantics, traffic expansion, source/channel effects, metadata generation, synthetic IQ generation, compressed artifact generation
- Python: config checking, plotting, visual verification, test-output export, OTA bundle handling, metadata offsetting, and SDR replay orchestration

The most important architectural boundary is:

- MATLAB decides what the scene means.
- Python decides how to inspect it or replay it.

## 2. Canonical object model

The core MATLAB abstraction is `source -> signal -> energy`.

```mermaid
flowchart TD
    RX["Rx"] --> ENG["VirtualSignalEngine / CompressedEngine"]
    ENG --> SRC["Source[*]"]
    SRC --> SIG["Signal[*]"]
    SIG --> TRAF["Traffic"]
    SIG --> EN["Transmission / energy[*]"]
    SRC --> IMP["RF impairments"]
    SRC --> CH["Channel model"]
    SIG --> SIGMETA["report.Signal"]
    EN --> ENMETA["report.Transmission"]
```

Meaning of each object:

- `Traffic`: when transmissions happen
- `Signal`: what one transmission waveform looks like
- `Source`: which signals belong to the same emitter and what source-level transforms are applied
- `Rx`: the synthetic observation point
- `Tx`: replay capacity in the compressed path only

`Tx` is not part of waveform semantics. It only appears when compressed generation needs to assign signals to replay resources.

## 3. Current config surfaces

There are three supported frontends:

| Flow | Config type | Entry point |
| --- | --- | --- |
| Synthetic generation | YAML | `matlab/examples/auto_siggen.m` |
| Synthetic generation | JSON | `matlab/examples/run_synthetic_json.m` |
| Compressed generation | YAML | `matlab/examples/auto_compressed_siggen.m` |

Structural config validation is handled by:

- `scripts/check_configs.py`

Detailed field definitions are documented in:

- [CONFIG_FORMAT.md](./CONFIG_FORMAT.md)

## 4. Synthetic generation flow

The synthetic path is the main path for generated IQ plus metadata.

```mermaid
flowchart LR
    A["YAML or JSON config"] --> B["check_configs.py<br/>optional"]
    B --> C["auto_siggen.m or run_synthetic_json.m"]
    C --> D["Normalized config"]
    D --> E["atomic.Rx"]
    D --> F["atomic.Source[*]"]
    F --> G["atomic.Signal[*]"]
    G --> H["Traffic expansion"]
    H --> I["generateTransmission()"]
    I --> J["Source effects<br/>IQ imbalance / DC / CFO / channel"]
    J --> K["Placement into Rx sample rate and center frequency"]
    E --> L["VirtualSignalEngine"]
    K --> L
    L --> M["Composite IQ"]
    L --> N["Metadata JSON"]
    L --> O["Scoring JSON"]
```

### 4.1 Synthetic config normalization

The synthetic wrappers both normalize into the same internal ingredients:

- `generationParameters`
- `rxConfig`
- `signals` or `sources`

`run_synthetic_json.m` now supports a short human-authored JSON form:

- `output`
- `rx`
- `signals`

and converts it into the same normalized shape the engine expects.

Important convenience behavior:

- if top-level `signals` are provided, each signal gets its own default `Source`
- if `trafficType` is omitted in the short JSON form, it defaults to periodic traffic at `100` transmissions per second
- default source channel is identity and default impairments are zero

### 4.2 Object construction

After normalization:

1. `atomic.Rx` is constructed from `rxConfig`
2. one or more `atomic.Source` objects are constructed
3. each source constructs one or more concrete `atomic.Signal` subclasses
4. `VirtualSignalEngine` owns the final scene assembly

### 4.3 Signal generation internals

For each signal:

1. `Traffic` expands the scene timing into concrete transmissions
2. the atomic waveform class generates baseband samples for each transmission through `generateTransmission()`
3. `Source` applies source-level effects:
   - carrier frequency offset
   - IQ imbalance
   - DC offset
   - channel model
4. the generated samples are resampled and shifted into the configured `Rx` observation band
5. `VirtualSignalEngine` sums all source contributions into one composite IQ output

### 4.4 Synthetic outputs

The synthetic path writes:

- `<base>.32cf`
- `<base>.json`
- `<base>_scoring.json`

These are written through `VirtualSignalEngine.writeDataFiles(...)`.

## 5. Plotting and visual verification flow

The plotting/verification path is synthetic-only and is intentionally separate from MATLAB generation.

```mermaid
flowchart LR
    A["<base>.32cf"] --> B["plot_and_verify_synthetic.py"]
    C["<base>.json"] --> B
    D["<base>_scoring.json"] --> B
    B --> E["time.png"]
    B --> F["psd.png"]
    B --> G["spectrogram.png"]
    B --> H["fullband_overlay.png"]
    B --> I["fullband_occupancy.png"]
    B --> J["zoom_overlay.png"]
    B --> K["zoom_occupancy.png"]
    B --> L["verify.json"]
```

What the plotter does:

- loads the generated IQ
- computes time-domain, PSD, and spectrogram views
- overlays signal and energy metadata boxes on top of the spectrogram
- colors signal families distinctly in mixed scenes
- writes a verification summary describing whether energy appears where metadata says it should

This is how the repo currently validates the synthetic atomic configs and the sneaky-neighbor scenes.

## 6. Repo-local test-output export flow

The repo keeps generated IQ files in `/tmp`, but stores plots and metadata snapshots inside the repo for inspection.

```mermaid
flowchart LR
    A["/tmp/<base>.json"] --> D["export_test_outputs.py"]
    B["/tmp/<base>_scoring.json"] --> D
    C["/tmp/<base>_*.png"] --> D
    E["/tmp/<base>_verify.json"] --> D
    F["source config"] --> D
    D --> G["configs/test_outputs/<name>/"]
```

Each exported bundle typically contains:

- `config.json`
- `metadata.json`
- `scoring.json`
- `verify.json`
- `time.png`
- `psd.png`
- `spectrogram.png`
- `occupancy.png`
- `fullband_overlay.png`
- `fullband_occupancy.png`
- `zoom_overlay.png`
- `zoom_occupancy.png`

No `.32cf` files are copied into the repo.

## 7. Compressed generation flow

The compressed path is used when the goal is long-duration replay rather than a single fully synthesized IQ output.

```mermaid
flowchart LR
    A["compressed_config.yml"] --> B["auto_compressed_siggen.m"]
    B --> C["CompressedEngine"]
    C --> D["Signal-to-Tx assignment"]
    C --> E["Per-signal compressed IQ generation"]
    C --> F["Metadata split and energy schedule"]
    E --> G["signal_iq/*.32cf"]
    F --> H["metadata.json"]
    F --> I["_scoring.json"]
    F --> J["_energy_meta.csv"]
    G --> K["zip bundle"]
    H --> K
    I --> K
    J --> K
```

Key distinction from the synthetic path:

- synthetic generation produces one final IQ output at the `Rx`
- compressed generation produces replay-oriented signal payloads and scheduling metadata

`Tx` objects matter here because the engine must decide which logical transmitter can replay which signal without overlap conflicts.

## 8. OTA replay flow

The Python OTA path consumes the compressed bundle and maps it to real radios.

```mermaid
flowchart LR
    A["compressed zip bundle"] --> B["rfsynth_tx.py"]
    B --> C["utils.py"]
    C --> D["Archive extraction"]
    C --> E["Ground-truth time offsetting"]
    C --> F["realTimeTestbed.py"]
    F --> G["transmitter.py"]
    G --> H["transmitter_flowgraph.py"]
    H --> I["GNU Radio / UHD timed replay"]
    I --> J["USRP radios"]
```

This path assumes:

- the compressed MATLAB bundle is already correct
- the `_energy_meta.csv` schedule matches the payload IQ files
- the radio JSON config maps bundle artifacts to real UHD devices

## 9. Implemented waveform inventory

Current concrete atomics in `matlab/lib/+atomic/`:

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

## 10. Current synthetic test strategy

The current repo-level synthetic checks are:

1. validate config structure with `check_configs.py`
2. generate IQ plus metadata in MATLAB
3. plot and visually verify the result with `plot_and_verify_synthetic.py`
4. export metadata and plots into `configs/test_outputs/`

The main config sets used for this are:

- `configs/synthetic_atomic/*.json`
- `configs/synthetic_examples/*.json`

The mixed-scene examples currently include:

- `ofdm_am_adjacent`
- `ofdm_fsk_adjacent`
- `wlan_tone_adjacent`
- `qam_channel_edge`

## 11. Extension points

If you want to extend the repository, the practical extension points are:

- new waveform class: `matlab/lib/+atomic/<NewSignal>.m`
- new timing model: `matlab/lib/+atomic/Traffic.m`
- new metadata field: `matlab/lib/metadata_utils/+report/*`
- synthetic scene behavior: `matlab/lib/VirtualSignalEngine.m`
- compressed artifact behavior: `matlab/lib/CompressedEngine.m`
- JSON config normalization: `matlab/examples/run_synthetic_json.m`
- plotting and verification behavior: `scripts/plot_and_verify_synthetic.py`
- repo-local output packaging: `scripts/export_test_outputs.py`
- OTA orchestration: `rfsynth/rfsynth_tx.py` and `rfsynth/otatestbed/*`

## 12. Short version

The full operational story is:

1. author a YAML or JSON config
2. validate it structurally
3. generate synthetic IQ plus metadata in MATLAB
4. inspect the IQ visually against metadata
5. export plots and metadata for repo-local review
6. optionally generate compressed artifacts instead
7. optionally replay those compressed artifacts over SDR

That is the current architecture in its actual code path, not just the paper-level abstraction.
