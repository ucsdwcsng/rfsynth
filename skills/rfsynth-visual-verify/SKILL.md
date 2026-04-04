---
name: rfsynth-visual-verify
description: Verify that synthetic rfsynth energy appears only where metadata says it should, using full-band spectrogram overlays of signal boxes and energy boxes plus a concise pass/fail analysis.
---

# rfsynth Visual Verify

Use this skill when the task is to visually verify that synthetic IQ energy lines up with metadata and does not appear in unexpected time/frequency regions.

Inputs are typically:
- `/tmp/<base>.32cf`
- `/tmp/<base>.json`

## Verification goal

Answer this question:

`Does the observed energy in the synthetic spectrogram stay within the expected metadata boxes, and are the metadata boxes visibly supported by energy in the IQ?`

## Required workflow

1. Parse the metadata into two layers:
   - signal boxes from `requiredMetadata`
   - energy boxes from each `transmissionArray`
2. Build a full-band spectrogram over the actual synthetic bandwidth.
3. Overlay:
   - signal boxes in one style
   - energy boxes in another style
4. Generate a metadata-only occupancy view on the same axes.
5. Compare the IQ and metadata visually before making any claim.

## Verification rules

- Full-band first. Do not verify from a narrow-band or heavily decimated plot alone.
- Distinguish signal-level boxes from energy-level boxes.
- Treat noise floor and ordinary spectral leakage as expected.
- Flag only material mismatches:
  - clear energy outside all metadata boxes
  - metadata boxes with no visible corresponding energy
  - timing or bandwidth mismatches that are large enough to matter

## Common failure mode

Do not confuse plotting loss with signal loss.

If a spectrogram only shows `+/- 5 MHz` or `+/- 10 MHz` while the capture bandwidth is much larger, the plot is incomplete unless the IQ was intentionally frequency-shifted and bandwidth-limited first.

## Expected outputs

Produce at least:
- `/tmp/<base>_fullband_overlay.png`
- `/tmp/<base>_fullband_occupancy.png`

## Expected findings structure

State:
- total signal box count
- total energy box count
- whether energy is visibly confined to expected regions
- whether any expected region appears empty
- whether the result is a visual pass, visual fail, or visually inconclusive

## Pass criteria

Call it a visual pass only if:
- the visible energy is inside or very close to the expected metadata regions
- no major out-of-box energy stands out
- each configured signal family has visible support in the spectrogram

## Answer format

Keep the result direct:
- `Visual pass`, `Visual fail`, or `Inconclusive`
- 2-4 bullets of evidence
- image paths used for the conclusion
