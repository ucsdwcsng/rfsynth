# Config Format

`rfsynth` currently supports three synthetic-config frontends and one compressed-generation frontend:

- JSON synthetic config via the Python-native CLI and library
- YAML synthetic config via [auto_siggen.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/auto_siggen.m)
- JSON synthetic config via [run_synthetic_json.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/run_synthetic_json.m)
- YAML compressed-generation config via [auto_compressed_siggen.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/auto_compressed_siggen.m)

The shortest format is the JSON synthetic format. That is the easiest one to hand-author and it is the canonical product-facing format for the Python-native path.

## Synthetic YAML

Use this with:

```matlab
auto_siggen('matlab/examples/config.yml');
```

Required top-level keys:

- `generationParameters`
- `rxConfig`
- `signals`

Minimal shape:

```yaml
generationParameters:
  flagOutputIqSamples: true
  tot_time: 0.02
  outputFile: /tmp/testVirtualEngine

rxConfig:
  name: rx1
  rxSampleRate_Hz: 1.2288e8
  centerFreq_Hz: 2.45e9
  location: [0, 0, 0]

signals:
  - type: Bluetooth
    args:
      trafficType:
        type: periodic
        transmissionPerSec: 100
      centerFreq_Hz: 2.402e9
      txPower_db: -79
```

Notes:

- `auto_siggen` creates one default `Source` per signal.
- YAML synthetic output is one composite IQ file plus metadata.
- `trafficType` is usually `periodic` or `customArray`.

## Synthetic JSON

Use this with:

```bash
cd /Users/dineshb/repos/signal-processing/rfsynth
PYTHONPATH=/Users/dineshb/repos/signal-processing/rfsynth \
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  -m rfsynth.cli generate configs/synthetic_examples/ofdm_am_adjacent_simple.json --out /tmp/rfsynth_python_demo
```

or with:

```matlab
run_synthetic_json('configs/synthetic_examples/ofdm_am_adjacent_simple.json');
```

Two JSON shapes are supported.

### JSON Short Form

This is the recommended human-authored format.

Required top-level keys:

- `output`
- `rx`
- `signals`

Minimal shape:

```json
{
  "output": {
    "tot_time": 0.02,
    "outputBase": "scene_name"
  },
  "rx": {
    "sampleRate_Hz": 122880000.0,
    "centerFreq_Hz": 2450000000.0
  },
  "signals": [
    {
      "type": "Ofdm",
      "centerFreq_Hz": 2450000000.0,
      "transmissionRate_Hz": 10000000.0,
      "txPower_db": -66,
      "Nfft": 256,
      "modOrder": 16,
      "symbolTime_s": 2.56e-5,
      "cpTime_s": 1.6e-6,
      "transmissionTotTime": 0.004
    },
    {
      "type": "Am",
      "centerFreq_Hz": 2454132031.25,
      "transmissionRate_Hz": 1000000.0,
      "bandwidth_Hz": 100000.0,
      "txPower_db": -72,
      "modulationIndex": 0.8,
      "messageFreq_Hz": 5000.0,
      "transmissionTotTime": 0.004
    }
  ]
}
```

Defaults applied by [run_synthetic_json.m](/Users/dineshb/repos/signal-processing/rfsynth/matlab/examples/run_synthetic_json.m):

- `output.outputFolder = /tmp`
- `output.flagOutputIqSamples = true`
- `rx.name = rx1`
- `rx.location = [0, 0, 0]`
- every flat signal gets its own default source
- default source channel is `IDENTITY`
- default source impairments are zero
- if `trafficType` is omitted, it defaults to periodic at `100` transmissions per second

The Python-native loader in [scene.py](/Users/dineshb/repos/signal-processing/rfsynth/rfsynth/native/scene.py) applies the same practical defaults.

For `Ofdm`, `symbolTime_s` and `cpTime_s` are optional human-readable timing fields. The implementation derives them from `Nfft` and `transmissionRate_Hz`, and if you provide them they are checked for consistency.

### JSON Verbose Form

This is closer to the internal MATLAB object model.

Required top-level keys:

- `generationParameters`
- `rxConfig`
- either `signals` or `sources`

Minimal shape:

```json
{
  "generationParameters": {
    "tot_time": 0.02,
    "outputFolder": "/tmp",
    "outputBase": "atomic_qam"
  },
  "rxConfig": {
    "name": "rx1",
    "rxSampleRate_Hz": 122880000.0,
    "centerFreq_Hz": 2450000000.0,
    "location": [0, 0, 0]
  },
  "sources": [
    {
      "name": "Source1",
      "origin": "synthetic_atomic",
      "location": [0, 0, 0],
      "channelModel": "IDENTITY",
      "freqOffset_Hz": 0,
      "iqImbalance": [0, 0],
      "dcOffset": [0, 0],
      "signals": [
        {
          "type": "Qam",
          "args": {
            "trafficType": {
              "type": "periodic",
              "transmissionPerSec": 100
            },
            "centerFreq_Hz": 2466000000.0,
            "transmissionRate_Hz": 1000000.0,
            "txPower_db": -70,
            "samplesPerSymbol": 8,
            "modOrder": 16,
            "beta": 0.35,
            "span": 10,
            "transmissionTotTime": 0.004
          }
        }
      ]
    }
  ]
}
```

## Compressed YAML

Use this with:

```matlab
auto_compressed_siggen('matlab/examples/compressed_config.yml');
```

Required top-level keys:

- `generationParameters`
- `rxConfig`
- `txConfig`
- `signals`

Minimal shape:

```yaml
generationParameters:
  flagOutputIqSamples: true
  tot_time: 10
  outputFolder: /tmp
  filePrefix: test

rxConfig:
  name: rx1
  rxSampleRate_Hz: 1.2288e8
  centerFreq_Hz: 2.45e9
  location: [0, 0, 0]

txConfig:
  - name: tx1
    sampleRate_Hz: 1.2288e8
    location: [0, 0, 0]
    centerFreqRange_Hz: [100e6, 6e9]

signals:
  - type: Bluetooth
    args:
      trafficType:
        type: periodic
        transmissionPerSec: 100
      centerFreq_Hz: 2.402e9
      txPower_db: -79
```

This path generates replay-oriented artifacts, not one final composite synthetic IQ.

## Traffic

Supported traffic shapes used by these wrappers:

Periodic:

```json
{
  "type": "periodic",
  "transmissionPerSec": 100
}
```

Custom arrivals:

```json
{
  "type": "customArray",
  "arrivalArray": [0.002, 0.004, 0.008]
}
```

## Checker

Use the lightweight checker to validate config structure without running MATLAB:

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  /Users/dineshb/repos/signal-processing/rfsynth/scripts/check_configs.py \
  /Users/dineshb/repos/signal-processing/rfsynth/configs/synthetic_examples/ofdm_am_adjacent_simple.json
```

Check the bundled examples:

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  /Users/dineshb/repos/signal-processing/rfsynth/scripts/check_configs.py
```

What the checker does:

- parses JSON and YAML
- validates required top-level structure
- validates `rx` / `rxConfig`
- validates `signals` and `sources`
- validates `trafficType` when present
- validates `txConfig` for compressed YAML

What it does not do:

- it does not instantiate MATLAB classes
- it does not prove waveform-specific argument correctness
- it does not run synthetic generation
