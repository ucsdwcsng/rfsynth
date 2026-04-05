from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from rfsynth import render_synthetic


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")


class Nr5gMatrixToolingTest(unittest.TestCase):
    def test_nr5g_matrix_expansion_counts(self) -> None:
        script = REPO_ROOT / "scripts" / "generate_nr5g_matrix.py"
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", str(script), "--out", tmp],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(proc.stdout)
            self.assertEqual(summary["profile_count"], 4)
            self.assertEqual(summary["config_count"], 20)

            manifest = json.loads(Path(summary["manifest_path"]).read_text())
            self.assertEqual(len(manifest["profiles"]), 4)
            self.assertEqual(len(manifest["configs"]), 20)
            config_dir = Path(summary["config_dir"])
            configs = sorted(path.name for path in config_dir.glob("*.json"))
            self.assertEqual(len(configs), 20)
            self.assertIn("nr5g_3800mhz_control_1sf_qpsk.json", configs)
            self.assertIn("nr5g_3800mhz_pdsch_5sf_16qam.json", configs)
            self.assertIn("nr5g_2655mhz_fr1_control_3sf_qpsk.json", configs)

    def test_nr5g_matrix_configs_render_direct(self) -> None:
        script = REPO_ROOT / "scripts" / "generate_nr5g_matrix.py"
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", str(script), "--out", tmp],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(proc.stdout)
            config_dir = Path(summary["config_dir"])
            for cfg in sorted(config_dir.glob("*.json")):
                with tempfile.TemporaryDirectory() as out_dir:
                    bundle = render_synthetic(cfg, out_dir=out_dir)
                    metadata = json.loads(bundle.metadata_path.read_text())
                    self.assertEqual(metadata["sourceArray"][0]["signalArray"][0]["runtimeMode"], "direct", cfg.name)


if __name__ == "__main__":
    unittest.main()
