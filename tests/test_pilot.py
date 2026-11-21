import copy
from pathlib import Path
import tempfile
import unittest

from strategist import core, pilot
from strategist.ingest import InputError


CASE = Path(__file__).resolve().parents[1]/'examples/telecom-brief'


class PilotDecisionTests(unittest.TestCase):
    def setUp(self):
        self.protocol = core.read_json(CASE/'pilot-plan.json')
        self.plan = pilot.compile_plan(self.protocol)
        self.reported = core.read_json(CASE/'observations/reported.json')
        self.reconciled = core.read_json(CASE/'observations/reconciled.json')

    def test_missing_outcomes_prevent_claiming_benefit(self):
        complete = pilot.evaluate(self.plan, self.reported)
        missing = pilot.evaluate(self.plan, self.reconciled)
        self.assertEqual(complete['effect_status'], 'meets_rule')
        self.assertEqual(complete['recommendation'], 'hold_expansion_for_economics')
        self.assertGreater(missing['primary']['observed_only_reduction'], .03)
        self.assertAlmostEqual(missing['primary']['all_assigned_reduction_bounds'][0], (204-145-80)/1700)
        self.assertAlmostEqual(missing['primary']['all_assigned_reduction_bounds'][1], (204-145)/1700)
        self.assertLess(missing['primary']['outer_score_interval'][0], 0)
        self.assertEqual(missing['recommendation'], 'resolve_uncertainty')

    def test_one_critical_incident_dominates_favorable_effect(self):
        self.reported['critical_incidents']['access_after_revocation'] = 1
        report = pilot.evaluate(self.plan, self.reported)
        self.assertEqual(report['effect_status'], 'meets_rule')
        self.assertEqual(report['recommendation'], 'pause_for_incident')

    def test_no_expand_before_predeclared_readout_or_maturity(self):
        self.reported['planned_readout'] = False
        self.assertEqual(pilot.evaluate(self.plan, self.reported)['recommendation'], 'continue_observation')
        self.reported['planned_readout'] = True
        self.reported['arms']['treatment']['mature'] = 1699
        self.assertEqual(pilot.evaluate(self.plan, self.reported)['recommendation'], 'continue_observation')

    def test_finance_assumption_cannot_clear_expansion_rule(self):
        economics = {'currency':'RUB','scope':self.protocol['economics_scope'],
                     'contribution_low':300_000,'total_cost_high':180_000,
                     'basis':'Synthetic range exercise','evidence_kind':'assumption'}
        self.reported['economics'] = economics
        self.assertEqual(pilot.evaluate(self.plan, self.reported)['recommendation'], 'hold_expansion_for_economics')
        economics['evidence_kind'] = 'checked_range'
        self.assertEqual(pilot.evaluate(self.plan, self.reported)['recommendation'], 'consider_limited_expansion')
        economics['total_cost_high'] = 350_000
        self.assertEqual(pilot.evaluate(self.plan, self.reported)['recommendation'], 'hold_expansion_for_economics')

    def test_positive_business_decision_fails_when_operation_floor_fails(self):
        self.reported['operations']['correct_on_time'] = 1170
        result = pilot.evaluate(self.plan, self.reported)
        self.assertEqual(result['operations_status'], 'below_floor')
        self.assertEqual(result['recommendation'], 'revise_pilot')

    def test_changed_threshold_rejects_existing_results(self):
        changed = copy.deepcopy(self.protocol)
        changed['minimum_reduction'] = .02
        with self.assertRaisesRegex(InputError, 'frozen pilot plan hash'):
            pilot.evaluate(pilot.compile_plan(changed), self.reported)

    def test_bad_denominator_and_missing_guardrail_are_rejected(self):
        self.reported['arms']['treatment']['unknown'] = 1690
        with self.assertRaisesRegex(InputError, r'adverse \+ unknown'):
            pilot.evaluate(self.plan, self.reported)
        self.reported['arms']['treatment']['unknown'] = 0
        del self.reported['critical_incidents']['duplicate_debit']
        with self.assertRaisesRegex(InputError, 'every critical event'):
            pilot.evaluate(self.plan, self.reported)

    def test_evaluate_uses_active_source_lineage(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'case'
            core.init_project(p, 'Synthetic pilot', 'Can we expand?', demo=True)
            pilot.save_plan(p, 'plan', self.protocol, 'synthetic')
            core.source_add(p, 'first', core.canonical(self.reported), '.json', 'Snapshot', 'synthetic')
            report = pilot.save_assessment(p, 'plan', 'first', 'assessment')
            self.assertTrue(report['synthetic'])
            core.source_add(p, 'updated', core.canonical(self.reconciled), '.json', 'Reconciled', 'synthetic')
            core.source_status(p, 'first', 'updated', 'Unknown outcomes reclassified')
            self.assertEqual(core.load(p)['sources']['assessment']['status'], 'withdrawn')
            with self.assertRaisesRegex(InputError, 'active source required'):
                pilot.save_assessment(p, 'plan', 'first', 'old-assessment')

    def test_results_imported_before_plan_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'case'
            core.init_project(p, 'Synthetic pilot', 'Can we expand?', demo=True)
            core.source_add(p, 'first', core.canonical(self.reported), '.json', 'Snapshot', 'synthetic')
            pilot.save_plan(p, 'plan', self.protocol, 'synthetic')
            with self.assertRaisesRegex(InputError, 'before importing'):
                pilot.save_assessment(p, 'plan', 'first', 'assessment')
