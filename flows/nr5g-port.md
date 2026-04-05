# NR5G Port Flow

Use this flow to add and finish `nr5g` in the Python-native `rfsynth` path without confusing oracle templates with production completion.

## Target

Reference source:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/nr5g.m`

## Definition of done

For NR, "finished" means the production runtime synthesizes the waveform from parameters and logic.

These do not count as final completion:
- production loading of exported MATLAB waveform templates
- production loading of exported MATLAB grids
- production use of stored MATLAB waveform samples

Those are allowed only in compare, debug, or test harnesses.

## Phase 1

Direct narrow slice only:
- one `gridSize`
- one `subCarrierSpacing`
- `CP = Normal`
- one `numSubframes`
- one `modulation`
- one `waveformProfile`
- one public config, for example a narrow `control` profile at one center frequency

Acceptance:
- one direct runtime slice renders
- unsupported combinations fail clearly
- compare artifacts exist
- no production template dependence

## Phase 2

Direct matrix expansion:
- widen one knob at a time from the Phase 1 slice
- add matrix tooling only after a direct slice exists
- likely widening order:
  1. second center-frequency variant
  2. FR1 slice
  3. `PDSCH 16QAM`
  4. wider `numSubframes`
  5. further grid size or numerology work

Acceptance:
- widened runtime remains direct
- matrix tooling and matrix tests are green
- matrix compare coverage exists

## Phase 3

Finish NR:
- complete the intended NR parameter surface
- remove any remaining template-backed runtime behavior
- keep oracle templates only in compare/debug/tests

Acceptance:
- production runtime is fully parameter-driven for the declared NR surface
- compare coverage is sufficient for the widened surface
- regression suite remains green

## Current status rule

If any supported NR slice still depends on checked-in templates in the production runtime, NR is not finished.

Current repo status:
- the supported NR matrix surface is already direct in production runtime
- matrix tests enforce direct rendering across the generated NR matrix
- stored NR waveform/template assets remain compare/debug artifacts only

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create or update `rfsynth/native/atomic/nr5g.py`
- register it
- add `configs/synthetic_atomic/nr5g.json`
- add at least one basic render test
- prefer direct Python reconstruction of resource grid, OFDM, CP, and resample stages
- keep templates out of the production renderer

### 2. Oracle compare

Agent:
- `agents/oracle-compare.md`

Preferred compare path:
- `scene-behavioral` first for a direct slice
- then raw compare where exactness is realistic
- for wider coverage, use the NR matrix compare tooling

### 3. Parity debug

Agent:
- `agents/parity-debug.md`

Likely mismatch classes:
- numerology assumptions
- grid size and occupied bandwidth
- CP handling
- reference-signal placement
- symbol timing and burst boundaries
- normalization
- waveform profile mismatch
- hidden template dependence

### 4. Regression

Agent:
- `agents/regression.md`

Tasks:
- rerun public checks after the NR atomic is integrated
- run matrix tests when NR matrix tooling changed

## Final milestone

Call NR finished only when all of these are true:

- Phase 1 is complete
- Phase 2 is complete
- Phase 3 is complete
- the default runtime does not depend on checked-in oracle template assets

## Suggested Controller Prompt

Use this flow with:

- `agents/atomic-porter.md`
- `agents/oracle-compare.md`
- `agents/parity-debug.md`
- `agents/regression.md`

Suggested instruction:

`Advance NR toward Phase 3. Keep the production runtime direct and parameter-driven. Oracle templates or vectors may be used only in compare, debug, or tests. Use atomic-porter -> oracle-compare -> parity-debug -> regression, and do not mark NR finished until all three phases are satisfied.`
