# LTE Port Flow

Use this flow to add one narrow `LTE_DL_FDD` preset to the Python-native `rfsynth` path in one controlled pass.

## Target

Reference source:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/LTE_DL_FDD.m`

Recommended one-shot subset:
- instance preset: `LTE_DL_FDD_763`
- `NDLRB = 6`
- `CP = Normal`
- `TotSubframes = 1`
- fixed `centerFreq_Hz = 763000000`
- `nPacket = 1`
- `idleTime = 0`
- one checked-in message vector path
- one oracle-backed exported waveform template
- one compare target only

This keeps the first milestone narrow: one LTE downlink preset that renders, compares, and survives regression.

Do not treat milestone 1 as “generic LTE support”.

Current recommended pattern:
- export one narrow LTE oracle from MATLAB
- check in the exact message vector used for that preset
- build one Python preset around the exported waveform template
- add one public config
- add one test
- close compare
- rerun regression

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create `rfsynth/native/atomic/lte_dl_fdd.py`
- register it in `rfsynth/native/atomic/__init__.py`
- add `configs/synthetic_atomic/lte_dl_fdd.json`
- add one render test in `tests/test_native_pipeline.py`
- if exact parity is needed quickly, export one narrow LTE template instead of approximating the full PHY on day one

Acceptance:
- the config renders through the Python-native engine
- metadata is emitted correctly
- the preset is still explicitly narrow, not a partial generic LTE implementation

### 2. Oracle compare

Agent:
- `agents/oracle-compare.md`

First compare mode:
- start with `scene-behavioral`

Then, only if explicit vectors or templates exist:
- move toward `atomic-exact`
- otherwise allow `near-exact`

Artifacts to inspect:
- `compare.json`
- time compare plot
- PSD compare plot
- spectrogram compare plot

Preferred first compare path:
- raw oracle-backed LTE burst compare using the checked-in message vector
- then scene-level compare

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
- message/vector mismatch
- preset mismatch such as bandwidth or subframe count

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

Call the one-shot LTE milestone complete when all of these are true:

- one narrow `LTE_DL_FDD` preset renders in Python
- one public config exists
- one raw oracle compare exists against MATLAB
- one scene compare exists against MATLAB
- regression suite remains green

## Current Extension Knobs

When you widen LTE after the first milestone, change only one of these at a time:

- instance preset
- `NDLRB`
- `TotSubframes`
- center frequency preset
- compare mode strictness

Do not widen more than one of those in the same first follow-up.

## Suggested Controller Prompt

Use this flow with:

- `agents/atomic-porter.md`
- `agents/oracle-compare.md`
- `agents/parity-debug.md`
- `agents/regression.md`

Suggested one-shot instruction:

`Use LTE_DL_FDD_763 only. Port one oracle-backed preset with NDLRB=6, TotSubframes=1, CP=Normal, centerFreq=763e6. Use atomic-porter -> oracle-compare -> parity-debug -> regression. Do not widen support until raw compare and scene compare are green.`
