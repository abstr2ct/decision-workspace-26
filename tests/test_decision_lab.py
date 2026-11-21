import copy
import itertools
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

from demo.lab_fixtures import make_model
from strategist import core, decision_lab as lab, lab_report, report, retrieval
from strategist.ingest import InputError
from strategist.mcp_server import Session

ROOT = Path(__file__).resolve().parents[1]


class ScenarioMathTests(unittest.TestCase):
    def test_reference_choice_can_be_fragile(self):
        result = lab.analyze(make_model())
        self.assertEqual(result['reference_only']['candidates'], ['expand'])
        self.assertEqual(result['reference_only']['worst_regret_over_all_scenarios']['expand'], 105000)
        self.assertEqual(result['robust']['candidates'], ['focus'])
        self.assertEqual(result['robust']['worst_regret'], 40000)

    def test_inconclusive_outcome_removes_guaranteed_value(self):
        ideal, ambiguous = lab.analyze(make_model(False)), lab.analyze(make_model(True))
        self.assertEqual(ideal['next_checks'], ['targeted-pilot'])
        self.assertEqual(ideal['checks'][0]['total_bound'], 12000)
        self.assertEqual(ambiguous['checks'][0]['total_bound'], 52000)
        self.assertTrue(ambiguous['stop_research'])
        self.assertEqual(ambiguous['next_checks'], [])

    def test_budget_and_delay_can_change_next_check(self):
        model = make_model(False)
        model['research_budget'] = 11000
        self.assertTrue(lab.analyze(model)['stop_research'])
        model['research_budget'] = 100000
        model['checks'][0]['delay_cost'] = 50000
        self.assertTrue(lab.analyze(model)['stop_research'])

    def test_constraints_are_not_offset_by_attractive_payoffs(self):
        model = make_model(False)
        model['constraints'] = [{'id': 'no-expansion', 'rule': 'No broad acquisition', 'basis': 'Owner constraint'}]
        model['options'][2]['violations'] = ['no-expansion']
        result = lab.analyze(model)
        self.assertEqual(result['excluded_options'], ['expand'])
        self.assertNotIn('expand', [x['option'] for x in result['robust']['ranking']])
        self.assertEqual(result['robust']['worst_regret'], 30000)

    def test_ties_are_not_arbitrarily_resolved(self):
        model = make_model()
        for s in model['scenarios']:
            s['payoffs'] = {o['id']: 10 for o in model['options']}
        result = lab.analyze(model)
        self.assertEqual(set(result['robust']['candidates']), {o['id'] for o in model['options']})
        self.assertEqual(result['robust']['worst_regret'], 0)
        self.assertTrue(result['stop_research'])

    def test_decimal_tie_is_not_broken_by_binary_roundoff(self):
        model = make_model()
        for i, s in enumerate(model['scenarios']):
            s['payoffs'] = {'focus': .2 if i % 2 else .4, 'expand': .3, 'keep': 0, 'close': 0}
        self.assertEqual(lab.analyze(model)['robust']['candidates'], ['expand', 'focus'])

    def test_missing_scenario_coverage_is_rejected(self):
        model = make_model(False)
        model['checks'][0]['outcomes'].pop()
        with self.assertRaisesRegex(InputError, 'cover every scenario'):
            lab.analyze(model)

    def test_invalid_numbers_and_false_evidence_label_are_rejected(self):
        for bad in (True, float('nan'), float('inf'), '120', None):
            model = make_model()
            model['scenarios'][0]['payoffs']['focus'] = bad
            with self.assertRaises(InputError):
                lab.analyze(model)
        model = make_model(); model['payoff_status'] = 'fact'
        with self.assertRaises(InputError):
            lab.analyze(model)

    def test_incomplete_matrix_negative_cost_and_probabilities_rejected(self):
        for change in ('matrix', 'negative', 'prior'):
            model = make_model()
            if change == 'matrix': del model['scenarios'][0]['payoffs']['close']
            elif change == 'negative': model['checks'][0]['cost'] = -1
            else: model['scenarios'][0]['probability'] = .8
            with self.assertRaises(InputError): lab.analyze(model)

    def test_exhaustive_policy_oracle_on_unseen_random_matrices(self):
        # Independent enumeration of all observation->action policies. Includes
        # overlapping observation sets; neither production solve nor regret code is reused.
        rng = random.Random(20261113)
        for _ in range(30):
            model = make_model(False)
            options = [o['id'] for o in model['options']]
            scenes = model['scenarios']
            for s in scenes:
                s['payoffs'] = {o: rng.randint(-30, 90) for o in options}
            model['checks'] = [model['checks'][0]]
            check = model['checks'][0]
            check['cost'], check['delay_cost'] = rng.randint(0, 15), rng.randint(0, 5)
            check['outcomes'] = [
                {'id': 'left', 'label': 'Left', 'scenarios': [s['id'] for s in scenes[:3]]},
                {'id': 'right', 'label': 'Right', 'scenarios': [s['id'] for s in scenes[1:]]},
            ]
            raw = {s['id']: s['payoffs'] for s in scenes}
            possible_policies = itertools.product(options, repeat=2)
            oracle = min(max(max(raw[sid].values()) - raw[sid][chosen]
                             for outcome, chosen in zip(check['outcomes'], policy)
                             for sid in outcome['scenarios']) for policy in possible_policies)
            result = lab.analyze(model)['checks'][0]
            self.assertEqual(result['residual_regret'], oracle)
            self.assertEqual(result['total_bound'], oracle + check['cost'] + check['delay_cost'])

    def test_adding_scenario_constant_preserves_regret(self):
        model = make_model()
        original = lab.analyze(model)
        for idx, s in enumerate(model['scenarios']):
            s['payoffs'] = {k: v + idx * 3211 for k, v in s['payoffs'].items()}
        self.assertEqual(lab.analyze(model), original)


class ScenarioStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)/'project'
        shutil.copytree(ROOT/'examples'/'replay', self.p)
        self.model = make_model()

    def tearDown(self):
        self.tmp.cleanup()

    def test_commit_invalidates_old_choice_without_choosing_for_user(self):
        old = core.load(self.p)['decision']['sha256']
        lab.commit(self.p, self.model)
        state = core.load(self.p)
        self.assertEqual(state['decision']['sha256'], old)
        self.assertFalse(core.approved(state, 'decision'))
        self.assertEqual(state['documents']['strategy']['status'], 'review_required')
        self.assertEqual(lab.show(self.p)['verification']['status'], 'active')

    def test_identical_commit_is_idempotent(self):
        lab.commit(self.p, self.model)
        before = (self.p/'state.json').read_bytes()
        lab.commit(self.p, self.model)
        self.assertEqual(before, (self.p/'state.json').read_bytes())

    def test_options_and_references_must_match_current_project(self):
        self.model['options'][0]['kind'] = 'other'
        with self.assertRaises(InputError): lab.commit(self.p, self.model)
        model = make_model()
        model['scenarios'][0]['claim_refs'] = ['nonexistent']
        with self.assertRaises(InputError): lab.commit(self.p, model)

    def test_source_withdrawal_blocks_lab_and_decision(self):
        lab.commit(self.p, self.model)
        state = core.load(self.p)
        sid = state['claims']['teams-retention']['evidence'][0]['source']
        self.assertTrue(retrieval.impact(self.p, sid)['decision_lab_directly_affected'])
        core.source_status(self.p, sid, reason='Input correction')
        with self.assertRaises(InputError): lab.show(self.p)
        with self.assertRaises(InputError): core.approve(self.p, 'decision', 'SCENARIO:owner', 'Cannot reuse stale assumptions', True)
        self.assertTrue(any('Decision lab' in x for x in core.audit(self.p)['errors']))

    def test_new_evidence_marks_analysis_stale(self):
        lab.commit(self.p, self.model)
        core.source_add(self.p, 'update', b'New observation', '.txt', 'Update')
        self.assertEqual(core.load(self.p)['decision_lab']['status'], 'review_required')

    def test_payload_tampering_detected(self):
        lab.commit(self.p, self.model)
        state = core.load(self.p)
        state['decision_lab']['result']['robust']['candidates'] = ['expand']
        core.atomic_write(self.p/'state.json', core.canonical(state))
        with self.assertRaisesRegex(InputError, 'payload changed'): lab.show(self.p)

    def test_pause_blocks_commit(self):
        with core.transaction(self.p) as s: s['paused'] = True
        with self.assertRaises(InputError): lab.commit(self.p, self.model)

    def test_html_cannot_execute_authored_markup(self):
        self.model['title'] = '</script><img src=x onerror=alert(1)>'
        lab.commit(self.p, self.model)
        html = lab_report.generate(self.p).read_text(encoding='utf-8')
        self.assertNotIn(self.model['title'], html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertIn('Content-Security-Policy', html)

    def test_draft_replaces_old_lab_page_with_stale_notice(self):
        lab.commit(self.p, self.model)
        lab_report.generate(self.p)
        core.source_add(self.p, 'new', b'Correction', '.txt', 'New')
        report.export_report(self.p, draft=True)
        page = (self.p/'exports'/'decision-lab.html').read_text(encoding='utf-8')
        self.assertIn('требует пересмотра', page)
        self.assertNotIn('lab-data', page)

    def test_fresh_process_and_mcp_read_only(self):
        lab.commit(self.p, self.model)
        before = (self.p/'state.json').read_bytes()
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'strategist', 'lab', 'show', str(self.p)],
                                cwd=ROOT, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['verification']['candidates'], ['focus'])
        self.assertEqual(Session(self.p).call_tool('strategy_lab', {})['verification']['status'], 'active')
        self.assertEqual(before, (self.p/'state.json').read_bytes())
