from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")


class LteMatrixToolingTest(unittest.TestCase):
    def test_lte_matrix_expansion_counts(self) -> None:
        script = REPO_ROOT / "scripts" / "generate_lte_dl_fdd_matrix.py"
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", str(script), "--out", tmp],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(proc.stdout)
            self.assertEqual(summary["profile_count"], 48)
            self.assertEqual(summary["config_count"], 96)
            self.assertEqual(summary["runtime_manifest_path"], summary["manifest_path"])

            manifest = json.loads(Path(summary["manifest_path"]).read_text())
            self.assertEqual(len(manifest["profiles"]), 48)
            self.assertIn("profile_dir", manifest)
            config_dir = Path(summary["config_dir"])
            self.assertEqual(len(list(config_dir.glob("*.json"))), 96)


if __name__ == "__main__":
    unittest.main()
