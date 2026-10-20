"""Offline adapter contract tests using bounded analytic and synthetic fixtures."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('routes_under_test',ROOT/'tools/route_adapter.py')
ra=importlib.util.module_from_spec(spec);spec.loader.exec_module(ra)
spec=importlib.util.spec_from_file_location('analytic_fixture',ROOT/'shared/tests/test_packet.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def repack(data,changes):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        payload={n:archive.read(n) for n in archive.namelist()}
    changes(payload)
    manifest=ra.ep.strict_json(payload['handoff-manifest.json'])
    manifest['files']=[{'path':n,'bytes':len(b),'sha256':ra.ep.digest(b)} for n,b in sorted(payload.items()) if n!='handoff-manifest.json']
    payload['handoff-manifest.json']=ra.ep.canonical(manifest)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for n,b in sorted(payload.items()):
            info=zipfile.ZipInfo(n,date_time=(2026,1,1,0,0,0));info.create_system=3;info.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(info,b)
    return output.getvalue()


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo=(ROOT/'shared/demo/resonance-commons-case-001-evidence.zip').read_bytes()
        cls.sha=ra.ep.digest(cls.demo)
        cls.ledger=ra.ep.verify_packet_bytes(cls.demo)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='resonance-route-test-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def observed(self,route):
        p=ra.profile(route);obs=ra.observation_template(p,self.ledger,self.sha)
        for key in ('route_access','evidence_loaded','new_dedicated_thread','metric_basis_confirmed'):obs[key]=True
        obs['observed_model_label']=p['accepted_model_labels'][0] if p['accepted_model_labels'] else None
        return p,obs

    def handoff(self,route='codex-local',filename='handoff.zip'):
        p=ra.profile(route);dest=self.root/filename
        result=ra.prepare(p,self.ledger,self.demo,dest)
        data=dest.read_bytes()
        self.assertEqual(result['status'],'prepared-not-sent');self.assertFalse(result['provider_contacted'])
        return data,ra.verify_handoff(data)

    def response(self,route='codex-local'):
        _,(p,ledger,req)=self.handoff(route)
        response=ra.response_template(p,ledger,self.sha)
        response['status']='completed';response['coverage']['signal_evidence']='completed';response['modalities_used']=['numeric']
        response['observed_model_label']=p['accepted_model_labels'][0] if p['accepted_model_labels'] else None
        metric=req['metric_catalog']['source.rms_linear']
        response['claims']=[{'id':'claim-01','kind':'measurement','metric_id':'source.rms_linear','value':metric['value'],'unit':metric['unit'],
                             'signal_basis':metric['signal_basis'],'evidence_ids':[metric['evidence_id']],'start_seconds':0,
                             'end_seconds':req['duration_seconds'],'source_channel_indices':metric['source_channel_indices']}]
        return p,ledger,req,response

    def test_distinct_route_snapshots_and_offline_readiness(self):
        checks=[]
        for route in ra.ROUTES:
            p=ra.profile(route);result=ra.capability_check(p,self.ledger,self.sha)
            self.assertEqual(result['configured_route_readiness'],route=='codex-local')
            self.assertTrue(result['offline_handoff_authoring_ready']);self.assertFalse(result['native_audio_verified']);self.assertFalse(result['provider_contacted'])
            ra.validate_readiness(p,self.ledger,self.sha,result);checks.append(p['route_label'])
        self.assertEqual(len(set(checks)),5)

    def test_exact_model_and_new_thread_gates(self):
        for route in ('chatgpt-6-pro','claude-opus-5-5'):
            p,obs=self.observed(route)
            self.assertTrue(ra.capability_check(p,self.ledger,self.sha,obs)['configured_route_readiness'])
            obs['observed_model_label']='Different Model'
            self.assertIn('exact_model',ra.capability_check(p,self.ledger,self.sha,obs)['blocked_gates'])
        p,obs=self.observed('chatgpt-6-pro');obs['new_dedicated_thread']=False
        self.assertEqual(ra.capability_check(p,self.ledger,self.sha,obs)['blocked_gates'],['new_dedicated_thread'])

    def test_muse_requires_metric_basis_confirmation(self):
        p,obs=self.observed('muse');obs['metric_basis_confirmed']=False
        self.assertEqual(ra.capability_check(p,self.ledger,self.sha,obs)['blocked_gates'],['metric_basis_confirmed'])
        self.assertIn('Python 3.12.3',p['runtime']);self.assertIn('3.13-specific binary wheels are incompatible',p['runtime'])

    def test_observation_source_route_and_boolean_refused(self):
        p,obs=self.observed('muse')
        for key,value in [('source_sha256','0'*64),('adapter_id','grokbot'),('packet_sha256','0'*64),('route_access',1)]:
            with self.subTest(key=key):
                bad=copy.deepcopy(obs);bad[key]=value
                with self.assertRaises(ra.ep.Refusal):ra.capability_check(p,self.ledger,self.sha,bad)

    def test_attachment_or_runtime_bytes_never_upgrade_native_audio(self):
        p,obs=self.observed('muse')
        for status in ('attachment_accepted','runtime_bytes_verified'):
            obs['audio_input_status']=status
            self.assertFalse(ra.capability_check(p,self.ledger,self.sha,obs)['native_audio_verified'])
        obs['audio_input_status']='native_processing_verified'
        with self.assertRaises(ra.ep.Refusal):ra.capability_check(p,self.ledger,self.sha,obs)

    def test_five_handoffs_are_deterministic_and_source_bound(self):
        for route in ra.ROUTES:
            with self.subTest(route=route):
                a,(p,ledger,req)=self.handoff(route,route+'-a.zip')
                b,_=self.handoff(route,route+'-b.zip');self.assertEqual(a,b)
                self.assertEqual(req['source_sha256'],self.ledger['source']['sha256'])
                self.assertFalse(req['audio_included']);self.assertEqual(req['status'],'prepared-not-sent')

    def test_input_packet_hash_refused(self):
        path=self.root/'evidence.zip';path.write_bytes(self.demo)
        with self.assertRaises(ra.ep.Refusal):ra.packet(path,'0'*64)

    def test_occupied_output_preserves_sentinel(self):
        path=self.root/'existing.zip';path.write_bytes(b'sentinel')
        with self.assertRaises(ra.ep.Refusal):ra.prepare(ra.profile('muse'),self.ledger,self.demo,path)
        self.assertEqual(path.read_bytes(),b'sentinel')
        self.assertEqual(sorted(x.name for x in self.root.iterdir()),['existing.zip'])

    def test_tampered_instructions_or_catalog_refused_even_if_rehashed(self):
        data,_=self.handoff()
        bad=repack(data,lambda p:p.update({'route-instructions.txt':b'Invent listening'}))
        with self.assertRaises(ra.ep.Refusal):ra.verify_handoff(bad)
        def change(payload):
            req=ra.ep.strict_json(payload['request.json']);req['metric_catalog']['source.rms_linear']['value']=.987
            payload['request.json']=ra.ep.canonical(req)
        with self.assertRaises(ra.ep.Refusal):ra.verify_handoff(repack(data,change))

    def test_forged_readiness_refused(self):
        data,_=self.handoff('muse')
        def change(payload):
            req=ra.ep.strict_json(payload['request.json']);req['readiness']['configured_route_readiness']=True
            payload['request.json']=ra.ep.canonical(req)
        with self.assertRaises(ra.ep.Refusal):ra.verify_handoff(repack(data,change))

    def analytic_packet(self):
        report,source,_=fixture.make_fixture(self.root)
        _,_,receipt=ra.ep.report_snapshot(report,source)
        pin=self.root/'pin.json';pin.write_bytes(ra.ep.canonical(receipt));path=self.root/'analytic.zip'
        ra.ep.build_packet(report,source,pin,ra.ep.digest(pin.read_bytes()),path,'Resonance Commons','case-001')
        data=path.read_bytes();return source,data,ra.ep.verify_packet_bytes(data)

    def test_exact_optional_audio_allowed_only_two_routes(self):
        source,data,ledger=self.analytic_packet()
        for route in ra.ROUTES:
            path=self.root/(route+'.zip')
            if route in ('muse','codex-local'):
                ra.prepare(ra.profile(route),ledger,data,path,audio=source)
                p,l,req=ra.verify_handoff(path.read_bytes());self.assertTrue(req['audio_included'])
                self.assertIn('source-audio-bytes',req['modalities_supplied'])
                self.assertFalse(req['readiness']['native_audio_verified'])
            else:
                with self.assertRaises(ra.ep.Refusal):ra.prepare(ra.profile(route),ledger,data,path,audio=source)
                self.assertFalse(path.exists())

    def test_different_audio_bytes_refused(self):
        source,data,ledger=self.analytic_packet();source.write_bytes(fixture.wav_bytes(2,[0]*640))
        with self.assertRaises(ra.ep.Refusal):ra.prepare(ra.profile('muse'),ledger,data,self.root/'out.zip',audio=source)
        self.assertFalse((self.root/'out.zip').exists())

    def test_exact_measurement_response_accepted_without_hearing_claim(self):
        p,l,req,response=self.response();result=ra.validate_response(p,l,req,response)
        self.assertEqual(result['measurement_claims'],1);self.assertFalse(result['semantic_truth_validated']);self.assertFalse(result['native_audio_verified'])

    def test_wrong_measurement_value_basis_channel_and_span_refused(self):
        p,l,req,response=self.response()
        for key,value in [('value',.12345),('signal_basis',ra.ep.MONO_BASIS),('source_channel_indices',[0]),('start_seconds',.1),('unit','dB')]:
            with self.subTest(key=key):
                bad=copy.deepcopy(response);bad['claims'][0][key]=value
                with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,bad)

    def test_wrong_model_source_and_native_claim_refused(self):
        p,l,req,response=self.response('chatgpt-6-pro')
        for key,value in [('observed_model_label','5.6 Pro'),('source_sha256','0'*64),('native_audio_claim',True)]:
            bad=copy.deepcopy(response);bad[key]=value
            with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,bad)

    def test_unavailable_and_coverage_consistency(self):
        p,l,req,response=self.response()
        for key in ('musical_inference','asr','learned_events','native_audio'):
            bad=copy.deepcopy(response);bad['coverage'][key]='completed'
            with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,bad)
        response['coverage']['signal_evidence']='unavailable'
        with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,response)
        empty=ra.response_template(p,l,self.sha);self.assertEqual(ra.validate_response(p,l,req,empty)['measurement_claims'],0)

    def test_unsupported_modality_and_empty_completed_response_refused(self):
        p,l,req,response=self.response()
        for modes in (['native-audio'],['source-audio-bytes'],[]):
            bad=copy.deepcopy(response);bad['modalities_used']=modes
            with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,bad)
        response['claims']=[]
        with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,response)

    def test_interpretation_is_bounded_but_semantically_unverified(self):
        p,l,req,response=self.response()
        response['claims']=[{'id':'claim-01','kind':'interpretation','text':'One channel contains more measured energy.','uncertainty':'Signal observation only; no instrument identification.',
                             'evidence_ids':['source-pcm16'],'start_seconds':0,'end_seconds':req['duration_seconds'],'source_channel_indices':[0,1]}]
        result=ra.validate_response(p,l,req,response)
        self.assertEqual(result['interpretation_claims'],1);self.assertFalse(result['semantic_truth_validated'])
        for key,value in [('end_seconds',float('nan')),('source_channel_indices',[2]),('evidence_ids',['invented-evidence']),('uncertainty','')]:
            bad=copy.deepcopy(response);bad['claims'][0][key]=value
            with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,bad)

    def test_follow_up_remains_source_bound_proposal(self):
        p,l,req,response=self.response()
        proposal=ra.ep.strict_json((ROOT/'shared/demo/follow-up-example.json').read_bytes())
        response['follow_up']=proposal
        self.assertFalse(ra.validate_response(p,l,req,response)['provider_contacted'])
        response['follow_up']['source_sha256']='0'*64
        with self.assertRaises(ra.ep.Refusal):ra.validate_response(p,l,req,response)


if __name__=='__main__':unittest.main(verbosity=2)
