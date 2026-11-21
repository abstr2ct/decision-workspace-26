import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from strategist import core, checkpoint, decision_card
from strategist.ingest import InputError

ROOT=Path(__file__).resolve().parents[1]


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'project'
        shutil.copytree(ROOT/'examples/replay',self.p)
        state=core.load(self.p)
        self.bundle={'base_revision':state['revision'], 'claims':[{'id':'new-uncertainty','type':'hypothesis',
                     'text':'Another explanation remains possible','evidence':[],'confidence':'low','confidence_reason':'Not observed'}],
                     'research':copy.deepcopy(state['documents']['research']['content']),
                     'options':copy.deepcopy(state['documents']['options']['content']),
                     'proposal':{'option_id':'focus','rationale':'New conditional recommendation requiring owner review','claims':['teams-retention']}}

    def tearDown(self):self.tmp.cleanup()

    def test_one_revision_and_no_invented_owner_approval(self):
        before=core.load(self.p)['revision']
        result=checkpoint.save(self.p,self.bundle)
        state=core.load(self.p)
        self.assertEqual(state['revision'],before+1)
        self.assertTrue(result['changed'])
        self.assertFalse(core.approved(state,'decision'))
        self.assertEqual(state['events'][-1]['kind'],'checkpoint_saved')

    def test_failed_late_validation_rolls_back_all_claims_and_documents(self):
        before=(self.p/'state.json').read_bytes()
        self.bundle['proposal']['claims']=['missing-claim']
        with self.assertRaises(InputError):checkpoint.save(self.p,self.bundle)
        self.assertEqual((self.p/'state.json').read_bytes(),before)
        self.assertNotIn('new-uncertainty',core.load(self.p)['claims'])
        self.assertFalse(list(self.p.glob('.checkpoint-*')))

    def test_retry_is_idempotent_and_old_revision_is_rejected_after_other_changes(self):
        checkpoint.save(self.p,self.bundle)
        before=(self.p/'state.json').read_bytes()
        self.assertFalse(checkpoint.save(self.p,self.bundle)['changed'])
        self.assertEqual((self.p/'state.json').read_bytes(),before)
        core.cost_add(self.p,'tool','0','RUB','0','Test only')
        with self.assertRaisesRegex(InputError,'Stale base_revision'):checkpoint.save(self.p,self.bundle)

    def test_approval_injection_is_rejected(self):
        self.bundle['approvals']={'decision':'approved'}
        with self.assertRaises(InputError):checkpoint.save(self.p,self.bundle)

    def test_pause_blocks_checkpoint(self):
        with core.transaction(self.p) as state:state['paused']=True
        with self.assertRaises(InputError):checkpoint.save(self.p,self.bundle)

    def test_final_atomic_write_failure_keeps_previous_state(self):
        before=(self.p/'state.json').read_bytes()
        original=core.atomic_write
        def write(path,data):
            if Path(path).resolve()==(self.p/'state.json').resolve():raise OSError('Simulated disk failure')
            return original(path,data)
        with patch.object(core,'atomic_write',side_effect=write):
            with self.assertRaises(OSError):checkpoint.save(self.p,self.bundle)
        self.assertEqual((self.p/'state.json').read_bytes(),before)
        self.assertFalse((self.p/'.write.lock').exists())

    def test_card_for_unapproved_proposal_is_explicit_and_does_not_mutate_state(self):
        checkpoint.save(self.p,self.bundle)
        before=(self.p/'state.json').read_bytes()
        result=decision_card.generate(self.p)
        packet=json.loads(Path(result['data']).read_text(encoding='utf-8'))
        self.assertEqual(packet['status'],'awaiting_owner_decision')
        self.assertIn('Решение на согласование',Path(result['card']).read_text(encoding='utf-8'))
        self.assertEqual((self.p/'state.json').read_bytes(),before)

    def test_stale_sources_prevent_new_card(self):
        sid=core.load(self.p)['claims']['teams-retention']['evidence'][0]['source']
        core.source_status(self.p,sid,reason='Correction')
        with self.assertRaises(InputError):decision_card.generate(self.p)

    def test_card_escapes_authored_markup(self):
        self.bundle['proposal']['rationale']='<script>alert(1)</script>'
        checkpoint.save(self.p,self.bundle)
        result=decision_card.generate(self.p)
        text=Path(result['card']).read_text(encoding='utf-8')
        self.assertNotIn('<script>alert(1)</script>',text)
        self.assertIn('&lt;script&gt;',text)
