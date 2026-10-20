"""Rerun bounded local source tests and public CLI checks, with sanitized output."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def tests(relative):
    path=ROOT/relative
    spec=importlib.util.spec_from_file_location('validation_'+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    return {'source':relative,'tests_run':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
            'skipped':[{'test':case.id().split('.')[-1],'reason':reason} for case,reason in result.skipped],
            'failures':[case.id().split('.')[-1] for case,_ in result.failures],
            'errors':[case.id().split('.')[-1] for case,_ in result.errors],'successful':result.wasSuccessful()}


def main():
    suites=[tests('shared/tests/test_packet.py'),tests('tests/test_routes.py')]
    if not all(s['successful'] for s in suites):raise RuntimeError('Source tests failed')
    demo=ROOT/'shared/demo/resonance-commons-case-001-evidence.zip';demo_sha=sha(demo.read_bytes())
    cli=ROOT/'tools/route_adapter.py';rows=[]
    with tempfile.TemporaryDirectory(prefix='resonance-staging-cli-') as temp:
        base=Path(temp)
        def command(args):
            proc=subprocess.run([sys.executable,'-I','-B',str(cli),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=30)
            if proc.returncode!=0:raise RuntimeError('Bounded public CLI validation failed')
            return json.loads(proc.stdout)
        for route in ('grokbot','muse','chatgpt-6-pro','claude-opus-5-5','codex-local'):
            checked=command(['check','--adapter',route,'--packet',demo,'--sha256',demo_sha])
            path=base/(route+'-handoff.zip')
            prepared=command(['prepare','--adapter',route,'--packet',demo,'--sha256',demo_sha,'--output',path])
            with zipfile.ZipFile(path) as archive:template=archive.read('response-template.json')
            response=base/(route+'-response.json');response.write_bytes(template)
            validated=command(['validate-response','--handoff',path,'--sha256',sha(path.read_bytes()),'--response',response])
            if prepared['status']!='prepared-not-sent' or validated['measurement_claims']!=0:raise RuntimeError('Unexpected CLI status')
            rows.append({'adapter_id':route,'check_command_passed':True,'prepare_command_passed':True,'validate_unavailable_response_passed':True,
                         'configured_route_readiness':checked['configured_route_readiness'],'blocked_gates':checked['blocked_gates'],
                         'handoff_bytes':path.stat().st_size,'handoff_sha256':sha(path.read_bytes()),'provider_contacted':False,
                         'native_audio_verified':False,'delivery_status':'prepared-not-sent; temporary local test file removed'})
    manifest=json.loads((ROOT/'shared/FILES.sha256.json').read_bytes())
    rows_manifest=manifest['files']
    for row in rows_manifest:
        data=(ROOT/'shared'/row['path']).read_bytes()
        if sha(data)!=row['sha256'] or len(data)!=row['bytes']:raise RuntimeError('Frozen shared source differs')
    record={'schema':'resonance-commons.staging-validation.v1','date':'2026-10-20','python_version':sys.version.split()[0],
            'platform':sys.platform,'scope':'Local standard-library tests and CLI only; no provider contacted, no model executed, no network or dependency installation',
            'source_suites':suites,'public_cli_routes':rows,'shared_frozen_manifest_verified':True,'shared_frozen_files_checked':len(rows_manifest),
            'demo':{'path':'shared/demo/resonance-commons-case-001-evidence.zip','bytes':demo.stat().st_size,'sha256':demo_sha},
            'tested_source':[{'path':rel,'sha256':sha((ROOT/rel).read_bytes())} for rel in ('shared/evidence_packet.py','tools/route_adapter.py','tests/test_routes.py','validation/validate_staging.py')],
            'limitations':['Current route observation fields are caller testimony, not backend attestation.',
                           'Interpretation truth and musical quality are not established by response validation.',
                           'No remote adapter execution, native audio, model or Music Geometry capability is established.',
                           'Historical session and runtime observations require a fresh capability check per packet.']}
    out=ROOT/'validation/staging-validation.json'
    with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'status':'passed','source_tests_run':sum(s['tests_run'] for s in suites),'source_tests_passed':sum(s['passed'] for s in suites),
                      'skipped':sum(len(s['skipped']) for s in suites),'routes':len(rows),'receipt':'validation/staging-validation.json','sha256':sha(out.read_bytes())}))


if __name__=='__main__':main()
