---
name: rfsynth-synthetic-test
description: Run synthetic-only MATLAB validation for the rfsynth repository, sweep synthetic YAML configs, generate .32cf plus metadata artifacts, and avoid the compressed or OTA paths.
---

# rfsynth Synthetic Test

Use this skill when the task is to validate synthetic generation in `/Users/dineshb/repos/signal-processing/rfsynth` and create IQ artifacts locally. This skill is only for the MATLAB synthetic path. Do not invoke compressed generation, GNU Radio, UHD, or OTA replay.

## Scope

- Repo root: `/Users/dineshb/repos/signal-processing/rfsynth`
- MATLAB code root: `matlab/`
- Synthetic configs: `matlab/examples/*.yml`
- Skip `matlab/examples/compressed_config.yml` unless the user explicitly asks for compressed generation

## Default workflow

1. Work from the repo root.
2. Run MATLAB in headless batch mode.
3. Use `restoredefaultpath`, then add only this repo's MATLAB library path:
   `cd('/Users/dineshb/repos/signal-processing/rfsynth/matlab'); addpath(genpath(fullfile(pwd,'lib')));`
4. Load the YAML config with:
   `cfg = yaml.loadFile(fullfile(pwd,'examples','config.yml'),'ConvertToArray',true);`
5. Build the synthetic scene programmatically:
   - construct `atomic.Rx`
   - construct one `atomic.Source` per configured signal
   - instantiate the signal with `feval(char("atomic." + s.type), namedargs2cell(s.args){:})`
   - add each signal to its source
   - add each source to `VirtualSignalEngine`
6. Generate IQ with:
   `samplesIQ = sigGen.generateSamples(0, cfg.generationParameters.tot_time, cfg.generationParameters.flagOutputIqSamples);`
7. Generate metadata with:
   `metadataStr = sigGen.getMetadataJson();`
8. Write artifacts explicitly:
   - IQ: `write_complex_binary(samplesIQ, '/tmp/<base>.32cf')`
   - metadata: write `metadataStr` to `/tmp/<base>.json`
9. Validate at minimum:
   - sample array is non-empty
   - metadata decodes cleanly
   - metadata `sourceArray` count matches the number of configured signals
10. Report:
   - config used
   - sample count
   - output file paths
   - any MATLAB warnings that did not stop execution

## Important guardrails

- Prefer the programmatic headless path over `matlab/examples/auto_siggen.m`.
- `auto_siggen.m` mixes plotting with generation and is not the best automation entrypoint.
- Do not rely on OTA or Python wrappers for this skill.
- User-level MATLAB startup scripts may emit unrelated warnings. Treat them as noise if MATLAB still exits `0` and the artifacts are created.

## Config sweep rule

If asked to run "all configs", sweep all synthetic YAML configs under `matlab/examples/` and exclude compressed or OTA-related inputs unless the user explicitly says otherwise.

In the current repo, that usually means:
- include `matlab/examples/config.yml`
- exclude `matlab/examples/compressed_config.yml`

## Expected outputs

For a smoke test, write artifacts to `/tmp` with a stable prefix such as:
- `/tmp/rfsynth_synth_smoke.32cf`
- `/tmp/rfsynth_synth_smoke.json`

## Answer format

Keep the response short and concrete:
- whether synthetic generation passed
- what config was used
- what files were created
- the sample count
- what was intentionally not tested
