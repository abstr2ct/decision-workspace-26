import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from strategist import core, dashboard, retrieval
from strategist.ingest import InputError
from strategist.mcp_server import Session

ROOT = Path(__file__).resolve().parents[1]


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)/'p'
        core.init_project(self.p, 'New task', 'Why is retention declining?')
        core.source_add(self.p, 'cohort-notes', b'Retention depends on the observation window. Cost and revenue are not profit.', '.txt', 'Retention notes')
        core.claim_add(self.p, {'id':'observation','type':'fact','text':'The notes discuss retention windows.',
                               'evidence':[{'source':'cohort-notes','locator':'line:1','quote':'observation window'}],
                               'confidence':'low','confidence_reason':'Own note, not empirical proof'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_bilingual_retrieval_and_claim_links(self):
        result = retrieval.retrieve(self.p, 'удержание')
        self.assertIn('retention', result['concepts'])
        self.assertIn('observation', result['hits'][0]['claim_links'])

    def test_retrieval_omits_withdrawn_sources(self):
        core.source_status(self.p,'cohort-notes',reason='Withdrawn')
        self.assertEqual(retrieval.retrieve(self.p,'retention')['hits'],[])

    def test_context_budget_and_no_raw_source_loading(self):
        packet = retrieval.context_packet(self.p,1500)
        self.assertLessEqual(packet['characters'],1500)
        self.assertEqual(packet['packet']['revision'],core.load(self.p)['revision'])
        self.assertNotIn('untrusted_content',json.dumps(packet))

    def test_context_has_explicit_omission_when_large(self):
        for n in range(20):
            core.claim_add(self.p,{'id':f'h{n}','type':'hypothesis','text':'Possible barrier '*40,'evidence':[],
                                  'confidence':'low','confidence_reason':'Unconfirmed'})
        self.assertGreater(retrieval.context_packet(self.p,2000)['omitted_claims'],0)

    def test_impact_preview_does_not_mutate(self):
        before=(self.p/'state.json').read_bytes()
        result=retrieval.impact(self.p,'cohort-notes')
        self.assertEqual(result['affected_claims'],['observation'])
        self.assertEqual(before,(self.p/'state.json').read_bytes())

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(InputError):
            core.project_file(self.p,'../secret.txt')
        with self.assertRaises(InputError):
            core.project_file(self.p,str(self.p/'state.json'))

    def test_audit_rejects_tampered_source_path_without_reading_outside(self):
        s=core.load(self.p)
        s['sources']['cohort-notes']['blob']='../outside.txt'
        core.atomic_write(self.p/'state.json',core.canonical(s))
        self.assertTrue(any('escapes project' in x for x in core.audit(self.p)['errors']))

    def test_dashboard_escapes_source_markup(self):
        payload='<script>alert("pwned")</script><img src=x onerror=alert(1)>'
        core.source_add(self.p,'hostile',payload.encode(),'.txt',payload)
        path=dashboard.generate(self.p,core.load(self.p),core.audit(self.p))
        html=path.read_text(encoding='utf-8')
        self.assertNotIn(payload,html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('Content-Security-Policy',html)

    def test_mcp_lifecycle(self):
        session=Session(self.p)
        self.assertIn('error',session.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'}))
        init=session.handle({'jsonrpc':'2.0','id':2,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}})
        self.assertEqual(init['result']['protocolVersion'],'2025-11-25')
        self.assertIsNone(session.handle({'jsonrpc':'2.0','method':'notifications/initialized'}))
        tools=session.handle({'jsonrpc':'2.0','id':3,'method':'tools/list'})['result']['tools']
        self.assertEqual(len(tools),7)
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in tools))

    def test_mcp_roundtrip_in_fresh_subprocess(self):
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'strategy_search','arguments':{'query':'удержание'}}}]
        before=(self.p/'state.json').read_bytes()
        p=subprocess.run([sys.executable,'-X','utf8','-m','strategist.mcp_server','--project',str(self.p)],cwd=ROOT,
                         input='\n'.join(json.dumps(r) for r in requests)+'\n',capture_output=True,encoding='utf-8')
        self.assertEqual(p.returncode,0,p.stderr)
        messages=[json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(messages),2)
        self.assertFalse(messages[-1]['result']['isError'])
        self.assertTrue(messages[-1]['result']['structuredContent']['hits'])
        self.assertEqual(before,(self.p/'state.json').read_bytes())

    def test_mcp_rejects_project_override_and_invalid_types(self):
        session=Session(self.p)
        with self.assertRaises(InputError):
            session.call_tool('strategy_resume',{'project':'../other'})
        with self.assertRaises(InputError):
            session.call_tool('strategy_context',{'max_chars':True})

    def test_source_state_cannot_be_reimported_as_evidence(self):
        p=subprocess.run([sys.executable,'-X','utf8','-m','strategist','source','add',str(self.p),str(self.p/'state.json'),
                          '--id','laundered','--title','Previous state'],cwd=ROOT,capture_output=True,encoding='utf-8')
        self.assertEqual(p.returncode,2)
        self.assertIn('cannot be imported',p.stderr)

    def test_access_challenge_is_not_article(self):
        from strategist.ingest import reject_access_challenge
        with self.assertRaises(InputError):
            reject_access_challenge(b'<html><title>Client Challenge</title><p>Enable cookies</p></html>')
        reject_access_challenge(b'<title>How to diagnose a CAPTCHA</title><p>A normal article</p>')

    def test_approval_actor_tampering_is_reported(self):
        from demo.fixtures import BRIEF
        core.commit_document(self.p,'brief',BRIEF)
        core.approve(self.p,'brief','owner','Explicit fixture consent')
        state=core.load(self.p);state['approvals']['brief']['actor']='Different actor'
        core.atomic_write(self.p/'state.json',core.canonical(state))
        self.assertTrue(any('does not match its recorded event' in err for err in core.audit(self.p)['errors']))

    def test_carry_forward_keeps_previous_decision_in_event(self):
        import shutil
        from contextlib import redirect_stdout
        from strategist.cli import main
        complete=Path(self.tmp.name)/'complete'
        shutil.copytree(ROOT/'examples'/'replay',complete)
        state=core.load(complete);old=state['commitments']['check-demand']['decision_hash']
        core.propose(complete,'focus','New bounded rationale',['teams-retention'])
        core.approve(complete,'decision','SCENARIO:owner','Fixture repeated consent',simulation=True)
        with redirect_stdout(io.StringIO()):
            code=main(['commitment','carry-forward',str(complete),'check-demand','--reason','Still required'])
        self.assertEqual(code,0)
        state=core.load(complete)
        self.assertNotEqual(old,state['commitments']['check-demand']['decision_hash'])
        self.assertEqual(state['events'][-1]['detail']['previous_decision_hash'],old)

