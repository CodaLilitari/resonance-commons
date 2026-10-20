#!/usr/bin/env python3
"""Offline route capability checks, immutable handoffs and response validation.

No provider is contacted. Configured observations are not backend attestation.
"""
from __future__ import annotations
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import stat
import sys
import wave
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("shared_evidence_packet",ROOT/"shared/evidence_packet.py")
ep=importlib.util.module_from_spec(spec);spec.loader.exec_module(ep)
ROUTES=("grokbot","muse","chatgpt-6-pro","claude-opus-5-5","codex-local")
CAPABILITIES=("signal_evidence","musical_inference","asr","learned_events","native_audio")
LIMIT=10*1024**2
NO_OBSERVATION="No current route observation supplied; historical snapshot does not establish readiness for this packet"
CALLER_OBSERVATION="Caller-supplied current observation, structurally checked and source-bound; not independently attested by this CLI"


def profile(route):
    ep.require(route in ROUTES,"Unknown route")
    p=ep.strict_json(ep.read_bytes(ROOT/"adapters"/route/"profile.json",32768))
    ep.require(p["schema"]=="resonance-commons.route-profile.v1" and p["version"]=="0.1.0" and p["adapter_id"]==route,"Profile identity mismatch")
    ep.require(p["claims"]["native_audio_processing_enabled"] is False,"Native audio is not enabled in this release")
    ep.require(set(p["required_readiness_gates"]) <= {"route_access","evidence_loaded","metric_basis_confirmed","exact_model","new_dedicated_thread","local_runtime"},"Unknown readiness gate")
    return p


def packet(path,expected):
    data=ep.read_bytes(path,LIMIT)
    ep.require(ep.SHA_RE.fullmatch(expected) and ep.digest(data)==expected,"Packet hash mismatch")
    return data,ep.verify_packet_bytes(data)


def observation_template(p,ledger,packet_sha):
    return {"schema":"resonance-commons.route-observation.v1","adapter_id":p["adapter_id"],"route_label":p["route_label"],
            "packet_sha256":packet_sha,"source_sha256":ledger["source"]["sha256"],"observed_model_label":None,
            "route_access":False,"evidence_loaded":False,"new_dedicated_thread":False,"metric_basis_confirmed":False,
            "audio_input_status":"not_supplied"}


def capability_check(p,ledger,packet_sha,observation=None):
    gates={key:False for key in p["required_readiness_gates"]}
    if "local_runtime" in gates:gates["local_runtime"]=sys.version_info >= (3,11)
    attestation=NO_OBSERVATION
    if observation is not None:
        expected=observation_template(p,ledger,packet_sha)
        ep.require(isinstance(observation,dict) and set(observation)==set(expected),"Observation fields mismatch")
        for key in ("schema","adapter_id","route_label","packet_sha256","source_sha256"):
            ep.require(observation[key]==expected[key],"Observation route/source/packet mismatch")
        for key in ("route_access","evidence_loaded","new_dedicated_thread","metric_basis_confirmed"):
            ep.require(type(observation[key]) is bool,"Observation gate must be boolean")
            if key in gates:gates[key]=observation[key]
        label=observation["observed_model_label"]
        ep.require(label is None or isinstance(label,str) and re.fullmatch(r"[A-Za-z0-9 ._-]{1,80}",label),"Invalid observed model label")
        ep.require(observation["audio_input_status"] in ("not_supplied","attachment_accepted","runtime_bytes_verified"),"Unsupported audio processing claim")
        if "exact_model" in gates:gates["exact_model"]=label in p["accepted_model_labels"]
        attestation=CALLER_OBSERVATION
    return {"schema":"resonance-commons.capability-check.v1","adapter_id":p["adapter_id"],"packet_sha256":packet_sha,
            "source_sha256":ledger["source"]["sha256"],"offline_handoff_authoring_ready":True,
            "configured_route_readiness":all(gates.values()),"readiness_gates":gates,
            "blocked_gates":[key for key,value in gates.items() if not value],"attestation":attestation,
            "historical_snapshot":p["snapshot"],"native_audio_verified":False,
            "provider_contacted":False,"python_version":sys.version.split()[0] if p["adapter_id"]=="codex-local" else None}


def validate_readiness(p,ledger,packet_sha,value):
    expected=capability_check(p,ledger,packet_sha)
    ep.require(isinstance(value,dict) and set(value)==set(expected),"Readiness fields mismatch")
    variable={"configured_route_readiness","readiness_gates","blocked_gates","attestation","python_version"}
    for key in set(expected)-variable:ep.require(value[key]==expected[key],"Readiness identity/status mismatch")
    gates=value["readiness_gates"]
    ep.require(isinstance(gates,dict) and set(gates)==set(p["required_readiness_gates"]) and all(type(v) is bool for v in gates.values()),"Readiness gates mismatch")
    ep.require(type(value["configured_route_readiness"]) is bool and value["configured_route_readiness"]==all(gates.values()),"Readiness result mismatch")
    ep.require(value["blocked_gates"]==[key for key in p["required_readiness_gates"] if not gates[key]],"Readiness blocked gates mismatch")
    ep.require(value["attestation"] in (NO_OBSERVATION,CALLER_OBSERVATION),"Unsupported readiness attestation")
    if value["attestation"]==NO_OBSERVATION:
        ep.require(all(not flag for key,flag in gates.items() if key!="local_runtime"),"Historical snapshot cannot establish remote readiness")
    version=value["python_version"]
    ep.require(isinstance(version,str) and re.fullmatch(r"[0-9.]{3,30}",version) if p["adapter_id"]=="codex-local" else version is None,"Invalid runtime observation")


def metrics(ledger):
    primary=ledger["measurements"]["source_pcm16"];mono=ledger["measurements"]["mono_derivative_pcm16"]
    ep.require(isinstance(primary.get("channels"),list) and len(primary["channels"])==primary["channel_count"],"Ledger channel rows mismatch")
    for i,row in enumerate(primary["channels"]):
        ep.require(isinstance(row,dict) and type(row.get("channel_index")) is int and row["channel_index"]==i,"Ledger channel order mismatch")
    channels=list(range(primary["channel_count"]))
    def row(value,unit,basis,indices,evidence):
        return {"value":value,"unit":unit,"signal_basis":basis,"source_channel_indices":indices,"evidence_id":evidence}
    result={"source.rms_linear":row(primary["rms_linear"],"linear_fs",ep.SOURCE_BASIS,channels,"source-pcm16"),
            "source.sample_peak_linear":row(primary["sample_peak_linear"],"linear_fs",ep.SOURCE_BASIS,channels,"source-pcm16"),
            "source.silence_ratio":row(primary["silence"]["ratio"],"ratio",ep.SOURCE_BASIS,channels,"source-pcm16"),
            "mono.rms_linear":row(mono["rms_linear"],"linear_fs",ep.MONO_BASIS,channels,"mono-derivative"),
            "mono.gain_db_vs_strongest_source_channel":row(ledger["transforms"][1]["gain_db_relative_to_strongest_source_channel"],"dB",ep.MONO_BASIS,channels,"mono-derivative")}
    for ch in primary["channels"]:
        for key,unit in [("rms_linear","linear_fs"),("sample_peak_linear","linear_fs"),("near_pcm16_rail_ratio","ratio")]:
            result[f"source.channel.{ch['channel_index']}.{key}"]=row(ch[key],unit,ep.SOURCE_BASIS,[ch["channel_index"]],"source-pcm16")
    return result


def response_template(p,ledger,packet_sha):
    return {"schema":"resonance-commons.route-response.v1","adapter_id":p["adapter_id"],"packet_sha256":packet_sha,
            "source_sha256":ledger["source"]["sha256"],"observed_model_label":None,"status":"unavailable",
            "native_audio_claim":False,"modalities_used":[],"claims":[],
            "coverage":{key:"unavailable" for key in CAPABILITIES},"follow_up":None}


def request(p,ledger,packet_sha,with_audio,readiness):
    return {"schema":"resonance-commons.route-request.v1","adapter_id":p["adapter_id"],"route_label":p["route_label"],
            "accepted_model_labels":p["accepted_model_labels"],"packet_sha256":packet_sha,"source_sha256":ledger["source"]["sha256"],
            "status":"prepared-not-sent","readiness":readiness,"audio_included":with_audio,
            "modalities_supplied":["numeric","text","plots"]+(["source-audio-bytes"] if with_audio else []),
            "task":"Describe the signal evidence, channel differences, silence intervals and mono transform. Separate interpretation from measured values. Request missing evidence instead of inventing music/model output.",
            "metric_catalog":metrics(ledger),"time_basis":ep.TIME_BASIS,
            "duration_seconds":ledger["time"]["decoded_stream_end_seconds_exclusive"],
            "claim_contract":{"maximum_claims":16,"measurement_fields":["id","kind","metric_id","value","unit","signal_basis","evidence_ids","start_seconds","end_seconds","source_channel_indices"],
                              "interpretation_fields":["id","kind","text","uncertainty","evidence_ids","start_seconds","end_seconds","source_channel_indices"],
                              "measurement_scope":"Catalog values cover the full decoded source duration; do not assign them to a narrower window",
                              "interpretation_scope":"Evidence-bound hypotheses; semantic truth is not mechanically validated"},
            "follow_up_contract":ep.follow_up_contract(ledger),"response_template":"response-template.json"}


def prepare(p,ledger,data,output,observation=None,audio=None):
    packet_sha=ep.digest(data)
    readiness=capability_check(p,ledger,packet_sha,observation)
    payload={"evidence.zip":data,"profile.json":ep.canonical(p),
             "route-instructions.txt":ep.read_bytes(ROOT/"adapters"/p["adapter_id"]/"instructions.txt",32768),
             "observation-template.json":ep.canonical(observation_template(p,ledger,packet_sha)),
             "response-template.json":ep.canonical(response_template(p,ledger,packet_sha))}
    if audio is not None:
        ep.require(p["handoff"]["optional_source_wav"] is True,"This route's source-WAV path is not enabled")
        b=ep.read_bytes(audio,LIMIT)
        ep.require(ep.digest(b)==ledger["source"]["sha256"] and len(b)==ledger["source"]["bytes"],"Audio differs from exact ledger source")
        _,n,sr,frames=ep.pcm(b)
        original=ledger["source"]["original_stream_probe"]
        ep.require((n,sr)==(original["channels"],original["sample_rate_hz"]) and frames/sr<=30,"Original WAV dimensions differ from probe")
        payload["source.wav"]=b
    payload["request.json"]=ep.canonical(request(p,ledger,packet_sha,audio is not None,readiness))
    manifest={"schema":"resonance-commons.route-handoff.v1","adapter_id":p["adapter_id"],"status":"prepared-not-sent",
              "files":[{"path":n,"bytes":len(b),"sha256":ep.digest(b)} for n,b in sorted(payload.items())]}
    payload["handoff-manifest.json"]=ep.canonical(manifest)
    ep.require(sum(map(len,payload.values()))<LIMIT-4096,"Handoff exceeds total project budget")
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_STORED) as archive:
        for n,b in sorted(payload.items()):
            info=zipfile.ZipInfo(n,date_time=(2026,1,1,0,0,0));info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(info,b)
    ep.require(len(buffer.getvalue())<=LIMIT,"Handoff exceeds 10 MiB")
    verify_handoff(buffer.getvalue())
    result=ep.publish_new(output,buffer.getvalue(),protected=[ROOT/x for x in ("shared","adapters","tools","tests","publication")])
    return {"status":"prepared-not-sent","adapter_id":p["adapter_id"],"provider_contacted":False,**result}


def verify_handoff(data):
    ep.require(len(data)<=LIMIT,"Handoff exceeds bounds")
    required={"evidence.zip","profile.json","route-instructions.txt","observation-template.json","response-template.json","request.json","handoff-manifest.json"}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        items=archive.infolist();names={x.filename for x in items}
        ep.require(names in (required,required|{"source.wav"}) and len(items)==len(names),"Handoff member names/duplicates refused")
        ep.require(sum(x.file_size for x in items)<=LIMIT,"Handoff payload exceeds bounds")
        for x in items:ep.require(x.compress_type==zipfile.ZIP_STORED and not x.flag_bits&1 and stat.S_ISREG(x.external_attr>>16),"Unsupported handoff member")
        payload={x.filename:archive.read(x) for x in items}
    manifest=ep.strict_json(payload["handoff-manifest.json"])
    ep.require(manifest["schema"]=="resonance-commons.route-handoff.v1" and manifest["status"]=="prepared-not-sent","Handoff schema/status mismatch")
    ep.require(manifest["files"]==[{"path":n,"bytes":len(b),"sha256":ep.digest(b)} for n,b in sorted(payload.items()) if n!="handoff-manifest.json"],"Handoff member hash mismatch")
    p=profile(manifest["adapter_id"])
    ep.require(payload["profile.json"]==ep.canonical(p),"Profile changed; prepare a fresh handoff")
    ep.require(payload["route-instructions.txt"]==ep.read_bytes(ROOT/"adapters"/p["adapter_id"]/"instructions.txt",32768),"Route instructions mismatch")
    ledger=ep.verify_packet_bytes(payload["evidence.zip"]);packet_sha=ep.digest(payload["evidence.zip"])
    req=ep.strict_json(payload["request.json"])
    ep.require(req["adapter_id"]==p["adapter_id"] and req["source_sha256"]==ledger["source"]["sha256"] and req["packet_sha256"]==packet_sha,"Handoff source/route mismatch")
    ep.require(req["metric_catalog"]==metrics(ledger) and req["follow_up_contract"]==ep.follow_up_contract(ledger),"Handoff evidence contract mismatch")
    ep.require(type(req["audio_included"]) is bool and req["audio_included"]==("source.wav" in payload),"Handoff audio status mismatch")
    validate_readiness(p,ledger,packet_sha,req["readiness"])
    ep.require(req==request(p,ledger,packet_sha,"source.wav" in payload,req["readiness"]),"Handoff request contract changed")
    if "source.wav" in payload:
        ep.require(p["handoff"]["optional_source_wav"] is True and ep.digest(payload["source.wav"])==ledger["source"]["sha256"],"Unexpected or mismatched audio")
        ep.pcm(payload["source.wav"])
    ep.require(payload["response-template.json"]==ep.canonical(response_template(p,ledger,packet_sha)) and payload["observation-template.json"]==ep.canonical(observation_template(p,ledger,packet_sha)),"Handoff template mismatch")
    return p,ledger,req


def validate_response(p,ledger,req,response):
    expected=response_template(p,ledger,req["packet_sha256"])
    ep.require(isinstance(response,dict) and set(response)==set(expected),"Response envelope mismatch")
    for key in ("schema","adapter_id","packet_sha256","source_sha256"):
        ep.require(response[key]==expected[key],"Response route/source binding mismatch")
    ep.require(response["native_audio_claim"] is False,"Native audio claim is unsupported")
    ep.require(response["status"] in ("completed","partial","unavailable"),"Unsupported response status")
    label=response["observed_model_label"]
    ep.require(label is None or isinstance(label,str) and re.fullmatch(r"[A-Za-z0-9 ._-]{1,80}",label),"Invalid response model label")
    if p["accepted_model_labels"] and response["status"]!="unavailable":
        ep.require(response["observed_model_label"] in p["accepted_model_labels"],"Wrong or unverified requested model")
    modes=response["modalities_used"]
    ep.require(isinstance(modes,list) and len(modes)<=4 and all(isinstance(x,str) and x in req["modalities_supplied"] for x in modes) and len(set(modes))==len(modes),"Unsupported response modality")
    coverage=response["coverage"]
    ep.require(isinstance(coverage,dict) and set(coverage)==set(CAPABILITIES),"Coverage fields mismatch")
    ep.require(coverage["signal_evidence"] in ("completed","partial","unavailable"),"Invalid signal coverage")
    ep.require(coverage["signal_evidence"]==response["status"],"Signal coverage and response status disagree")
    ep.require(all(coverage[x]=="unavailable" for x in CAPABILITIES if x!="signal_evidence"),"Unexecuted model/music capability upgraded")
    claims=response["claims"]
    ep.require(isinstance(claims,list) and len(claims)<=16,"Claim count exceeds bounds")
    ep.require(response["status"]!="unavailable" or claims==[],"Unavailable response cannot contain claims")
    ep.require(response["status"]=="unavailable" or len(claims)>0 and len(modes)>0,"Nonempty evidence required for completed/partial response")
    duration=ledger["time"]["decoded_stream_end_seconds_exclusive"];n=ledger["measurements"]["source_pcm16"]["channel_count"]
    evidence={e["id"] for e in ledger["evidence"]};seen=set()
    for claim in claims:
        ep.require(isinstance(claim,dict) and claim.get("kind") in ("measurement","interpretation"),"Invalid claim kind")
        fields=req["claim_contract"][claim["kind"]+"_fields"]
        ep.require(set(claim)==set(fields),"Claim fields mismatch")
        ep.require(isinstance(claim["id"],str) and re.fullmatch(r"claim-[0-9]{2}",claim["id"]) and claim["id"] not in seen,"Invalid/duplicate claim ID");seen.add(claim["id"])
        a=ep.number(claim["start_seconds"],0,duration);b=ep.number(claim["end_seconds"],0,duration)
        ep.require(a<b,"Invalid claim time range")
        indices=claim["source_channel_indices"]
        ep.require(isinstance(indices,list) and 1<=len(indices)<=n and all(type(i) is int and 0<=i<n for i in indices) and len(set(indices))==len(indices),"Invalid claim channel indices")
        refs=claim["evidence_ids"]
        ep.require(isinstance(refs,list) and 1<=len(refs)<=4 and all(isinstance(e,str) and e in evidence for e in refs) and len(set(refs))==len(refs),"Invalid claim evidence IDs")
        if claim["kind"]=="measurement":
            ep.require(claim["metric_id"] in req["metric_catalog"],"Unknown metric")
            metric=req["metric_catalog"][claim["metric_id"]]
            ep.same(claim["value"],metric["value"])
            ep.require(claim["unit"]==metric["unit"] and claim["signal_basis"]==metric["signal_basis"] and indices==metric["source_channel_indices"] and metric["evidence_id"] in refs,"Measurement basis/channel/evidence mismatch")
            ep.same(a,0);ep.same(b,duration)
        else:
            for key in ("text","uncertainty"):
                ep.require(isinstance(claim[key],str) and 1<=len(claim[key])<=1000 and not any(ord(c)<32 and c not in "\n\t" for c in claim[key]),"Interpretation text invalid")
    if response["follow_up"] is not None:ep.validate_follow_up(ledger,response["follow_up"])
    return {"status":"structure-and-value-bindings-accepted","adapter_id":p["adapter_id"],"measurement_claims":sum(c["kind"]=="measurement" for c in claims),
            "interpretation_claims":sum(c["kind"]=="interpretation" for c in claims),"semantic_truth_validated":False,"native_audio_verified":False,"provider_contacted":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True)
    for name in ("check","prepare"):
        cmd=sub.add_parser(name);cmd.add_argument("--adapter",required=True,choices=ROUTES);cmd.add_argument("--packet",required=True,type=Path);cmd.add_argument("--sha256",required=True);cmd.add_argument("--observation",type=Path)
        if name=="prepare":cmd.add_argument("--output",required=True,type=Path);cmd.add_argument("--audio",type=Path)
    cmd=sub.add_parser("validate-response");cmd.add_argument("--handoff",required=True,type=Path);cmd.add_argument("--sha256",required=True);cmd.add_argument("--response",required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=="validate-response":
        data=ep.read_bytes(args.handoff,LIMIT);ep.require(ep.SHA_RE.fullmatch(args.sha256) and ep.digest(data)==args.sha256,"Handoff external hash mismatch")
        p,ledger,req=verify_handoff(data);result=validate_response(p,ledger,req,ep.strict_json(ep.read_bytes(args.response,ep.MAX_JSON)))
    else:
        p=profile(args.adapter);data,ledger=packet(args.packet,args.sha256)
        obs=ep.strict_json(ep.read_bytes(args.observation,32768)) if args.observation else None
        result=capability_check(p,ledger,args.sha256,obs) if args.command=="check" else prepare(p,ledger,data,args.output,obs,args.audio)
    print(json.dumps(result,sort_keys=True,allow_nan=False));return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,zipfile.BadZipFile,wave.Error,zlib.error) as exc:
        reason=str(exc) if isinstance(exc,ep.Refusal) else "Input, contract or filesystem requirement failed"
        print(json.dumps({"status":"refused","error_type":type(exc).__name__,"reason":reason}),file=sys.stderr);raise SystemExit(2)
