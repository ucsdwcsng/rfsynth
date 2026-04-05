# NR5G Port Flow

Use this flow to add `nr5g` to the Python-native `rfsynth` path without trying to solve all 5G variants at once.

## Target

Reference source:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/nr5g.m`

Recommended first supported subset:
- one instance preset such as `nr5g77` or `FR1`
- one `subCarrierSpacing`
- one `NDLRB`
- `CP = Normal`
- one `TotSubframes`
- one `modulation`

The point is to close one narrow NR waveform first, not all bands and numerologies.

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create `rfsynth/native/atomic/nr5g.py`
- register it
- add `configs/synthetic_atomic/nr5g.json`
- add one basic render test

Good first target:
- one FR1-style preset
- fixed grid size
- fixed subcarrier spacing
- QPSK first

Acceptance:
- the Python-native engine renders a non-empty burst and emits metadata

### 2. Oracle compare

Agent:
- `agents/oracle-compare.md`

First compare mode:
- `scene-behavioral`

Move to stricter compare only after the narrow preset is stable.

For NR, expect exact parity to require more explicit control over:
- payload bits
- grid mapping
- reference signals
- symbol scheduling

### 3. Parity debug

Agent:
- `agents/parity-debug.md`

Likely mismatch classes for NR:
- numerology assumptions
- grid size and occupied bandwidth
- CP handling
- reference-signal placement
- symbol timing and burst boundaries
- normalization

Acceptance:
- one preset reaches acceptable parity

### 4. Regression

Agent:
- `agents/regression.md`

Tasks:
- rerun public checks after the NR atomic is integrated

Acceptance:
- no regressions in current public scenes

## Final milestone

Call the first NR milestone complete when all of these are true:

- one narrow `nr5g` preset renders in Python
- one public config exists
- MATLAB compare artifacts exist
- regression suite remains green
