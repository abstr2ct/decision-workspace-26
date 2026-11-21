import unittest
from strategist.analytics import compare_cohorts
from strategist.ingest import InputError

HEADER='cohort,segment,eligible,activated,retained_d30,matured_d30,revenue_rub,variable_cost_rub,acquisition_cost_rub\n'

def fixture(rows):
    return (HEADER+'\n'.join(','.join(map(str,r))+',0,0,0' for r in rows)).encode()


class MixTests(unittest.TestCase):
    def setUp(self):
        self.rows=[['old','a',100,80,48,'true'],['old','b',100,20,4,'true'],
                   ['new','a',100,20,13,'true'],['new','b',100,80,20,'true']]

    def test_mix_reverses_aggregate_despite_better_segment_rates(self):
        r=compare_cohorts(fixture(self.rows),'old','new')
        self.assertEqual((r['baseline_d30'],r['current_d30']),(.52,.33))
        self.assertEqual(r['current_d30_at_baseline_mix'],.57)
        self.assertEqual((r['within_segment_change_pp'],r['mix_change_pp'],r['total_change_pp']),(5,-24,-19))

    def test_correction_exposes_real_within_segment_decline(self):
        self.rows[2][4]=5
        r=compare_cohorts(fixture(self.rows),'old','new')
        self.assertEqual((r['current_d30'],r['within_segment_change_pp'],r['mix_change_pp']),(.25,-27,0))

    def test_unmatured_selected_cohort_is_rejected(self):
        self.rows[-1][-1]='false'
        with self.assertRaises(InputError):compare_cohorts(fixture(self.rows),'old','new')

    def test_missing_segment_is_not_imputed(self):
        with self.assertRaises(InputError):compare_cohorts(fixture(self.rows[:-1]),'old','new')

    def test_zero_denominator_is_not_a_zero_rate(self):
        self.rows[-1][3:5]=[0,0]
        with self.assertRaises(InputError):compare_cohorts(fixture(self.rows),'old','new')

    def test_exact_identity_with_uneven_counts(self):
        self.rows[0][3:5]=[79,47]
        r=compare_cohorts(fixture(self.rows),'old','new')
        self.assertAlmostEqual(r['total_change_pp'],r['within_segment_change_pp']+r['mix_change_pp'])
