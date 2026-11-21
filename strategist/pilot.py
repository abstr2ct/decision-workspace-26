"""Evaluate a fixed-window, two-arm pilot from auditable aggregate counts."""

import json
import math
import re
from pathlib import Path
from statistics import NormalDist

from . import analytics, core


def require_fields(data, fields, label):
    core.require(isinstance(data, dict) and set(data) == set(fields.split()),
                 f'{label}: expected exactly these fields: {fields}')


def count(value, label):
    core.require(type(value) is int and 0 <= value <= 1_000_000_000,
                 f'{label}: expected a nonnegative integer up to 1,000,000,000')
    return value


def decimal_number(value, label, low, high):
    core.require(type(value) in (float, int) and low <= value <= high,
                 f'{label}: expected a number within [{low}, {high}]')
    return value


def nonempty(value, label):
    core.require(isinstance(value, str) and bool(value.strip()), f'{label}: text required')


def compile_plan(protocol):
    require_fields(protocol, 'name unit population endpoint control owner window_days baseline_rate '
                   'minimum_reduction alpha power minimum_operations operation_success_floor '
                   'critical_events currency economics_scope', 'protocol')
    for key in ('name', 'unit', 'population', 'endpoint', 'control', 'owner', 'economics_scope'):
        nonempty(protocol[key], key)
    core.require(1 <= count(protocol['window_days'], 'window_days') <= 365, 'Use a window of 1–365 days')
    core.require(count(protocol['minimum_operations'], 'minimum_operations') > 0, 'Minimum operations must be positive')
    decimal_number(protocol['operation_success_floor'], 'operation_success_floor', .01, 1)
    baseline = decimal_number(protocol['baseline_rate'], 'baseline_rate', .001, .999)
    reduction = decimal_number(protocol['minimum_reduction'], 'minimum_reduction', .0001, .99)
    alpha = decimal_number(protocol['alpha'], 'alpha', .001, .2)
    power = decimal_number(protocol['power'], 'power', .51, .999)
    core.require(isinstance(protocol['currency'], str) and re.fullmatch('[A-Z]{3}', protocol['currency']),
                 'Use a three-letter currency code')
    events = protocol['critical_events']
    core.require(isinstance(events, list) and 1 <= len(events) <= 12, 'List 1–12 critical event IDs')
    for event in events:
        core.check_id(event)
    core.require(len(events) == len(set(events)), 'Critical event IDs must be unique')
    sample = analytics.plan_ab(baseline, baseline-reduction, alpha, power)
    core.require(sample['independent_units_per_arm'] <= 1_000_000_000, 'Sample exceeds count schema')
    return {'kind': 'pilot_protocol_v1', 'protocol': protocol, 'sample_plan': sample}


def read_arm(arm, label):
    require_fields(arm, 'assigned mature adverse unknown', label)
    assigned, mature, events, unknown = (count(arm[key], f'{label}.{key}') for key in
                                         ('assigned', 'mature', 'adverse', 'unknown'))
    core.require(events + unknown <= mature <= assigned,
                 f'{label}: adverse + unknown <= mature <= assigned required')
    return assigned, mature, events, unknown


def difference_interval(c_events, c_n, t_events, t_n, alpha):
    """Newcombe method 10: independent score intervals without continuity correction."""
    c = c_events/c_n
    t = t_events/t_n
    z = NormalDist().inv_cdf(1-alpha/2)
    c_low, c_high = analytics.wilson(c_events, c_n, z)
    t_low, t_high = analytics.wilson(t_events, t_n, z)
    return (max(-1, c-t-math.hypot(c-c_low, t_high-t)),
            min(1, c-t+math.hypot(c_high-c, t-t_low)))


def effect_summary(control, treatment, alpha):
    c_n, c_mature, c_events, c_unknown = control
    t_n, t_mature, t_events, t_unknown = treatment
    # Pending follow-up has unknown outcome until the full fixed observation window.
    c_unresolved = c_n-c_mature+c_unknown
    t_unresolved = t_n-t_mature+t_unknown
    observed_only = None
    if c_mature > c_unknown and t_mature > t_unknown:
        observed_only = c_events/(c_mature-c_unknown) - t_events/(t_mature-t_unknown)
    bounds = interval = None
    if c_n and t_n:
        bounds = [c_events/c_n-(t_events+t_unresolved)/t_n, (c_events+c_unresolved)/c_n-t_events/t_n]
        # Use extreme completions of unknown outcomes. The outer interval is
        # a sensitivity summary, with nominal score coverage for each completion.
        low = difference_interval(c_events, c_n, t_events+t_unresolved, t_n, alpha)[0]
        high = difference_interval(c_events+c_unresolved, c_n, t_events, t_n, alpha)[1]
        interval = [low, high]
    return {'observed_only_reduction': observed_only, 'all_assigned_reduction_bounds': bounds,
            'outer_score_interval': interval, 'unknown_or_immature': {'control':c_unresolved,'treatment':t_unresolved}}


def evaluate(compiled_plan, snapshot):
    protocol = compiled_plan['protocol']
    core.require(compile_plan(protocol) == compiled_plan, 'Plan structure or sample size changed')
    require_fields(snapshot, 'plan_sha256 window_days planned_readout assignment_verified outcome_verified '
                   'incident_reporting_verified arms operations critical_incidents economics', 'snapshot')
    sha = core.digest(core.canonical(compiled_plan))
    core.require(snapshot['plan_sha256'] == sha, 'Snapshot does not match the frozen pilot plan hash')
    core.require(type(snapshot['window_days']) is int and snapshot['window_days'] == protocol['window_days'],
                 'Snapshot follow-up window differs from the plan')
    for key in ('planned_readout', 'assignment_verified', 'outcome_verified', 'incident_reporting_verified'):
        core.require(type(snapshot[key]) is bool, f'{key}: true or false required')
    arms = snapshot['arms']
    require_fields(arms, 'control treatment', 'arms')
    control = read_arm(arms['control'], 'control')
    treatment = read_arm(arms['treatment'], 'treatment')
    effect = effect_summary(control, treatment, protocol['alpha'])
    min_n = compiled_plan['sample_plan']['independent_units_per_arm']
    mature_enough = all(arm[0] >= min_n and arm[0] == arm[1] for arm in (control, treatment))
    measurement_verified = snapshot['assignment_verified'] and snapshot['outcome_verified']
    effect_result = 'await_readout'
    if not measurement_verified:
        effect_result = 'verify_measurement'
    elif snapshot['planned_readout'] and mature_enough:
        if effect['outer_score_interval'][1] < protocol['minimum_reduction']:
            effect_result = 'below_useful_range'
        elif (effect['all_assigned_reduction_bounds'][0] >= protocol['minimum_reduction']
              and effect['outer_score_interval'][0] > 0):
            effect_result = 'meets_rule'
        else:
            effect_result = 'inconclusive'

    operations = snapshot['operations']
    require_fields(operations, 'confirmed correct_on_time unknown', 'operations')
    confirmed, correct, unknown = (count(operations[key], f'operations.{key}') for key in
                                    ('confirmed', 'correct_on_time', 'unknown'))
    core.require(correct + unknown <= confirmed, 'Correct and unknown operations must fit the denominator')
    success_rate = correct/confirmed if confirmed else None
    if confirmed < protocol['minimum_operations']:
        operations_result = 'insufficient'
    else:
        operations_result = 'meets_rule' if success_rate >= protocol['operation_success_floor'] else 'below_floor'
    incidents = snapshot['critical_incidents']
    core.require(isinstance(incidents, dict) and set(incidents) == set(protocol['critical_events']),
                 'Report counts for every critical event defined in the plan')
    for key, value in incidents.items():
        count(value, f'critical_incidents.{key}')
    safety_result = 'critical_incident' if any(incidents.values()) else (
        'checks_reported' if snapshot['incident_reporting_verified'] else 'unverified')

    economics = snapshot['economics']
    minimum_net = None
    economics_result = 'unresolved'
    if economics is not None:
        require_fields(economics, 'currency scope basis evidence_kind contribution_low total_cost_high', 'economics')
        core.require((economics['currency'], economics['scope']) == (protocol['currency'], protocol['economics_scope']),
                     'Economics currency and scope must match the plan')
        nonempty(economics['basis'], 'economics.basis')
        core.require(economics['evidence_kind'] in ('assumption', 'checked_range'), 'Label finance assumptions explicitly')
        low = decimal_number(economics['contribution_low'], 'contribution_low', -1e15, 1e15)
        cost = decimal_number(economics['total_cost_high'], 'total_cost_high', 0, 1e15)
        minimum_net = low-cost
        if economics['evidence_kind'] == 'checked_range':
            economics_result = 'meets_rule' if minimum_net >= 0 else 'negative_lower_scenario'

    if safety_result == 'critical_incident':
        next_step = 'pause_for_incident'
    elif effect_result == 'verify_measurement' or safety_result == 'unverified':
        next_step = 'verify_measurement'
    elif effect_result == 'await_readout' or operations_result == 'insufficient':
        next_step = 'continue_observation'
    elif operations_result == 'below_floor' or effect_result == 'below_useful_range':
        next_step = 'revise_pilot'
    elif effect_result == 'inconclusive':
        next_step = 'resolve_uncertainty'
    elif economics_result != 'meets_rule':
        next_step = 'hold_expansion_for_economics'
    else:
        next_step = 'consider_limited_expansion'
    return {'kind':'pilot_assessment_v1','plan_sha256':sha,'recommendation':next_step,
            'window_days':protocol['window_days'],'minimum_per_arm':min_n,'assigned':{'control':control[0],'treatment':treatment[0]},
            'sample_and_window_ready':mature_enough,'primary':effect,
            'confidence_level':1-protocol['alpha'],'minimum_reduction':protocol['minimum_reduction'],
            'effect_status':effect_result,'operations_status':operations_result,'operation_success_rate':success_rate,
            'incident_status':safety_result,'critical_incidents':incidents,'economics_status':economics_result,
            'economics_lower_scenario_net':minimum_net,'currency':protocol['currency'],
            'limits':['Proposed action for owner review. No approval or launch is performed.',
                      'Independent randomization units, a fixed readout and correct incoming counts are assumed.',
                      'Observed-only effect is descriptive. The decision uses all assigned units and extreme outcomes for unknowns.',
                      'The outer score interval is a sensitivity summary, not an exact coverage guarantee.',
                      'A positive effect and minimum point reduction do not prove the causal effect is at least the minimum.',
                      'Incident capture and finance scope are supplied by their owners, not authenticated by this calculation.']}


def save_plan(project, plan_id, protocol, origin):
    state = core.load(project)
    core.require(origin == 'own' or (origin == 'synthetic' and state['demo']),
                 'Synthetic pilot plans require a demo project')
    compiled = compile_plan(protocol)
    record = core.source_add(project, plan_id, core.canonical(compiled), '.json', 'Frozen pilot plan', origin)
    return {'id':plan_id,'sha256':record['sha256'],
            'minimum_per_arm':compiled['sample_plan']['independent_units_per_arm']}


def active_snapshot(project, state, source_id):
    source = state['sources'].get(source_id)
    core.require(source is not None and source['status'] == 'active', f'{source_id}: active source required')
    path = core.project_file(project, source['blob'])
    core.require(Path(path).suffix == '.json', f'{source_id}: JSON source required')
    raw = path.read_bytes()
    core.require(core.digest(raw) == source['sha256'], f'{source_id}: snapshot digest mismatch')
    value = json.loads(raw.decode('utf-8-sig'))
    core.require(isinstance(value, dict), f'{source_id}: JSON object required')
    return source, value


def save_assessment(project, plan_id, result_id, assessment_id):
    state = core.load(project)
    plan_source, plan = active_snapshot(project, state, plan_id)
    result_source, snap = active_snapshot(project, state, result_id)
    core.require(plan_source['synthetic'] == result_source['synthetic'] and
                 (state['demo'] or not plan_source['synthetic']), 'Use matching provenance for plan and results')
    order = {e['detail']['id']: e['seq'] for e in state['events'] if e['kind'] == 'source_added'}
    core.require(plan_id in order and result_id in order and order[plan_id] < order[result_id],
                 'Freeze the plan before importing its result snapshot')
    result = evaluate(plan, snap)
    core.require(plan_source['sha256'] == result['plan_sha256'], 'Plan must be a canonical frozen snapshot')
    result.update(plan_source=plan_id, result_source=result_id, result_sha256=result_source['sha256'],
                  synthetic=result_source['synthetic'])
    core.source_add(project, assessment_id, core.canonical(result), '.json',
                    'Pilot assessment against frozen thresholds', 'derived', parents=[plan_id,result_id])
    return result
