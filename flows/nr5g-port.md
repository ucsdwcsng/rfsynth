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
- one `waveformProfile`

The point is to close one narrow NR waveform first, not all bands and numerologies.

Current working pattern in this repo:
- direct Python reconstruction for simple narrow control-style presets
- oracle-backed grid templates for exact narrow presets

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create `rfsynth/native/atomic/nr5g.py`
- register it
- add `configs/synthetic_atomic/nr5g.json`
- add one basic render test
- if exact parity is needed quickly, export one narrow MATLAB template instead of approximating the full PHY

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
- waveform profile selection

Preferred exact-parity shortcut:
- export one narrow template with `matlab/lib/utils/exportNr5gTemplate.m`
- load that template in Python as one oracle-backed profile

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
- waveform profile mismatch such as `control` vs `pdsch`

Acceptance:
- one preset reaches acceptable parity

Current proved sequence:
1. narrow control-style preset
2. second center-frequency variant
3. FR1 oracle-backed preset
4. `PDSCH 16QAM` oracle-backed preset

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

## Current Extension Knobs

When you modify this flow for the next NR step, pick only one of:

- new `waveformProfile`
- new `modulation`
- new `gridSize`
- new center-frequency preset
- new numerology

Do not widen more than one of those in the same first pass.

## How To Modify This Flow

Edit this flow when NR support widens.

Common next edits:
- change the first target preset
- add a new `waveformProfile`
- tighten the compare mode from `scene-behavioral` to `near-exact` or `atomic-exact`
- add a second milestone after the first preset is green, for example:
  - `FR1`
  - `PDSCH 16QAM`
  - a second numerology
