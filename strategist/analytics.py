"""Auditable cohort arithmetic, no statistical or causal shortcuts."""

import csv
import io
import math
from collections import defaultdict
from statistics import NormalDist

from .ingest import InputError, decode


def plan_ab(baseline, target, alpha=.05, power=.8):
    if not all(math.isfinite(x) for x in (baseline, target, alpha, power)) or not (0 < baseline < 1 and 0 < target < 1 and baseline != target and 0 < alpha < 1 and .5 < power < 1):
        raise InputError('Use probabilities in (0,1), a nonzero effect, and power > .5')
    mean = (baseline+target)/2
    z_alpha = NormalDist().inv_cdf(1-alpha/2)
    z_power = NormalDist().inv_cdf(power)
    n = math.ceil((z_alpha*math.sqrt(2*mean*(1-mean)) + z_power*math.sqrt(baseline*(1-baseline)+target*(1-target)))**2/(target-baseline)**2)
    return {'method': 'Two independent proportions, equal allocation, normal approximation without continuity correction',
            'baseline': baseline, 'target': target, 'absolute_mde': abs(target-baseline), 'alpha_two_sided': alpha, 'power': power,
            'independent_units_per_arm': n, 'total': n*2,
            'limitations': ['Not a promise of achievable effect', 'Account for clustering, attrition, multiplicity and sparse samples separately',
                           'If actual traffic is insufficient, run a feasibility pilot or preplan a longer window']}


def wilson(successes, total, z=1.959963984540054):
    if not total:
        return None
    p = successes / total
    d = 1 + z*z / total
    mid = (p + z*z / (2*total)) / d
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / d
    return [mid-half, mid+half]


def cohort_analysis(data):
    rows = list(csv.DictReader(io.StringIO(decode(data))))
    required = {'cohort', 'segment', 'eligible', 'activated', 'retained_d30', 'matured_d30', 'revenue_rub', 'variable_cost_rub', 'acquisition_cost_rub'}
    if not rows or not required.issubset(rows[0]):
        raise InputError('Missing required cohort columns: ' + ', '.join(sorted(required)))
    groups = defaultdict(lambda: {'eligible': 0, 'activated': 0, 'retained_d30': 0, 'revenue_rub': 0., 'variable_cost_rub': 0., 'acquisition_cost_rub': 0., 'cohorts': []})
    seen, excluded = set(), []
    for index, row in enumerate(rows, 2):
        key = row['cohort'], row['segment']
        if not all(key) or key in seen:
            raise InputError(f'Empty or duplicated cohort/segment at row {index}')
        seen.add(key)
        if row['matured_d30'] not in ('true', 'false'):
            raise InputError(f'matured_d30 must be true/false at row {index}')
        nums = {}
        for col in ('eligible', 'activated', 'retained_d30', 'revenue_rub', 'variable_cost_rub', 'acquisition_cost_rub'):
            try:
                nums[col] = float(row[col])
            except (TypeError, ValueError) as exc:
                raise InputError(f'Missing/non-numeric {col} at row {index}') from exc
            if not math.isfinite(nums[col]) or nums[col] < 0:
                raise InputError(f'Invalid {col} at row {index}')
        if any(not nums[k].is_integer() for k in ('eligible', 'activated', 'retained_d30')):
            raise InputError(f'Counts must be integers at row {index}')
        if not 0 <= nums['retained_d30'] <= nums['activated'] <= nums['eligible'] or not nums['eligible']:
            raise InputError(f'Invalid funnel denominators at row {index}')
        if row['matured_d30'] == 'false':
            excluded.append({'row': index, 'reason': 'D30 not matured', 'cohort': row['cohort'], 'segment': row['segment']})
            continue
        group = groups[row['segment']]
        for col, value in nums.items():
            group[col] += value
        group['cohorts'].append(row['cohort'])
    out = {}
    for segment, group in sorted(groups.items()):
        e, a, r = group['eligible'], group['activated'], group['retained_d30']
        out[segment] = dict(group, activation_rate=a/e, d30_per_activated=r/a if a else None,
                            d30_per_eligible=r/e, d30_95pct_wilson=wilson(r, a),
                            contribution_before_acquisition_rub=group['revenue_rub']-group['variable_cost_rub'],
                            contribution_after_acquisition_rub=group['revenue_rub']-group['variable_cost_rub']-group['acquisition_cost_rub'])
    return {'method': 'Sum mutually exclusive matured cohorts by segment; ratios of sums, Wilson 95% for D30/activated',
            'currency': 'RUB', 'window': 'first 30 days; no LTV extrapolation', 'segments': out, 'excluded': excluded,
            'limits': ['Synthetic input stays synthetic', 'Descriptive segment differences are not causal effects',
                       'Wilson intervals assume independent Bernoulli observations; repeated users/clusters invalidate them',
                       'Contribution excludes fixed costs, taxes and later cash flows; this is not profit or LTV']}


def compare_cohorts(data, baseline, current):
    """Exact descriptive rate bridge: old weights first, current rates second.

    R1-R0 = sum(w0*(r1-r0)) + sum((w1-w0)*r1).
    Order is explicit: the interaction belongs to the mix term. Not causality.
    """
    from fractions import Fraction
    validated = cohort_analysis(data)  # Validate all rows, even excluded ones.
    if baseline == current:
        raise InputError('Choose two different cohort IDs')
    rows = list(csv.DictReader(io.StringIO(decode(data))))
    selected = {}
    for period in (baseline, current):
        matches = [r for r in rows if r['cohort'] == period]
        if not matches or any(r['matured_d30'] != 'true' for r in matches):
            raise InputError(f'Every row of selected cohort must be mature: {period}')
        if any(float(r['activated']) == 0 for r in matches):
            raise InputError('Every segment needs a positive activated denominator in both cohorts')
        selected[period] = {r['segment']: r for r in matches}
    if set(selected[baseline]) != set(selected[current]):
        raise InputError('Segment coverage differs; missing segments cannot be silently treated as zero')
    totals = {p: sum(int(float(r['activated'])) for r in selected[p].values()) for p in selected}
    r0_total = r1_total = within = mix = Fraction(0)
    segments = []
    for segment in sorted(selected[baseline]):
        a, b = selected[baseline][segment], selected[current][segment]
        n0, n1 = int(float(a['activated'])), int(float(b['activated']))
        r0, r1 = Fraction(int(float(a['retained_d30'])), n0), Fraction(int(float(b['retained_d30'])), n1)
        w0, w1 = Fraction(n0, totals[baseline]), Fraction(n1, totals[current])
        change_rate, change_mix = w0*(r1-r0), (w1-w0)*r1
        r0_total += w0*r0; r1_total += w1*r1
        within += change_rate; mix += change_mix
        segments.append({'segment': segment, 'baseline_rate': float(r0), 'current_rate': float(r1),
                         'baseline_weight': float(w0), 'current_weight': float(w1),
                         'within_contribution_pp': float(100*change_rate), 'mix_contribution_pp': float(100*change_mix)})
    assert within + mix == r1_total-r0_total
    return {'method': 'Descriptive ordered decomposition: baseline weights, then current segment rates',
            'baseline_cohort': baseline, 'current_cohort': current,
            'denominator': 'activated accounts; same D30 definition and mutually exclusive segments required',
            'baseline_d30': float(r0_total), 'current_d30': float(r1_total),
            'current_d30_at_baseline_mix': float(r0_total+within),
            'total_change_pp': float(100*(r1_total-r0_total)),
            'within_segment_change_pp': float(100*within), 'mix_change_pp': float(100*mix),
            'segments': segments, 'excluded_immature_rows': validated['excluded'],
            'limits': ['Accounting identity, not a causal explanation or proof of product improvement',
                       'Order matters for attribution: interaction assigned to the mix term',
                       'No significance test; sampling uncertainty and confounding remain',
                       'Identical maturity, segment definitions and tracking must be checked against source metadata']}
