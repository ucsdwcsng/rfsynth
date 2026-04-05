from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from rfsynth import Scene, Signal, Source, Traffic, VirtualSignalEngine, compile_replay, load_scene, plot_artifacts, render_synthetic, run_replay, verify_artifacts
from rfsynth.native.waveforms import compute_transmission_windows


REPO_ROOT = Path("/Users/dineshb/repos/signal-processing/rfsynth")


class NativePipelineTest(unittest.TestCase):
    def test_short_scene_pipeline(self) -> None:
        scene_path = REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent_simple.json"
        with tempfile.TemporaryDirectory() as tmp:
            bundle = render_synthetic(scene_path, out_dir=tmp)
            self.assertTrue(bundle.iq_path.exists())
            self.assertTrue(bundle.metadata_path.exists())
            self.assertTrue(bundle.scoring_path.exists())

            plots = plot_artifacts(bundle)
            self.assertIn("fullband_overlay", plots.paths)
            self.assertTrue(plots.paths["fullband_overlay"].exists())

            verify = verify_artifacts(bundle)
            self.assertEqual(verify["verdict"], "Visual pass")

            plan = compile_replay(bundle)
            self.assertEqual(len(plan.events), 4)
            run = run_replay(plan, backend="sim", out_dir=tmp)
            self.assertTrue(run.output_path.exists())

    def test_public_atomic_subset(self) -> None:
        subset = [
            "am.json",
            "bluetooth.json",
            "nr5g.json",
            "ofdm.json",
            "wlan_nonht80211g.json",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for name in subset:
                bundle = render_synthetic(REPO_ROOT / "configs" / "synthetic_atomic" / name, out_dir=tmp)
                verify = verify_artifacts(bundle)
                self.assertIn(verify["verdict"], {"Visual pass", "Inconclusive"})

    def test_short_and_verbose_configs_normalize_to_same_scene_shape(self) -> None:
        short_scene = load_scene(REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent_simple.json")
        verbose_scene = load_scene(REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent.json")
        self.assertEqual(short_scene.generation.total_time_s, verbose_scene.generation.total_time_s)
        self.assertEqual(short_scene.rx.sample_rate_hz, verbose_scene.rx.sample_rate_hz)
        self.assertEqual(len(short_scene.sources), 2)
        self.assertEqual(len(verbose_scene.sources), 2)
        self.assertEqual(sum(len(source.signals) for source in short_scene.sources), 2)
        self.assertEqual(sum(len(source.signals) for source in verbose_scene.sources), 2)

    def test_custom_array_traffic_expands_exact_arrivals(self) -> None:
        scene = load_scene(
            {
                "output": {"tot_time": 0.02, "outputBase": "custom_traffic"},
                "rx": {"sampleRate_Hz": 1_000_000.0, "centerFreq_Hz": 2.45e9},
                "signals": [
                    {
                        "type": "Sine",
                        "centerFreq_Hz": 2.45e9,
                        "bandwidth_Hz": 100_000.0,
                        "transmissionRate_Hz": 1_000_000.0,
                        "transmissionTotTime": 0.001,
                        "trafficType": {"type": "customArray", "arrivalArray": [0.001, 0.004, 0.009]},
                    }
                ],
            }
        )
        windows = compute_transmission_windows(scene.sources[0].signals[0], scene)
        self.assertEqual([round(window.start_time, 6) for window in windows], [0.001, 0.004, 0.009])
        self.assertEqual([round(window.stop_time, 6) for window in windows], [0.002, 0.005, 0.01])

    def test_replay_plan_is_time_sorted(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent_simple.json")
        with tempfile.TemporaryDirectory() as tmp:
            bundle = render_synthetic(scene, out_dir=tmp)
            plan = compile_replay(bundle)
            starts = [event.time_start for event in plan.events]
            self.assertEqual(starts, sorted(starts))
            self.assertEqual(plan.scene_id, bundle.base_path.name)

    def test_load_scene_returns_runtime_object_graph(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent_simple.json")
        self.assertIsInstance(scene, Scene)
        self.assertIsInstance(scene.sources[0], Source)
        self.assertIsInstance(scene.sources[0].signals[0], Signal)
        self.assertIsInstance(scene.sources[0].signals[0].traffic, Traffic)
        self.assertEqual(scene.sources[0].signals[0].source, scene.sources[0])

    def test_virtual_signal_engine_matches_scene_signal_count(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_examples" / "ofdm_am_adjacent_simple.json")
        engine = VirtualSignalEngine(scene)
        iq, rendered = engine.generate_samples(seed=1234)
        self.assertGreater(len(iq), 0)
        self.assertEqual(len(rendered), sum(len(source.signals) for source in scene.sources))

    def test_wlan_nonht_all_mcs_render(self) -> None:
        base_cfg = json.loads((REPO_ROOT / "configs" / "synthetic_atomic" / "wlan_nonht80211g.json").read_text())
        sample_counts: list[int] = []
        for mcs in range(8):
            cfg = json.loads(json.dumps(base_cfg))
            args = cfg["sources"][0]["signals"][0].setdefault("args", {})
            args["mcs"] = mcs
            args["psduLength"] = 66
            scene = load_scene(cfg)
            signal = scene.sources[0].signals[0]
            burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
            self.assertGreater(len(burst.samples), 0)
            self.assertEqual(burst.sample_rate_hz, 20e6)
            self.assertEqual(burst.extras["mcs"], mcs)
            sample_counts.append(len(burst.samples))
        self.assertEqual(sample_counts, sorted(sample_counts, reverse=True))
        self.assertEqual(sample_counts, [2240, 1680, 1360, 1040, 880, 720, 640, 640])

    def test_bluetooth_parameter_surface_render(self) -> None:
        base_cfg = json.loads((REPO_ROOT / "configs" / "synthetic_atomic" / "bluetooth.json").read_text())

        def cte_msg(kind: str) -> list[int]:
            bits = [0] * 64
            if kind == "ConnectionCTE":
                bits[16:21] = [0, 1, 0, 0, 0]
                bits[22:24] = [0, 0]
            else:
                bits[32:37] = [0, 1, 0, 0, 0]
                bits[38:40] = [0, 0]
            return bits

        cases = [
            ({"mode": "LE1M"}, 8e6),
            ({"mode": "LE2M"}, 16e6),
            ({"mode": "LE500K"}, 8e6),
            ({"mode": "LE125K"}, 8e6),
            ({"WhitenStatus": "On", "channelIndex": 0}, 8e6),
            ({"modulationIndex": 0.45}, 8e6),
            ({"modulationIndex": 0.55}, 8e6),
            ({"pulseLength": 4}, 8e6),
            ({"samplesPerSymbol": 4}, 4e6),
            ({"DFPacketType": "ConnectionCTE", "message": cte_msg("ConnectionCTE")}, 8e6),
            ({"mode": "LE2M", "DFPacketType": "ConnectionCTE", "message": cte_msg("ConnectionCTE")}, 16e6),
            ({"DFPacketType": "ConnectionlessCTE", "message": cte_msg("ConnectionlessCTE")}, 8e6),
        ]
        for updates, expected_rate in cases:
            cfg = json.loads(json.dumps(base_cfg))
            args = cfg["sources"][0]["signals"][0].setdefault("args", {})
            args.update(updates)
            scene = load_scene(cfg)
            signal = scene.sources[0].signals[0]
            burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
            self.assertGreater(len(burst.samples), 0)
            self.assertEqual(burst.sample_rate_hz, expected_rate)
            self.assertEqual(burst.extras["mode"], args.get("mode", "LE1M"))

    def test_nr5g_narrow_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "nr5g.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 40000)
        self.assertEqual(burst.sample_rate_hz, 40e6)
        self.assertEqual(burst.bandwidth_hz, 10e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.modality, "multi_carrier")
        self.assertEqual(burst.extras["family"], "nr5g")
        self.assertEqual(burst.extras["subCarrierSpacing_kHz"], 15.0)
        self.assertEqual(burst.extras["numSubframes"], 1)


if __name__ == "__main__":
    unittest.main()
