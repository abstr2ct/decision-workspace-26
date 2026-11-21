import copy
import unittest

from tools.compare_runs import compare


class ComparisonTests(unittest.TestCase):
    def measurement(self):
        return {'task_id': 'case-1', 'input_sha256': 'same-inputs', 'evaluation_protocol': 'v1', 'reviewer': 'blind reviewer',
                'wall_seconds': 600, 'human_seconds': 100, 'quality_checks_passed': 8, 'quality_checks_total': 10,
                'costs': [{'currency': 'RUB', 'amount': '100'}], 'cost_coverage_complete': True}

    def test_real_difference_and_negative_savings(self):
        a, b = self.measurement(), self.measurement()
        a.update(wall_seconds=700, human_seconds=50)
        a['costs'][0]['amount'] = '120'
        result = compare(a, b)
        self.assertEqual(result['wall_seconds_saved'], -100)
        self.assertEqual(result['human_seconds_saved'], 50)
        self.assertEqual(result['cost_difference_baseline_minus_agent'], {'RUB': '-20'})

    def test_incomplete_costs_do_not_establish_savings(self):
        a, b = self.measurement(), self.measurement()
        a['cost_coverage_complete'] = False
        self.assertIsNone(compare(a, b)['cost_difference_baseline_minus_agent'])

    def test_different_inputs_rejected(self):
        a, b = self.measurement(), self.measurement()
        b['input_sha256'] = 'different'
        with self.assertRaises(ValueError):
            compare(a, b)

    def test_unknown_human_time_is_not_zero(self):
        a, b = self.measurement(), self.measurement()
        a['human_seconds'] = None
        self.assertIsNone(compare(a, b)['human_seconds_saved'])
        self.assertEqual(compare(a, b)['wall_seconds_saved'], 0)

    def test_unmeasured_template_rejected(self):
        a, b = self.measurement(), self.measurement()
        a['record_status'] = 'UNMEASURED_TEMPLATE_NOT_A_BENCHMARK'
        with self.assertRaises(ValueError):
            compare(a, b)
