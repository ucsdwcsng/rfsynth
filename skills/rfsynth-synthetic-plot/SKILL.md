---
name: rfsynth-synthetic-plot
description: Plot rfsynth synthetic IQ artifacts from .32cf plus metadata JSON, generating full-band spectrograms, PSDs, time-domain views, and metadata occupancy plots.
---

# rfsynth Synthetic Plot

Use this skill when the task is to visualize a synthetic `rfsynth` IQ file and its metadata. Inputs are typically:

- `/tmp/<base>.32cf`
- `/tmp/<base>.json`

This skill is for visualization only. It does not regenerate IQ.

## Default workflow

1. Read the metadata JSON first.
2. Extract:
   - `sampleRate_Hz`
   - `freqCenter_Hz`
   - signal-level boxes from `requiredMetadata`
   - energy-level boxes from each signal's `transmissionArray`
3. Read the IQ as `complex64`.
4. Generate these plots by default:
   - time-domain view of the first 1-2 ms
   - PSD over the full capture
   - full-band spectrogram
   - metadata-only occupancy plot
5. Save plots to `/tmp/<base>_*.png`.

## Python environment

Prefer a Python environment that already has `numpy`, `scipy`, and `matplotlib`.

In this workspace, prefer:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python`

Set a writable Matplotlib config dir when needed:
- `MPLCONFIGDIR=/tmp/mpl-rfsynth`

## Plotting rules

- Always start with a full-band spectrogram spanning `[-fs/2, +fs/2]` around the center frequency.
- Only make zoomed or decimated plots after the full-band view exists.
- If you decimate for readability, say so clearly and explain the new displayed span.
- Never present a narrow-band decimated spectrogram as if it were the full synthetic bandwidth.

## Overlay conventions

Use consistent overlays:
- signal boxes: cyan dashed rectangles
- energy boxes: yellow solid rectangles
- metadata-only occupancy: lightly filled signal boxes plus outlined energy boxes

## Default outputs

Recommended output set:
- `/tmp/<base>_time.png`
- `/tmp/<base>_psd.png`
- `/tmp/<base>_spectrogram.png`
- `/tmp/<base>_occupancy.png`

## Interpretation guidance

When summarizing plots:
- state the RF center frequency
- state the displayed bandwidth
- call out the expected offsets of visible signals
- say whether the spectrogram and metadata boxes visually align

## Answer format

Return:
- the generated image paths
- one short paragraph on what the plots show
- any plotting caveat, especially if decimation or frequency shifting was used
