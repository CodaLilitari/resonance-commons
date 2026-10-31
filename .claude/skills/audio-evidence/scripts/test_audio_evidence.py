"""Tests for audio_evidence.py with synthetic signals whose answers are known.

Needs numpy, ffmpeg and ffprobe (Claude's cloud workspace has them); matplotlib for the
packet test. Run: python3 -B -m unittest test_audio_evidence -v
"""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
import wave
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audio_evidence", HERE / "audio_evidence.py")
ae = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ae)
np = ae.np

READY = np is not None and shutil.which("ffmpeg") and shutil.which("ffprobe")
try:
    import matplotlib  # noqa: F401
    PLOTS = True
except ImportError:
    PLOTS = False


def write_wav(path, samples, rate):
    """samples: frames x channels floats in [-1, 1]."""
    data = np.clip(np.round(np.asarray(samples) * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(data.shape[1])
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(data.tobytes())


@unittest.skipUnless(READY, "needs numpy, ffmpeg and ffprobe")
class Base(unittest.TestCase):
    rate = 44100

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="audio-evidence-")
        self.root = Path(self.temp.name)
        self.count = 0

    def tearDown(self):
        self.temp.cleanup()

    def source(self, samples, rate=None, name=None):
        self.count += 1
        path = self.root / (name or f"source-{self.count}.wav")
        write_wav(path, samples, rate or self.rate)
        return path

    def analyse(self, path, plots=False, **kw):
        self.count += 1
        out = self.root / f"evidence-{self.count}"
        ae.analyse(path, out, plots=plots, **kw)
        return out, json.loads((out / "ledger.json").read_text())

    def tone(self, freq, seconds, amp=0.5, rate=None):
        rate = rate or self.rate
        t = np.arange(int(rate * seconds)) / rate
        return amp * np.sin(2 * np.pi * freq * t)


class MeasurementTests(Base):
    def test_sine_levels_are_exact(self):
        mono = self.tone(997, 4, amp=0.5)[:, None]
        _, ledger = self.analyse(self.source(mono))
        ch = ledger["measurements"]["source_channels"]["channels"][0]
        self.assertAlmostEqual(ch["rms_dbfs"], 20 * math.log10(0.5 / math.sqrt(2)), delta=0.02)
        self.assertAlmostEqual(ch["sample_peak_dbfs"], 20 * math.log10(0.5), delta=0.02)
        self.assertAlmostEqual(ch["crest_factor_db"], 3.01, delta=0.03)
        self.assertAlmostEqual(ch["zero_crossings_per_second"], 2 * 997, delta=4)
        self.assertEqual(ch["full_scale_runs_ge3"]["count"], 0)
        self.assertEqual(ledger["measurements"]["source_channels"]["channels"][0]["name"], "mono")

    def test_full_scale_runs_count_flat_tops(self):
        clipped = np.clip(self.tone(100, 3, amp=1.5), -1, 1)[:, None]
        _, ledger = self.analyse(self.source(clipped))
        ch = ledger["measurements"]["source_channels"]["channels"][0]
        self.assertGreater(ch["near_full_scale_ratio"], 0.4)
        self.assertAlmostEqual(ch["full_scale_runs_ge3"]["count"], 600, delta=4)  # two flat tops per cycle
        self.assertGreater(ch["full_scale_runs_ge3"]["longest_samples"], 50)

    def test_stereo_identical_inverted_and_uncorrelated(self):
        tone = self.tone(220, 3)
        _, same = self.analyse(self.source(np.stack([tone, tone], 1)))
        self.assertAlmostEqual(same["measurements"]["stereo"]["correlation"], 1.0, places=3)
        self.assertAlmostEqual(same["measurements"]["stereo"]["mono_fold_down_change_db"], 0.0, delta=0.01)
        _, inverted = self.analyse(self.source(np.stack([tone, -tone], 1)))
        self.assertAlmostEqual(inverted["measurements"]["stereo"]["correlation"], -1.0, places=3)
        self.assertIsNone(inverted["measurements"]["stereo"]["mono_fold_down_change_db"])
        rng = np.random.default_rng(3)
        noise = rng.standard_normal((self.rate * 3, 2)) * 0.1
        _, loose = self.analyse(self.source(noise))
        self.assertLess(abs(loose["measurements"]["stereo"]["correlation"]), 0.05)
        self.assertAlmostEqual(loose["measurements"]["stereo"]["mono_fold_down_change_db"], -3.01, delta=0.15)

    def test_silence_interval_in_decoded_time(self):
        tone = self.tone(330, 6)
        tone[int(2.0 * self.rate):int(3.5 * self.rate)] = 0
        _, ledger = self.analyse(self.source(tone[:, None]))
        intervals = ledger["measurements"]["silence"]["intervals"]
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0]["start_seconds"], 2.0, delta=0.021)
        self.assertAlmostEqual(intervals[0]["end_seconds"], 3.5, delta=0.021)
        _, span = self.analyse(self.source(tone[:, None]), start=1.0, end=5.0)
        self.assertAlmostEqual(span["measurements"]["silence"]["intervals"][0]["start_seconds"], 2.0, delta=0.021)
        self.assertEqual(span["time"]["start_seconds"], 1.0)

    def test_edges_catch_a_hard_cut(self):
        tone = self.tone(220, 3)
        _, cut = self.analyse(self.source(tone[:, None]))
        self.assertTrue(cut["measurements"]["edges"]["ends_while_sounding"])
        faded = tone * np.clip((3.0 - np.arange(tone.size) / self.rate) / 1.0, 0, 1)
        _, fade = self.analyse(self.source(faded[:, None]))
        self.assertFalse(fade["measurements"]["edges"]["ends_while_sounding"])
        self.assertLess(fade["measurements"]["edges"]["end_level_dbfs"], -30)

    def test_loudness_follows_level(self):
        tone = self.tone(1000, 6, amp=0.4)
        _, loud = self.analyse(self.source(np.stack([tone, tone], 1)))
        _, quiet = self.analyse(self.source(np.stack([tone / 2, tone / 2], 1)))
        a, b = loud["measurements"]["loudness"], quiet["measurements"]["loudness"]
        self.assertAlmostEqual(b["integrated_lufs"] - a["integrated_lufs"], -6.0, delta=0.15)
        self.assertAlmostEqual(a["true_peak_dbtp"], 20 * math.log10(0.4), delta=0.2)
        self.assertEqual(len(a["true_peak_per_channel_dbtp"]), 2)

    def test_band_balance_and_bandwidth(self):
        rng = np.random.default_rng(5)
        noise = rng.standard_normal(self.rate * 4) * 0.05
        spectrum = np.fft.rfft(noise)
        freqs = np.fft.rfftfreq(noise.size, 1 / self.rate)
        spectrum[freqs > 16000] = 0
        lowpassed = np.fft.irfft(spectrum, noise.size)
        _, ledger = self.analyse(self.source(lowpassed[:, None]))
        balance = ledger["measurements"]["spectral_balance"]
        self.assertAlmostEqual(balance["effective_bandwidth_hz"], 16000, delta=400)
        self.assertGreater(balance["bands"]["air"]["energy_share"], balance["bands"]["bass"]["energy_share"])


class EstimateTests(Base):
    def test_pitch_and_chroma_of_a_440_tone(self):
        _, ledger = self.analyse(self.source(self.tone(440, 4)[:, None]))
        pitch = ledger["estimates"]["pitch"]
        self.assertAlmostEqual(pitch["median_hz"], 440.0, delta=1.0)
        self.assertTrue(pitch["median_note"].startswith("A4"))
        self.assertGreater(pitch["voiced_ratio"], 0.9)
        chroma = ledger["estimates"]["key"]["mean_chroma"]
        self.assertEqual(max(chroma, key=chroma.get), "A")

    def test_click_train_tempo(self):
        rate, bpm = 22050, 100.0
        clicks = np.zeros(int(rate * 20))
        rng = np.random.default_rng(1)
        for k in range(int(20 * bpm / 60)):
            start = int(k * 60 / bpm * rate)
            burst = rng.standard_normal(400) * np.exp(-np.arange(400) / 60) * 0.8
            clicks[start:start + 400] += burst[:max(0, min(400, clicks.size - start))]
        _, ledger = self.analyse(self.source(clicks[:, None], rate=rate))
        tempo = ledger["estimates"]["tempo"]
        candidates = [tempo["bpm"], *tempo["octave_alternatives"]]
        self.assertTrue(any(abs(c - bpm) / bpm < 0.02 for c in candidates), tempo)
        self.assertGreater(ledger["estimates"]["beats"]["count"], 25)

    def test_major_triads_give_c_major_or_its_relative(self):
        t = np.arange(int(self.rate * 2)) / self.rate
        chord = lambda freqs: sum(np.sin(2 * np.pi * f * t) for f in freqs) * 0.15
        progression = [(261.63, 329.63, 392.0), (349.23, 440.0, 523.25), (392.0, 493.88, 587.33), (261.63, 329.63, 392.0)]
        signal = np.concatenate([chord(c) for c in progression * 2])
        _, ledger = self.analyse(self.source(signal[:, None]))
        key = ledger["estimates"]["key"]
        self.assertIn(key["key"], ("C major", "A minor"))
        self.assertIn(key["runner_up"], ("C major", "A minor", "G major", "F major", "E minor", "D minor"))


class PacketAndProbeTests(Base):
    def make(self, plots=PLOTS):
        tone = self.tone(440, 5)
        rng = np.random.default_rng(9)
        stereo = np.stack([tone, tone * 0.8 + rng.standard_normal(tone.size) * 0.01], 1)
        src = self.source(stereo, name="Secret Song Title.wav")
        out, ledger = self.analyse(src, plots=plots)
        return src, out, ledger

    @unittest.skipUnless(PLOTS, "needs matplotlib")
    def test_packet_is_deterministic_private_and_verifiable(self):
        src, out, _ = self.make()
        again = self.root / "again"
        ae.analyse(src, again, plots=True)
        first = ae.build_packet(out, self.root / "a.zip")
        second = ae.build_packet(again, self.root / "b.zip")
        self.assertEqual(first["sha256"], second["sha256"])
        data = (self.root / "a.zip").read_bytes()
        self.assertNotIn(b"Secret Song", data)
        self.assertNotIn(str(self.root).encode(), data)
        with zipfile.ZipFile(self.root / "a.zip") as archive:
            names = archive.namelist()
            self.assertEqual(names[0], "manifest.json")
            self.assertFalse(any(n.endswith((".wav", ".mp3", ".flac")) for n in names))
            self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in archive.infolist()))
            for name in names:
                if name.endswith(".png"):
                    self.assertNotIn(b"tEXt", archive.read(name))
        self.assertEqual(ae.verify_packet(self.root / "a.zip", first["sha256"])["status"], "verified")
        with self.assertRaises(ae.EvidenceError):
            ae.verify_packet(self.root / "a.zip", "0" * 64)
        tampered = bytearray(data)
        tampered[len(tampered) // 2] ^= 0x01
        (self.root / "t.zip").write_bytes(bytes(tampered))
        with self.assertRaises((ae.EvidenceError, zipfile.BadZipFile)):
            ae.verify_packet(self.root / "t.zip", ae.sha256_bytes(bytes(tampered)))
        with self.assertRaises(ae.EvidenceError):
            ae.build_packet(out, self.root / "a.zip")

    def request(self, ledger, **changes):
        body = {"schema": ae.REQUEST_SCHEMA, "source_sha256": ledger["source"]["sha256"],
                "probes": [{"id": "probe-01", "operation": "time-window", "start_seconds": 1, "end_seconds": 2,
                            "channel_indices": [0, 1]}]}
        body.update(changes)
        return body

    def test_follow_up_requests_are_bounded(self):
        _, _, ledger = self.make(plots=False)
        self.assertEqual(len(ae.validate_request(self.request(ledger), ledger)), 1)
        probe = self.request(ledger)["probes"][0]
        bad = [
            self.request(ledger, schema="other"),
            self.request(ledger, source_sha256="0" * 64),
            {**self.request(ledger), "command": "rm -rf /"},
            self.request(ledger, probes=[{**probe, "operation": "download"}]),
            self.request(ledger, probes=[{**probe, "url": "https://example.com"}]),
            self.request(ledger, probes=[dict(probe, id=f"probe-0{i}") for i in range(1, 5)]),
            self.request(ledger, probes=[probe, dict(probe)]),
            self.request(ledger, probes=[{**probe, "end_seconds": 99}]),
            self.request(ledger, probes=[{**probe, "start_seconds": 2, "end_seconds": 1}]),
            self.request(ledger, probes=[{**probe, "start_seconds": True}]),
            self.request(ledger, probes=[{**probe, "channel_indices": [2]}]),
            self.request(ledger, probes=[{**probe, "channel_indices": [0, 0]}]),
            self.request(ledger, probes=[]),
        ]
        for body in bad:
            with self.subTest(body=json.dumps(body)[:120]):
                with self.assertRaises(ae.EvidenceError):
                    ae.validate_request(body, ledger)
        for text in (b'{"schema": 1, "schema": 2}', b'{"x": NaN}'):
            with self.assertRaises((ae.EvidenceError, ValueError)):
                ae.load_json_strict(text)

    def test_probe_runs_only_on_the_exact_source(self):
        src, out, ledger = self.make(plots=False)
        body = self.request(ledger, probes=[
            {"id": "probe-01", "operation": "time-window", "start_seconds": 1, "end_seconds": 3, "channel_indices": [0]},
            {"id": "probe-02", "operation": "higher-resolution-signal-measurement", "start_seconds": 0, "end_seconds": 1,
             "channel_indices": [0, 1]}])
        request = self.root / "request.json"
        request.write_text(json.dumps(body))
        result = ae.run_probes(src, out, request, self.root / "probes", plots=False)
        self.assertEqual(result["probes"], 2)
        receipt = json.loads((self.root / "probes" / "probe-ledger.json").read_text())
        window = receipt["probes"][0]
        self.assertAlmostEqual(window["channels"][0]["rms_dbfs"], 20 * math.log10(0.5 / math.sqrt(2)), delta=0.05)
        self.assertIn("loudness", window)
        native = receipt["probes"][1]
        self.assertIsNotNone(native["channels"][0]["oversampled_peak_4x_dbfs"])
        other = self.source(self.tone(440, 5)[:, None])
        with self.assertRaises(ae.EvidenceError):
            ae.run_probes(other, out, request, self.root / "probes-2", plots=False)

    def test_compare_reports_level_change(self):
        tone = self.tone(1000, 5, amp=0.4)
        a, _ = self.analyse(self.source(np.stack([tone, tone], 1)))
        b, _ = self.analyse(self.source(np.stack([tone / 2, tone / 2], 1)))
        report = ae.compare(a, b)
        self.assertFalse(report["same_source"])
        self.assertAlmostEqual(report["metrics"]["integrated_lufs"]["b_minus_a"], -6.0, delta=0.15)

    def test_refusals(self):
        src, out, _ = self.make(plots=False)
        with self.assertRaises(ae.EvidenceError):
            ae.analyse(src, out)  # output exists
        with self.assertRaises(ae.EvidenceError):
            ae.analyse(src, self.root / "bad-case", case_id="song-1")
        with self.assertRaises(ae.EvidenceError):
            ae.analyse(src, self.root / "long", max_seconds=2)
        link = self.root / "link.wav"
        link.symlink_to(src)
        with self.assertRaises(ae.EvidenceError):
            ae.analyse(link, self.root / "linked")


if __name__ == "__main__":
    unittest.main()
