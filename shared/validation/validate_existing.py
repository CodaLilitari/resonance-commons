"""Replay CLI acceptance on five explicitly supplied existing synthetic reports.

No report generator/model/decoder is run. Read-only inputs; owned temporary outputs.
This validation helper is not part of the provider packet.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root",required=True,type=Path)
    parser.add_argument("--fixtures-root",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=args.output.resolve()
    if output.exists() or output.parent != root/"validation":
        parser.error("Use a new output JSON directly inside this helper's validation folder")
    script=root/"evidence_packet.py"
    spec=importlib.util.spec_from_file_location("packet_tests",root/"tests/test_packet.py")
    tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
    log=io.StringIO();started=time.perf_counter()
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    if not result.wasSuccessful():
        raise RuntimeError(log.getvalue())
    base=args.report_root.resolve();fixtures=args.fixtures_root.resolve()
    cases=[("left-only",fixtures/"stereo-left-only.wav","finite",False),
           ("right-only",base/"independent-right-only.wav","finite",False),
           ("anti-phase",fixtures/"stereo-antiphase.wav","negative_infinity_zero_mono",True),
           ("mono-identity",fixtures/"a4-440hz.wav","finite",False),
           ("zero-reference",fixtures/"stereo-silence.wav","undefined_zero_source",False)]
    rows=[]
    def cli(command):
        run=subprocess.run([sys.executable,"-I","-B",str(script),*command],capture_output=True,text=True,timeout=30)
        if run.returncode:
            raise RuntimeError(run.stderr)
        return json.loads(run.stdout)
    def check(condition,message):
        if not condition:raise RuntimeError(message)
    with tempfile.TemporaryDirectory(prefix="integration-",dir=root/"validation") as temp:
        scratch=Path(temp)
        for index,(name,source,status,loss) in enumerate(cases,1):
            report=base/(name+"-artifacts")
            before={p:sha(p) for p in [source,*report.iterdir()] if p.is_file()}
            receipt=scratch/(name+".json");packet=scratch/(name+".zip");tick=time.perf_counter()
            outputs=[cli(["pin","--report",str(report),"--source",str(source),"--output",str(receipt)])]
            outputs.append(cli(["build","--report",str(report),"--source",str(source),"--receipt",str(receipt),
                                "--receipt-sha256",sha(receipt),"--output",str(packet),"--case-id",f"case-{index:03}"]))
            outputs.append(cli(["verify","--packet",str(packet),"--sha256",sha(packet)]))
            with zipfile.ZipFile(packet) as archive:
                ledger=json.loads(archive.read("ledger.json"));member_count=len(archive.namelist())
            matrix=ledger["transforms"][1];primary=ledger["measurements"]["source_pcm16"];mono=ledger["measurements"]["mono_derivative_pcm16"]
            check(matrix["gain_status"]==status and matrix["severe_loss_detected"] is loss,"Gain status mismatch")
            check(ledger["project_name"]=="Resonance Commons","Project name mismatch")
            check(ledger["source"]["sha256"]==sha(source) and ledger["source"]["original_audio_supplied_in_packet"] is False,"Source/modality mismatch")
            check(ledger["time"]["parent_recording_origin_seconds"] is None,"Invented origin")
            check(all(v["status"]=="unavailable" and v["attempted"] is False for v in ledger["capabilities"].values()),"Capability inflation")
            check(ledger["evidence"][2]["top_to_bottom_source_channel_indices"]==list(range(primary["channel_count"])),"Waveform mapping mismatch")
            check(ledger["evidence"][3]["top_to_bottom_source_channel_indices"]==list(reversed(range(primary["channel_count"]))),"Spectrogram mapping mismatch")
            if name=="anti-phase":
                check(primary["rms_linear"]>0 and primary["silence"]["ratio"]==0 and mono["rms_linear"]==0,"Anti-phase source lost")
            if name=="zero-reference":
                check(primary["rms_linear"]==0 and primary["silence"]["ratio"]==1 and matrix["gain_db_relative_to_strongest_source_channel"] is None,"Silence/null mismatch")
            if name in ("left-only","right-only"):
                check(abs(matrix["gain_db_relative_to_strongest_source_channel"]+6.020599913279624)<1e-6,"Single-channel attenuation mismatch")
            check(before=={p:sha(p) for p in before},"Existing input changed")
            rows.append({"control":name,"status":"passed","source_sha256":sha(source),"input_snapshot_sha256":sha(receipt),
                         "packet_sha256":sha(packet),"packet_bytes":packet.stat().st_size,"member_count":member_count,"gain_status":status,
                         "severe_loss_detected":loss,"source_rms_linear":primary["rms_linear"],"mono_rms_linear":mono["rms_linear"],
                         "inputs_unchanged":True,"cli_statuses":[r["status"] for r in outputs],"elapsed_seconds":round(time.perf_counter()-tick,3)})
    receipt={"schema":"coda.resonance-commons.shared-packet-validation.v1","status":"passed","captured_at_utc":datetime.now(timezone.utc).isoformat(),
             "builder_version":"0.1.0","python":sys.version.split()[0],"platform":sys.platform,
             "unit_tests":{"run":result.testsRun,"passed":result.testsRun-len(result.skipped),"failures":len(result.failures),"errors":len(result.errors),
                           "skips":[{"test":str(t),"reason":reason} for t,reason in result.skipped]},
             "integration_controls":rows,"preserved_existing_inputs":True,"no_model_decoder_network_or_wsl_execution":True,
             "scope":"Builder consistency/integrity and bounded synthetic packet checks; no musical-quality or provider-audio capability claim",
             "elapsed_seconds":round(time.perf_counter()-started,3),"source_files":[{"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)}
                         for p in [script,root/"tests/test_packet.py",root/"README.md",root/"NOTICE.txt",Path(__file__).resolve()]]}
    with output.open("x",encoding="utf-8") as file:
        json.dump(receipt,file,indent=2,allow_nan=False);file.write("\n")
    print(json.dumps({"status":"passed","receipt":output.name,"sha256":sha(output),"unit_tests":receipt["unit_tests"],"integration_controls_passed":len(rows)}))


if __name__=="__main__":
    main()
