# LTE Port Flow

Use this flow to add `LTE_DL_FDD` to the Python-native `rfsynth` path with controlled scope.

## Target

Reference source:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/LTE_DL_FDD.m`

Recommended first supported subset:
- `NDLRB = 6`
- `CP = Normal`
- `TotSubframes = 10`
- `modulation = QPSK`
- one fixed center frequency
- one explicit message vector path for compare work

This keeps the first milestone narrow: one LTE downlink preset that renders and compares correctly.

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create `rfsynth/native/atomic/lte_dl_fdd.py`
- register it in `rfsynth/native/atomic/__init__.py`
- add `configs/synthetic_atomic/lte_dl_fdd.json`
- add one render test in `tests/test_native_pipeline.py`

Acceptance:
- the config renders through the Python-native engine
- metadata is emitted correctly

### 2. Oracle compare

Agent:
- `agents/oracle-compare.md`

First compare mode:
- start with `scene-behavioral`

Then, if possible:
- add explicit message-vector support and move toward `atomic-exact`

Artifacts to inspect:
- `compare.json`
- time compare plot
- PSD compare plot
- spectrogram compare plot

### 3. Parity debug

Agent:
- `agents/parity-debug.md`

Likely mismatch classes for LTE:
- resource-grid mapping
- control/data placement
- reference signals
- cyclic prefix handling
- OFDM symbol ordering
- normalization or windowing

Acceptance:
- exact or near-exact parity if explicit vectors are available
- otherwise behavioral parity with clear explanation

### 4. Regression

Agent:
- `agents/regression.md`

Tasks:
- run config checks
- run unit tests
- run the public synthetic suite

Acceptance:
- no regressions in existing public configs

## Final milestone

Call the first LTE milestone complete when all of these are true:

- `LTE_DL_FDD` renders in Python
- one public config exists
- at least one compare path exists against MATLAB
- regression suite remains green
