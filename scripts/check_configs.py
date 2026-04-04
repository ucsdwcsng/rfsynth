#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")
DEFAULT_PATHS = [
    REPO_ROOT / "matlab" / "examples" / "config.yml",
    REPO_ROOT / "matlab" / "examples" / "compressed_config.yml",
    REPO_ROOT / "configs" / "synthetic_atomic",
    REPO_ROOT / "configs" / "synthetic_examples",
]


@dataclass
class ValidationResult:
    path: str
    mode: str
    ok: bool
    errors: list[str]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Files or directories to validate")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    targets = [Path(p) for p in args.paths] if args.paths else DEFAULT_PATHS
    files = expand_targets(targets)
    results = [validate_file(path) for path in files]

    if args.json:
        print(
            json.dumps(
                {
                    "results": [
                        {
                            "path": r.path,
                            "mode": r.mode,
                            "ok": r.ok,
                            "errors": r.errors,
                        }
                        for r in results
                    ]
                },
                indent=2,
            )
        )
    else:
        for result in results:
            status = "PASS" if result.ok else "FAIL"
            print(f"{status} {result.path} [{result.mode}]")
            for error in result.errors:
                print(f"  - {error}")

    return 0 if all(r.ok for r in results) else 1


def expand_targets(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            for child in sorted(target.iterdir()):
                if child.suffix.lower() in {".json", ".yml", ".yaml"}:
                    files.append(child)
        else:
            files.append(target)
    return files


def validate_file(path: Path) -> ValidationResult:
    try:
        cfg = load_config(path)
        errors = validate_config(cfg, path)
        mode = detect_mode(cfg, path)
        return ValidationResult(str(path), mode, not errors, errors)
    except Exception as exc:
        return ValidationResult(str(path), "unparsed", False, [str(exc)])


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text()
    suffix = path.suffix.lower()
    if suffix == ".json":
        cfg = json.loads(text)
    elif suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("PyYAML is required to validate YAML files") from exc
        cfg = yaml.safe_load(text)
    else:
        raise RuntimeError(f"Unsupported config extension: {path.suffix}")

    if not isinstance(cfg, dict):
        raise RuntimeError("Top-level config must be a mapping/object")
    return cfg


def detect_mode(cfg: dict[str, Any], path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        return "compressed-yaml" if "txConfig" in cfg else "synthetic-yaml"
    if "output" in cfg or "rx" in cfg:
        return "synthetic-json-short"
    if "txConfig" in cfg:
        return "compressed-json"
    return "synthetic-json-verbose"


def validate_config(cfg: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    mode = detect_mode(cfg, path)

    if mode == "synthetic-yaml":
        require_mapping(cfg, "generationParameters", errors)
        require_mapping(cfg, "rxConfig", errors)
        require_listlike(cfg, "signals", errors)
        validate_generation_parameters(cfg.get("generationParameters"), yaml_mode=True, compressed=False, errors=errors)
        validate_rx_config(cfg.get("rxConfig"), errors)
        validate_signals_list(cfg.get("signals"), allow_flat=False, errors=errors)
    elif mode == "compressed-yaml":
        require_mapping(cfg, "generationParameters", errors)
        require_mapping(cfg, "rxConfig", errors)
        require_listlike(cfg, "signals", errors)
        require_listlike(cfg, "txConfig", errors)
        validate_generation_parameters(cfg.get("generationParameters"), yaml_mode=True, compressed=True, errors=errors)
        validate_rx_config(cfg.get("rxConfig"), errors)
        validate_tx_config(cfg.get("txConfig"), errors)
        validate_signals_list(cfg.get("signals"), allow_flat=False, errors=errors)
    elif mode == "synthetic-json-short":
        require_mapping(cfg, "output", errors)
        require_mapping(cfg, "rx", errors)
        require_listlike(cfg, "signals", errors)
        validate_output_block(cfg.get("output"), errors)
        validate_rx_short(cfg.get("rx"), errors)
        validate_signals_list(cfg.get("signals"), allow_flat=True, errors=errors)
    else:
        require_mapping(cfg, "generationParameters", errors)
        require_mapping(cfg, "rxConfig", errors)
        if "signals" not in cfg and "sources" not in cfg:
            errors.append("config must define either signals or sources")
        validate_generation_parameters(cfg.get("generationParameters"), yaml_mode=False, compressed=False, errors=errors)
        validate_rx_config(cfg.get("rxConfig"), errors)
        if "signals" in cfg:
            validate_signals_list(cfg.get("signals"), allow_flat=False, errors=errors)
        if "sources" in cfg:
            validate_sources(cfg.get("sources"), errors)

    return errors


def require_mapping(cfg: dict[str, Any], key: str, errors: list[str]) -> None:
    value = cfg.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object/mapping")


def require_listlike(cfg: dict[str, Any], key: str, errors: list[str]) -> None:
    value = cfg.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be a list/array")


def validate_generation_parameters(
    generation_parameters: Any,
    *,
    yaml_mode: bool,
    compressed: bool,
    errors: list[str],
) -> None:
    if not isinstance(generation_parameters, dict):
        return
    if "tot_time" not in generation_parameters:
        errors.append("generationParameters.tot_time is required")
    if yaml_mode and compressed:
        if "outputFolder" not in generation_parameters:
            errors.append("generationParameters.outputFolder is required for compressed YAML")
        if "filePrefix" not in generation_parameters:
            errors.append("generationParameters.filePrefix is required for compressed YAML")
    elif yaml_mode:
        if "outputFile" not in generation_parameters:
            errors.append("generationParameters.outputFile is required for synthetic YAML")


def validate_output_block(output_cfg: Any, errors: list[str]) -> None:
    if not isinstance(output_cfg, dict):
        return
    if "tot_time" not in output_cfg:
        errors.append("output.tot_time is required")


def validate_rx_config(rx_cfg: Any, errors: list[str]) -> None:
    if not isinstance(rx_cfg, dict):
        return
    for key in ("name", "rxSampleRate_Hz", "centerFreq_Hz", "location"):
        if key not in rx_cfg:
            errors.append(f"rxConfig.{key} is required")


def validate_rx_short(rx_cfg: Any, errors: list[str]) -> None:
    if not isinstance(rx_cfg, dict):
        return
    for key in ("sampleRate_Hz", "centerFreq_Hz"):
        if key not in rx_cfg:
            errors.append(f"rx.{key} is required")


def validate_sources(sources: Any, errors: list[str]) -> None:
    if not isinstance(sources, list):
        errors.append("sources must be a list/array")
        return
    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{idx}] must be an object")
            continue
        signals = source.get("signals")
        if signals is None:
            errors.append(f"sources[{idx}].signals is required")
            continue
        validate_signals_list(signals, allow_flat=False, errors=errors, prefix=f"sources[{idx}].signals")


def validate_tx_config(tx_cfg: Any, errors: list[str]) -> None:
    if not isinstance(tx_cfg, list):
        return
    for idx, tx in enumerate(tx_cfg):
        if not isinstance(tx, dict):
            errors.append(f"txConfig[{idx}] must be an object")
            continue
        for key in ("sampleRate_Hz", "location", "centerFreqRange_Hz"):
            if key not in tx:
                errors.append(f"txConfig[{idx}].{key} is required")


def validate_signals_list(signals: Any, *, allow_flat: bool, errors: list[str], prefix: str = "signals") -> None:
    if not isinstance(signals, list):
        errors.append(f"{prefix} must be a list/array")
        return
    for idx, signal in enumerate(signals):
        validate_signal(signal, allow_flat=allow_flat, errors=errors, prefix=f"{prefix}[{idx}]")


def validate_signal(signal: Any, *, allow_flat: bool, errors: list[str], prefix: str) -> None:
    if not isinstance(signal, dict):
        errors.append(f"{prefix} must be an object")
        return
    if "type" not in signal:
        errors.append(f"{prefix}.type is required")
        return

    args = signal.get("args")
    if args is not None:
        if not isinstance(args, dict):
            errors.append(f"{prefix}.args must be an object")
            return
        signal_args = args
    elif allow_flat:
        signal_args = {k: v for k, v in signal.items() if k != "type"}
    else:
        signal_args = {}

    traffic = signal_args.get("trafficType")
    if traffic is not None:
        validate_traffic(traffic, errors, prefix=f"{prefix}.trafficType")


def validate_traffic(traffic: Any, errors: list[str], prefix: str) -> None:
    if not isinstance(traffic, dict):
        errors.append(f"{prefix} must be an object")
        return
    traffic_type = traffic.get("type")
    if traffic_type is None:
        errors.append(f"{prefix}.type is required")
        return
    if traffic_type == "periodic" and "transmissionPerSec" not in traffic:
        errors.append(f"{prefix}.transmissionPerSec is required for periodic traffic")
    if traffic_type == "customArray" and "arrivalArray" not in traffic:
        errors.append(f"{prefix}.arrivalArray is required for customArray traffic")


if __name__ == "__main__":
    raise SystemExit(main())
