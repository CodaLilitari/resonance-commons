"""Bounded, independent analytic fixtures; no EchoSeam executable or model."""
import array
import copy
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import wave
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("packet_under_test", ROOT / "evidence_packet.py")
ep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep)


def tiny_png():
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0)) + chunk(b"IDAT",zlib.compress(b"\0\0\0\0")) + chunk(b"IEND",b"")


def wav_bytes(channels, samples):
    b=io.BytesIO()
    with wave.open(b,"wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(struct.pack("<"+"h"*len(samples),*samples))
    return b.getvalue()


def analytic_channel(i, amplitude):
    # Exactly alternating signs, 320 frames. No estimate from builder code.
    value=amplitude/32768
    db=20*math.log10(value) if amplitude else None
    return {"channel_index":i,"rms_linear":value,"rms_dbfs":db,"sample_peak_linear":value,"sample_peak_dbfs":db,
            "dc_offset_linear":0,"near_pcm16_rail_ratio":0,"zero_crossing_rate":1 if amplitude else 0}


def make_fixture(parent):
    report=parent/"report"
    report.mkdir()
    source=parent/"original.wav"
    left=[(-16384 if i%2==0 else 16384) for i in range(320)]
    source_bytes=wav_bytes(2,[v for sample in left for v in (sample,0)])
    source.write_bytes(source_bytes)
    (report/"source-channels.wav").write_bytes(source_bytes)
    (report/"mono-derivative.wav").write_bytes(wav_bytes(1,[v//2 for v in left]))
    def metrics(channels,basis):
        rms=math.sqrt(sum(x["rms_linear"]**2 for x in channels)/len(channels))
        peak=max(x["sample_peak_linear"] for x in channels)
        return {"signal_basis":basis,"channel_count":len(channels),"sample_rate_hz":8000,"sample_frames":320,"duration_seconds":.04,
                "channels":channels,"rms_linear":rms,"rms_dbfs":20*math.log10(rms),"sample_peak_linear":peak,"sample_peak_dbfs":20*math.log10(peak),
                "silence":{"signal_basis":basis,"threshold_dbfs":-45,"minimum_duration_seconds":.25,"frame_duration_seconds":.02,
                           "intervals":[],"ratio":0,"total_seconds":0}}
    analysis={"schema":"lilitari-echoseam-analysis-v3","edition_version":"0.1.3","signal_basis":ep.SOURCE_BASIS,"time_basis":ep.TIME_BASIS,
              "source":{"name":"<script>PRIVATE_SOURCE_NAME</script>","sha256":hashlib.sha256(source_bytes).hexdigest(),"bytes":len(source_bytes),"selected_audio_stream_index":0},
              "mono_severe_loss_detected":False,"observations":{
                  "source_pcm16":metrics([analytic_channel(0,16384),analytic_channel(1,0)],ep.SOURCE_BASIS),
                  "mono_derivative_pcm16":metrics([analytic_channel(0,8192)],ep.MONO_BASIS),
                  "mono_downmix":{"signal_basis":ep.MONO_BASIS,"input_signal_basis":ep.SOURCE_BASIS,"source_channel_indices":[0,1],"output_channel_count":1,
                    "coefficient_matrix":[[.5,.5]],"ffmpeg_filter":"pan=mono|c0=0.5*c0+0.5*c1","strongest_source_channel_rms_linear":.5,
                    "rms_ratio_to_strongest_source_channel":.5,"gain_db_relative_to_strongest_source_channel":20*math.log10(.5),"gain_status":"finite",
                    "severe_loss_detected":False,"severe_loss_threshold_ratio":.05,"single_active_stereo_ideal_gain_db":20*math.log10(.5)},
                  "timeline":[{"start_seconds":0,"end_seconds":.04,"type":"outside_detected_silence_intervals","signal_basis":ep.SOURCE_BASIS}],
                  "ebu_r128":{"signal_basis":ep.SOURCE_BASIS,"integrated_lufs":-12,"loudness_range_lu":0,"estimated_true_peak_dbfs":-6},
                  "volume_detect":{"signal_basis":ep.SOURCE_BASIS,"mean_volume_db":-9,"max_volume_db":-6}},
              "plots":{"waveform.png":{"signal_basis":ep.SOURCE_BASIS,"top_to_bottom_source_channel_indices":[0,1]},
                       "spectrogram.png":{"signal_basis":ep.SOURCE_BASIS,"top_to_bottom_source_channel_indices":[1,0],"bottom_to_top_source_channel_indices":[0,1]},
                       "spectrogram-source-channel-0.png":{"signal_basis":ep.SOURCE_BASIS,"source_channel_index":0},
                       "spectrogram-source-channel-1.png":{"signal_basis":ep.SOURCE_BASIS,"source_channel_index":1}}}
    (report/"analysis.json").write_bytes(ep.canonical(analysis))
    (report/"probe.json").write_bytes(ep.canonical({"streams":[{"codec_type":"audio","index":0,"channels":2,"sample_rate":"8000","codec_name":"pcm_s16le"}],
                                                  "format":{"filename":"C:/PRIVATE_MACHINE_PATH/source.wav"}}))
    for filename,key in [("transcript.json","segments"),("events.json","events")]:
        (report/filename).write_bytes(ep.canonical({"attempted":False,key:[],"epistemic_status":"no_claim"}))
    for name in ep.COMMON|ep.OPTIONAL:
        if name.endswith(".png"):
            (report/name).write_bytes(tiny_png())
        elif not (report/name).exists():
            (report/name).write_bytes(b"<script>PRIVATE_RAW_HTML_OR_LOG</script>")
    return report,source,analysis


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="coda-packet-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.report,self.source,self.analysis=make_fixture(self.root)
        self.receipt=self.root/"receipt.json"

    def pin(self):
        analysis,members,receipt=ep.report_snapshot(self.report,self.source)
        self.receipt.write_bytes(ep.canonical(receipt))
        return analysis,members,receipt

    def build(self,filename="packet.zip"):
        self.pin()
        path=self.root/filename
        result=ep.build_packet(self.report,self.source,self.receipt,ep.digest(self.receipt.read_bytes()),path,"Test Project","case-001")
        return path,result

    def change_analysis(self,fn):
        a=copy.deepcopy(self.analysis)
        fn(a)
        (self.report/"analysis.json").write_bytes(ep.canonical(a))

    def test_analytic_source_and_matrix_and_time(self):
        path,_=self.build()
        ledger=ep.verify_packet_bytes(path.read_bytes())
        self.assertEqual(ledger["measurements"]["source_pcm16"]["channels"][0]["rms_linear"],.5)
        self.assertEqual(ledger["measurements"]["source_pcm16"]["channels"][1]["rms_linear"],0)
        self.assertEqual(ledger["transforms"][1]["coefficient_matrix"],[[.5,.5]])
        self.assertAlmostEqual(ledger["transforms"][1]["gain_db_relative_to_strongest_source_channel"],-6.020599913279624)
        self.assertEqual(ledger["time"]["decoded_stream_end_seconds_exclusive"],.04)
        self.assertIsNone(ledger["time"]["parent_recording_origin_seconds"])
        self.assertEqual(ledger["evidence"][3]["top_to_bottom_source_channel_indices"],[1,0])

    def test_deterministic_bytes_and_private_field_projection(self):
        first,_=self.build()
        second,_=self.build("second.zip")
        self.assertEqual(first.read_bytes(),second.read_bytes())
        for forbidden in [b"PRIVATE_",b"<script>",b"C:/",b"original.wav"]:
            self.assertNotIn(forbidden,first.read_bytes())
        ledger=ep.verify_packet_bytes(first.read_bytes())
        self.assertTrue(all(x["status"]=="unavailable" and x["attempted"] is False for x in ledger["capabilities"].values()))

    def test_pin_hash_mismatch(self):
        self.pin()
        with self.assertRaises(ep.Refusal):
            ep.build_packet(self.report,self.source,self.receipt,"0"*64,self.root/"packet.zip","Name","case-001")

    def test_report_tamper_after_pin(self):
        self.pin()
        (self.report/"report.html").write_text("tampered")
        with self.assertRaises(ep.Refusal):
            ep.build_packet(self.report,self.source,self.receipt,ep.digest(self.receipt.read_bytes()),self.root/"packet.zip","Name","case-001")

    def test_report_budget_is_applied_before_next_read(self):
        # Small artificial budget; two individually legal large text members.
        # The reader must reject based on stat before reading the second payload.
        (self.report/"analysis.txt").write_bytes(b"a"*6000)
        (self.report/"ebur128.txt").write_bytes(b"b"*6000)
        seen=[]
        original=ep.read_bytes
        def observe(path,limit=ep.MAX_FILE):
            seen.append((Path(path).name,limit))
            return original(path,limit)
        budget=(self.report/"analysis.json").stat().st_size+9000
        with mock.patch.object(ep,"MAX_FILE",budget),mock.patch.object(ep,"read_bytes",observe),self.assertRaises(ep.Refusal):
            ep.report_snapshot(self.report,self.source)
        self.assertEqual(seen[-1][0],"ebur128.txt")
        self.assertLess(seen[-1][1],6000)

    def test_wrong_original_source(self):
        self.source.write_bytes(b"not the original")
        with self.assertRaises(ep.Refusal):
            self.pin()

    def test_forged_measurement_rejected_after_repin(self):
        self.change_analysis(lambda a:a["observations"]["source_pcm16"]["channels"][0].update(rms_linear=.25))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_waveform_mapping_rejected_after_repin(self):
        self.change_analysis(lambda a:a["plots"]["waveform.png"].update(top_to_bottom_source_channel_indices=[1,0]))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_spectrogram_mapping_rejected_after_repin(self):
        self.change_analysis(lambda a:a["plots"]["spectrogram.png"].update(top_to_bottom_source_channel_indices=[0,1]))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_timeline_shift_rejected(self):
        self.change_analysis(lambda a:a["observations"]["timeline"][0].update(start_seconds=.01))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_mono_matrix_rejected(self):
        self.change_analysis(lambda a:a["observations"]["mono_downmix"].update(coefficient_matrix=[[1,1]]))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_mono_pcm_rejected_after_repin(self):
        (self.report/"mono-derivative.wav").write_bytes(wav_bytes(1,[0]*320))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_learned_status_cannot_be_upgraded(self):
        (self.report/"transcript.json").write_bytes(ep.canonical({"attempted":True,"segments":[],"epistemic_status":"no_claim"}))
        with self.assertRaises(ep.Refusal):
            self.build()

    def test_missing_required_member(self):
        (self.report/"waveform.png").unlink()
        with self.assertRaises((OSError,ep.Refusal)):
            self.build()

    def test_nonfinite_and_duplicate_json(self):
        for raw in [b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e999}',b'{"x":1,"x":2}']:
            with self.subTest(raw=raw),self.assertRaises(ep.Refusal):
                ep.strict_json(raw)

    def test_oversized_json_and_nesting(self):
        for raw in [b" "*(ep.MAX_JSON+1),b"["*40+b"0"+b"]"*40]:
            with self.assertRaises(ep.Refusal):
                ep.strict_json(raw)

    def test_existing_file_and_directory_unchanged(self):
        for name,is_dir in [("occupied.zip",False),("occupied-dir",True)]:
            path=self.root/name
            if is_dir:
                path.mkdir();(path/"sentinel").write_bytes(b"keep")
            else:path.write_bytes(b"keep")
            with self.assertRaises(ep.Refusal):self.build(name)
            self.assertEqual((path/"sentinel" if is_dir else path).read_bytes(),b"keep")

    def test_destination_race_cannot_replace(self):
        path=self.root/"race.zip"
        original=os.link
        def race(src,dst,**kw):
            Path(dst).write_bytes(b"racer")
            return original(src,dst,**kw)
        with mock.patch.object(ep.os,"link",race),self.assertRaises(FileExistsError):
            self.build("race.zip")
        self.assertEqual(path.read_bytes(),b"racer")
        self.assertFalse(list(self.root.glob(".evidence-packet-*")))

    def test_unsupported_publication_has_no_replace_fallback(self):
        with mock.patch.object(ep.os,"link",side_effect=OSError("unsupported")),self.assertRaisesRegex(ep.Refusal,"no replacement fallback"):
            self.build()
        self.assertFalse((self.root/"packet.zip").exists())

    def test_output_cannot_overlap_report(self):
        self.pin()
        with self.assertRaises(ep.Refusal):
            ep.build_packet(self.report,self.source,self.receipt,ep.digest(self.receipt.read_bytes()),self.report/"packet.zip","Name","case-001")

    def test_hardlinked_source_refused(self):
        alias=self.root/"source-alias.wav"
        try:os.link(self.source,alias)
        except OSError as exc:self.skipTest("Host cannot create hardlinks: "+type(exc).__name__)
        with self.assertRaises(ep.Refusal):self.build()

    def test_symlink_file_and_parent_refused(self):
        link=self.root/"link"
        try:link.symlink_to(self.report,target_is_directory=True)
        except OSError as exc:self.skipTest("Host cannot create symlinks: "+type(exc).__name__)
        with self.assertRaises(ep.Refusal):ep.report_snapshot(link,self.source)
        with self.assertRaises(ep.Refusal):ep.publish_new(link/"packet.zip",b"unsafe")

    @unittest.skipUnless(os.name == "nt", "Windows junction check")
    def test_windows_junction_parent_refused(self):
        link=self.root/"junction"
        # Exact disposable test paths only; creation requires no elevation.
        result=subprocess.run(["cmd","/c","mklink","/J",str(link),str(self.report)],capture_output=True)
        self.assertEqual(result.returncode,0,"Could not create the owned test junction")
        try:
            with self.assertRaises(ep.Refusal):ep.report_snapshot(link,self.source)
            with self.assertRaises(ep.Refusal):ep.publish_new(link/"packet.zip",b"unsafe")
            self.assertFalse((self.report/"packet.zip").exists())
        finally:
            link.rmdir()  # Remove just this junction, never recursively traverse it.

    def test_png_crc_metadata_and_decompression_bounds(self):
        bad=bytearray(tiny_png());bad[-1]^=1
        with self.assertRaises(ep.Refusal):ep.png(bytes(bad))
        def chunk(kind,data):return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
        for injected in [chunk(b"tEXt",b"private metadata"),chunk(b"IDAT",zlib.compress(b"x"*1000))]:
            data=tiny_png()[:-12]+injected+tiny_png()[-12:]
            with self.assertRaises(ep.Refusal):ep.png(data)

    def test_zip_member_tamper(self):
        path,_=self.build()
        data=io.BytesIO()
        with zipfile.ZipFile(path) as original,zipfile.ZipFile(data,"w") as altered:
            for info in original.infolist():
                b=original.read(info)
                altered.writestr(info,b+b" " if info.filename=="ledger.json" else b)
        with self.assertRaises(ep.Refusal):ep.verify_packet_bytes(data.getvalue())

    def test_zip_traversal_duplicate_compression_refused(self):
        path,_=self.build()
        for attack in ["traversal","duplicate","compressed"]:
            data=io.BytesIO()
            with zipfile.ZipFile(path) as original,zipfile.ZipFile(data,"w") as altered:
                for info in original.infolist():
                    b=original.read(info)
                    if attack=="compressed":info.compress_type=zipfile.ZIP_DEFLATED
                    if attack=="traversal" and info.filename=="ledger.json":info.filename="../ledger.json"
                    altered.writestr(info,b)
                if attack=="duplicate":altered.writestr("ledger.json",b"{}")
            with self.subTest(attack=attack),self.assertRaises(ep.Refusal):ep.verify_packet_bytes(data.getvalue())

    def test_follow_up_valid_and_adversarial(self):
        path,_=self.build()
        ledger=ep.verify_packet_bytes(path.read_bytes())
        request={"schema":"coda.audio-follow-up-request.v1","source_sha256":ledger["source"]["sha256"],"probes":[{"id":"probe-01","operation":"channel-view","start_seconds":0,"end_seconds":.04,"channel_indices":[1]}]}
        self.assertEqual(ep.validate_follow_up(ledger,request)["status"],"valid-proposal-not-executed")
        mutations=[lambda r:r.update(source_sha256="0"*64),lambda r:r["probes"][0].update(start_seconds=-1),
                   lambda r:r["probes"][0].update(end_seconds=.041),lambda r:r["probes"][0].update(end_seconds=0),
                   lambda r:r["probes"][0].update(channel_indices=[True]),lambda r:r["probes"][0].update(channel_indices=[0,0]),
                   lambda r:r["probes"][0].update(operation="shell"),lambda r:r["probes"][0].update(command="bad"),
                   lambda r:r["probes"].extend(copy.deepcopy(r["probes"])),lambda r:r["probes"][0].update(end_seconds=float("nan"))]
        for mutate in mutations:
            bad=copy.deepcopy(request);mutate(bad)
            with self.subTest(mutation=mutate),self.assertRaises(ep.Refusal):ep.validate_follow_up(ledger,bad)

    def test_forged_ledger_extent_rejected_before_range(self):
        path,_=self.build()
        with zipfile.ZipFile(path) as z:
            payload={n:z.read(n) for n in z.namelist()}
        base=json.loads(payload["ledger.json"])
        changes=[lambda x:x["measurements"]["source_pcm16"].update(channel_count=10**9),
                 lambda x:x["measurements"]["source_pcm16"].update(channel_count=True),
                 lambda x:x["time"].update(decoded_stream_end_seconds_exclusive=31),
                 lambda x:x.update(measurements=[]),lambda x:x.update(source=None),lambda x:x.update(time="bad")]
        for change in changes:
            ledger=copy.deepcopy(base);change(ledger)
            # Re-hash the manifest too: a caller may have pinned malicious bytes.
            altered=dict(payload);altered["ledger.json"]=ep.canonical(ledger)
            manifest=json.loads(altered["manifest.json"])
            manifest["files"]=[{"path":n,"bytes":len(altered[n]),"sha256":ep.digest(altered[n])} for n in sorted(ep.PACKET_FILES)]
            altered["manifest.json"]=ep.canonical(manifest)
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,"w") as z:
                for n,b in altered.items():
                    info=zipfile.ZipInfo(n);info.external_attr=(stat.S_IFREG|0o644)<<16
                    z.writestr(info,b)
            with self.assertRaises(ep.Refusal):ep.verify_packet_bytes(buffer.getvalue())

    def test_name_and_case_id_cannot_inject_or_reveal_source_labels(self):
        a,m,r=self.pin();v=ep.validate_report(a,m)
        for name,case in [("<script>","case-001"),("Name","left-only"),("../escape","case-001")]:
            with self.assertRaises(ep.Refusal):ep.make_ledger(a,r,v,name,case)


if __name__=="__main__":
    unittest.main(verbosity=2)
