from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from rfsynth import Scene, Signal, Source, Traffic, VirtualSignalEngine, compile_replay, load_scene, plot_artifacts, render_synthetic, run_replay, verify_artifacts
from rfsynth.native.atomic.lte_dl_fdd import (
    _lte_code_block_segment,
    _lte_crc_attach,
    _lte_default_dci_bits,
    _lte_dlsch_encode_transport_block,
    _lte_dlsch_info,
    _lte_dlsch_rate_match_lengths,
    _lte_expected_payload_bits,
    _lte_message_bits,
    _lte_pdcch_candidate_starts,
    _lte_pdcch_n_cce,
    _lte_pdcch_prbs,
    _lte_pdsch_scramble,
    _lte_phich_rows,
    _lte_phich_symbols,
    _lte_qpp_interleaver_indices,
    _lte_qpp_interleaver_params,
    _lte_rate_match_turbo_block,
    _lte_sync_symbol_indices,
    _lte_transport_stream_window,
    _lte_turbo_encode_block,
    _lte_transport_block_bits_total,
)
from rfsynth.native.atomic.nr5g_template import symbol_phase_sequence
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
            "lte_dl_fdd.json",
            "lte_dl_fdd_2600.json",
            "lte_dl_fdd_100rb.json",
            "lte_dl_fdd_75rb.json",
            "lte_dl_fdd_50rb.json",
            "lte_dl_fdd_25rb.json",
            "lte_dl_fdd_16qam.json",
            "lte_dl_fdd_extcp.json",
            "lte_dl_fdd_5sf.json",
            "lte_dl_fdd_15rb.json",
            "nr5g.json",
            "nr5g78.json",
            "nr5g_fr1.json",
            "nr5g_pdsch_16qam.json",
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

    def test_lte_dl_fdd_direct_phase1_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 1920)
        self.assertEqual(burst.sample_rate_hz, 1.92e6)
        self.assertEqual(burst.bandwidth_hz, 1.4e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 6)
        self.assertEqual(burst.extras["TotSubframes"], 1)

    def test_lte_dl_fdd_2600_direct_phase1_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_2600.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 1920)
        self.assertEqual(burst.sample_rate_hz, 1.92e6)
        self.assertEqual(burst.bandwidth_hz, 1.4e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 6)
        self.assertEqual(burst.extras["TotSubframes"], 1)
        self.assertEqual(burst.extras["centerFreq_Hz"], 2.655e9)

    def test_lte_dl_fdd_ndlrb50_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_50rb.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 15360)
        self.assertEqual(burst.sample_rate_hz, 15.36e6)
        self.assertEqual(burst.bandwidth_hz, 10.0e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 50)
        self.assertEqual(burst.extras["TotSubframes"], 1)

    def test_lte_dl_fdd_ndlrb75_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_75rb.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 23040)
        self.assertEqual(burst.sample_rate_hz, 23.04e6)
        self.assertEqual(burst.bandwidth_hz, 15.0e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 75)
        self.assertEqual(burst.extras["TotSubframes"], 1)

    def test_lte_dl_fdd_ndlrb100_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_100rb.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 30720)
        self.assertEqual(burst.sample_rate_hz, 30.72e6)
        self.assertEqual(burst.bandwidth_hz, 20.0e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 100)
        self.assertEqual(burst.extras["TotSubframes"], 1)

    def test_lte_dl_fdd_ndlrb25_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_25rb.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 7680)
        self.assertEqual(burst.sample_rate_hz, 7.68e6)
        self.assertEqual(burst.bandwidth_hz, 5.0e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 25)
        self.assertEqual(burst.extras["TotSubframes"], 1)

    def test_lte_dl_fdd_16qam_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_16qam.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 1920)
        self.assertEqual(burst.sample_rate_hz, 1.92e6)
        self.assertEqual(burst.bandwidth_hz, 1.4e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 6)
        self.assertEqual(burst.extras["TotSubframes"], 1)
        self.assertEqual(burst.extras["modulation"], "16QAM")

    def test_lte_transport_helpers_match_known_36212_entries(self) -> None:
        self.assertEqual(_lte_qpp_interleaver_params(40), (3, 10))
        self.assertEqual(_lte_qpp_interleaver_params(704), (155, 44))
        interleaver = _lte_qpp_interleaver_indices(40)
        self.assertEqual(interleaver.tolist()[:8], [0, 13, 6, 19, 12, 25, 18, 31])

        info = _lte_dlsch_info(672 + 24)
        self.assertEqual(info, {"C": 1, "Km": 0, "Cm": 0, "Kp": 704, "Cp": 1, "F": 8, "L": 0, "Bout": 704})

        block = _lte_code_block_segment(np.ones(696, dtype=np.int8))[0]
        self.assertEqual(block.shape[0], 704)
        self.assertTrue(np.all(block[:8] == -1))
        self.assertTrue(np.all(block[8:] == 1))

        self.assertEqual(
            _lte_transport_block_bits_total({"NDLRB": 6, "CP": "Normal", "modulation": "QPSK", "TotSubframes": 1}),
            328,
        )
        self.assertEqual(
            _lte_transport_block_bits_total({"NDLRB": 6, "CP": "Normal", "modulation": "QPSK", "TotSubframes": 5}),
            3176,
        )
        self.assertEqual(
            _lte_transport_block_bits_total({"NDLRB": 6, "CP": "Extended", "modulation": "QPSK", "TotSubframes": 1}),
            208,
        )
        self.assertEqual(
            _lte_expected_payload_bits({"NDLRB": 6, "CP": "Extended", "modulation": "QPSK", "TotSubframes": 1}),
            408,
        )
        self.assertEqual(
            _lte_transport_block_bits_total({"NDLRB": 50, "CP": "Normal", "modulation": "QPSK", "TotSubframes": 1}),
            6200,
        )
        self.assertEqual(
            _lte_transport_block_bits_total({"NDLRB": 100, "CP": "Normal", "modulation": "16QAM", "TotSubframes": 1}),
            25456,
        )

    def test_lte_turbo_encode_matches_known_k40_probe(self) -> None:
        message = np.array(json.loads("[0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1]"), dtype=np.int8)
        expected = np.array(json.loads("[0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0]"), dtype=np.int8)
        np.testing.assert_array_equal(_lte_turbo_encode_block(message), expected)

    def test_lte_dlsch_narrow_transport_block_matches_known_oracle_bits(self) -> None:
        message = np.array(json.loads("[0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0]"), dtype=np.int8)
        expected_head = [
            0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1,
            1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1,
            1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1,
            1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1,
        ]
        expected_tail = [1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        coded = _lte_dlsch_encode_transport_block(message, 672, rv=0)
        self.assertEqual(coded.shape[0], 672)
        self.assertEqual(coded.tolist()[:64], expected_head)
        self.assertEqual(coded.tolist()[-32:], expected_tail)
        rate_only = _lte_rate_match_turbo_block(_lte_turbo_encode_block(_lte_code_block_segment(_lte_crc_attach(message, "24A"))[0]), 672, rv=0)
        np.testing.assert_array_equal(coded, rate_only)

    def test_lte_dlsch_info_matches_known_multiblock_breakpoints(self) -> None:
        self.assertEqual(
            _lte_dlsch_info(6144 + 24),
            {"C": 2, "Km": 3072, "Cm": 0, "Kp": 3136, "Cp": 2, "F": 56, "L": 24, "Bout": 6272},
        )
        self.assertEqual(
            _lte_dlsch_info(7000 + 24),
            {"C": 2, "Km": 3520, "Cm": 1, "Kp": 3584, "Cp": 1, "F": 32, "L": 24, "Bout": 7104},
        )
        self.assertEqual(
            _lte_dlsch_info(20000 + 24),
            {"C": 4, "Km": 4992, "Cm": 1, "Kp": 5056, "Cp": 3, "F": 40, "L": 24, "Bout": 20160},
        )

    def test_lte_code_block_segment_multiblock_layout(self) -> None:
        bits = np.ones(7000 + 24, dtype=np.int8)
        blocks = _lte_code_block_segment(bits)
        self.assertEqual([block.shape[0] for block in blocks], [3520, 3584])
        self.assertTrue(np.all(blocks[0][:32] == -1))
        self.assertTrue(np.all(blocks[0][32:-24] == 1))
        self.assertTrue(np.all(blocks[1][:-24] == 1))

    def test_lte_dlsch_rate_match_lengths_sum_to_requested_g(self) -> None:
        self.assertEqual(_lte_dlsch_rate_match_lengths(672, 1, "QPSK"), [672])
        self.assertEqual(_lte_dlsch_rate_match_lengths(26760, 3, "QPSK"), [8920, 8920, 8920])
        self.assertEqual(sum(_lte_dlsch_rate_match_lengths(28336, 5, "16QAM")), 28336)

    def test_lte_dlsch_encode_multiblock_matches_requested_length(self) -> None:
        message = np.arange(28336, dtype=np.int8) & 1
        coded = _lte_dlsch_encode_transport_block(message, 110976, rv=0, modulation="16QAM")
        self.assertEqual(coded.shape[0], 110976)

    def test_lte_message_path_preserves_explicit_codeword_bits(self) -> None:
        cfg = json.loads((REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_16qam.json").read_text())
        args = cfg["sources"][0]["signals"][0]["args"]
        bits = _lte_message_bits(args, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(bits.shape[0], 1344)
        self.assertEqual(bits[:16].tolist(), [0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1])
        window, cursor = _lte_transport_stream_window(bits[:6], 4, 8)
        self.assertEqual(window.tolist(), [1, 0, 0, 1, 0, 1, 1, 0])
        self.assertEqual(cursor, 12)

    def test_lte_pdcch_candidate_search_matches_known_50rb_probe(self) -> None:
        total_regs = 240
        self.assertEqual(_lte_pdcch_n_cce(total_regs), 26)
        self.assertEqual(_lte_pdcch_candidate_starts(total_regs, 0), [20, 0])
        self.assertEqual(_lte_pdcch_prbs(16).tolist(), [0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1])
        self.assertEqual(_lte_pdcch_prbs(16, 1).tolist(), [0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0])
        expected = [
            complex(-0.7071067811865475, -0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(-0.7071067811865475, -0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(-0.7071067811865475, -0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(-0.7071067811865475, -0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
            complex(0.7071067811865475, 0.7071067811865475),
        ]
        self.assertEqual(
            _lte_phich_rows(100),
            [
                (66, 68, 69, 71),
                (462, 464, 465, 467),
                (858, 860, 861, 863),
                (72, 74, 75, 77),
                (468, 470, 471, 473),
                (864, 866, 867, 869),
                (78, 80, 81, 83),
                (474, 476, 477, 479),
                (870, 872, 873, 875),
            ],
        )
        self.assertEqual(
            _lte_phich_rows(75),
            [
                (66, 68, 69, 71),
                (360, 362, 363, 365),
                (660, 662, 663, 665),
                (72, 74, 75, 77),
                (366, 368, 369, 371),
                (666, 668, 669, 671),
            ],
        )
        self.assertEqual(_lte_sync_symbol_indices("Normal"), (5, 6))
        self.assertEqual(_lte_sync_symbol_indices("Extended"), (4, 5))
        self.assertEqual(
            _lte_pdsch_scramble(np.zeros(32, dtype=np.int8), 0).tolist(),
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
        )
        self.assertEqual(
            _lte_pdsch_scramble(np.zeros(32, dtype=np.int8), 1).tolist(),
            [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        )
        np.testing.assert_allclose(_lte_phich_symbols(0, 1, "Normal"), np.asarray(expected, dtype=np.complex128), atol=1e-12, rtol=0.0)
        np.testing.assert_allclose(
            _lte_phich_symbols(0, 1, "Extended"),
            np.asarray(
                [
                    complex(-0.7071067811865475, -0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(-0.7071067811865475, -0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(-0.7071067811865475, -0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                    complex(-0.7071067811865475, -0.7071067811865475),
                    complex(0.7071067811865475, 0.7071067811865475),
                ],
                dtype=np.complex128,
            ),
            atol=1e-12,
            rtol=0.0,
        )
        self.assertEqual(
            _lte_default_dci_bits({"NDLRB": 6, "CP": "Extended", "modulation": "QPSK"}).tolist(),
            [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        )
        self.assertEqual(
            _lte_default_dci_bits({"NDLRB": 6, "CP": "Normal", "modulation": "QPSK"}, subframe_idx=1).tolist(),
            [1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0],
        )
        self.assertEqual(
            _lte_default_dci_bits({"NDLRB": 6, "CP": "Normal", "modulation": "QPSK"}, subframe_idx=5).tolist(),
            [1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0],
        )

    def test_lte_dl_fdd_extcp_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_extcp.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 1920)
        self.assertEqual(burst.sample_rate_hz, 1.92e6)
        self.assertEqual(burst.bandwidth_hz, 1.4e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 6)
        self.assertEqual(burst.extras["TotSubframes"], 1)
        self.assertEqual(burst.extras["CP"], "Extended")

    def test_lte_dl_fdd_5sf_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_5sf.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 9600)
        self.assertEqual(burst.sample_rate_hz, 1.92e6)
        self.assertEqual(burst.bandwidth_hz, 1.4e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 6)
        self.assertEqual(burst.extras["TotSubframes"], 5)

    def test_lte_dl_fdd_ndlrb15_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "lte_dl_fdd_15rb.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 3840)
        self.assertEqual(burst.sample_rate_hz, 3.84e6)
        self.assertEqual(burst.bandwidth_hz, 3.0e6)
        self.assertEqual(burst.protocol, "cellular")
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["NDLRB"], 15)
        self.assertEqual(burst.extras["TotSubframes"], 1)

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
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["subCarrierSpacing_kHz"], 15.0)
        self.assertEqual(burst.extras["numSubframes"], 1)

    def test_nr5g78_render_and_phase_formula(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "nr5g78.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 40000)
        self.assertEqual(burst.sample_rate_hz, 40e6)
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["centerFreq_Hz"], 3.3e9)
        expected = np.array(
            [
                -107992.24746714914,
                -1587486.0377670925,
                -3066979.828067036,
                -4546473.618366978,
                -6025967.408666922,
                -7505461.1989668645,
                -8984954.98926681,
                -10475248.004313467,
                -11954741.794613408,
                -13434235.58491335,
                -14913729.375213297,
                -16393223.16551324,
                -17872716.95581318,
                -19352210.746113125,
            ],
            dtype=np.float64,
        )
        np.testing.assert_allclose(symbol_phase_sequence(3.3e9), expected, atol=1e-6, rtol=0.0)

    def test_nr5g_fr1_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "nr5g_fr1.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 40000)
        self.assertEqual(burst.sample_rate_hz, 40e6)
        self.assertEqual(burst.bandwidth_hz, 5e6)
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["gridSize"], 15)
        self.assertEqual(burst.extras["centerFreq_Hz"], 2.655e9)

    def test_nr5g_pdsch_16qam_oracle_backed_preset_render(self) -> None:
        scene = load_scene(REPO_ROOT / "configs" / "synthetic_atomic" / "nr5g_pdsch_16qam.json")
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 40000)
        self.assertEqual(burst.sample_rate_hz, 40e6)
        self.assertEqual(burst.bandwidth_hz, 10e6)
        self.assertEqual(burst.extras["runtimeMode"], "direct")
        self.assertEqual(burst.extras["gridSize"], 50)
        self.assertEqual(burst.extras["modulation"], "16QAM")
        self.assertEqual(burst.extras["waveformProfile"], "pdsch")

    def test_nr5g_multisubframe_zero_pad_matches_helper_behavior(self) -> None:
        cfg = json.loads((REPO_ROOT / "configs" / "synthetic_atomic" / "nr5g.json").read_text())
        cfg["sources"][0]["signals"][0]["args"]["numSubframes"] = 5
        scene = load_scene(cfg)
        signal = scene.sources[0].signals[0]
        burst = signal.generate_transmission(scene, np.random.Generator(np.random.MT19937(1234)))
        self.assertEqual(len(burst.samples), 200000)
        self.assertGreater(np.max(np.abs(burst.samples[:40000])), 0.0)
        self.assertEqual(np.max(np.abs(burst.samples[40000:])), 0.0)


if __name__ == "__main__":
    unittest.main()
