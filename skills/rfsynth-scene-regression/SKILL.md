---
name: rfsynth-scene-regression
description: Run the public Python-native rfsynth synthetic regression suite across atomic and mixed-scene configs, collect render plus verify results, and flag any regressions before or after parity work.
---

# rfsynth Scene Regression

Use this skill when the task is to rerun the public Python-native synthetic suite and confirm that changes did not break the existing configs, plots, verification, or replay scaffolding.

## Scope

- Public atomic configs:
  - `configs/synthetic_atomic/*.json`
- Mixed-scene examples:
  - `configs/synthetic_examples/*.json`
- Main suite runner:
  - `scripts/run_python_native_suite.py`
- Config checker:
  - `scripts/check_configs.py`
- Unit tests:
  - `tests/test_native_pipeline.py`

## Default workflow

1. Validate configs first with `scripts/check_configs.py`.
2. Run the Python-native unit tests.
3. Run the synthetic suite with `scripts/run_python_native_suite.py`.
4. Read `python_native_suite_summary.json`.
5. Inspect any non-pass case directly in its output folder.
6. If the change was parity-related, optionally run the MATLAB compare loop after the Python regression is green.

## Recommended commands

Config check:

```bash
python3 scripts/check_configs.py
```

Unit tests:

```bash
python3 -m unittest tests.test_native_pipeline
```

Public regression sweep:

```bash
python3 scripts/run_python_native_suite.py \
  --out /tmp/rfsynth_python_native_suite
```

## Expected outputs

The suite writes one bundle per config plus:

- `/tmp/rfsynth_python_native_suite/python_native_suite_summary.json`

Each bundle should contain:

- `.32cf`
- `.json`
- `_scoring.json`
- plotting outputs
- `verify.json`

## Interpretation rules

- `DummySignal` is expected to be special because it is intentionally silent.
- For real waveforms, the target is `Visual pass`.
- If a config regresses from `Visual pass` to `Inconclusive` or `Visual fail`, treat that as a real regression until explained.

## When to add MATLAB

If the user asks for parity or if a regression looks suspicious, follow this skill with:
- `rfsynth-matlab-oracle-compare`

## Answer format

Return:
- whether config validation passed
- whether unit tests passed
- how many configs were swept
- which configs failed or became inconclusive
- where the suite summary and artifacts were written
