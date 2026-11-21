"""Finite-scenario decision stress tests. No LLM calls or invented probabilities.

All payoffs are explicitly authored assumptions, including ones informed by facts.
The regret of a choice is the gap to the best feasible choice IN THE SAME scenario.
Tests are set-valued observations: overlapping outcomes represent ambiguity.
"""

import copy
import math
from decimal import Decimal
from . import core

VERSION = 1
LIMITS = {'options': 20, 'scenarios': 100, 'checks': 30, 'outcomes': 100}


def number(value, name, nonnegative=False):
    core.require(type(value) in (int, float) and abs(value) <= 1e12 and math.isfinite(value),
                 f'{name}: finite number up to 1e12 required (not bool)')
    core.require(not nonnegative or value >= 0, f'{name}: cannot be negative')
    return value


def records(value, name, minimum=0):
    core.require(isinstance(value, list) and minimum <= len(value) <= LIMITS.get(name, 100),
                 f'{name}: expected {minimum}..{LIMITS.get(name, 100)} records')
    ids = []
    for record in value:
        core.require(isinstance(record, dict), f'{name}: object required')
        core.check_id(record.get('id', ''))
        ids.append(record['id'])
    core.require(len(set(ids)) == len(ids), f'{name}: duplicate IDs')
    return ids


def text_fields(record, names):
    for name in names:
        core.require(isinstance(record.get(name), str) and record[name].strip(), f'Nonempty text required: {name}')


def validate(model):
    core.require(isinstance(model, dict) and model.get('schema_version') == VERSION, 'Decision lab schema_version must be 1')
    text_fields(model, ('title', 'unit', 'metric_definition', 'horizon', 'coverage_limits'))
    core.require(model.get('payoff_status') == 'assumption', 'Payoffs must be explicitly labelled assumption, never observed fact')
    core.require(model.get('higher_is_better') is True, 'Convert all values to one higher-is-better metric first')
    core.require(model['unit'] in ('RUB', 'USD', 'EUR', 'utility_points'), 'Unsupported unit')
    number(model.get('research_budget'), 'research_budget', True)
    constraints = records(model.get('constraints', []), 'constraints')
    opts = records(model.get('options'), 'options', 3)
    kinds = set()
    for option in model['options']:
        text_fields(option, ('name', 'kind'))
        kinds.add(option['kind'])
        violations = option.get('violations')
        core.require(isinstance(violations, list) and len(set(violations)) == len(violations)
                     and set(violations) <= set(constraints), 'Unknown or duplicate constraint violations')
    core.require({'status_quo', 'shutdown'} <= kinds, 'Include status_quo and shutdown')
    core.require(any(not o['violations'] for o in model['options']), 'No feasible option: resolve constraints with the owner')
    for constraint in model.get('constraints', []):
        text_fields(constraint, ('rule', 'basis'))
    scenes = records(model.get('scenarios'), 'scenarios', 2)
    core.require(model.get('reference_scenario') in scenes, 'reference_scenario must exist')
    for scenario in model['scenarios']:
        text_fields(scenario, ('name', 'assumption', 'falsifier'))
        core.require(isinstance(scenario.get('claim_refs'), list) and all(isinstance(c, str) for c in scenario['claim_refs']), 'claim_refs must be a list of IDs')
        core.require('probability' not in scenario, 'Probabilities are not used: do not hide an arbitrary prior in scenarios')
        values = scenario.get('payoffs')
        core.require(isinstance(values, dict) and set(values) == set(opts), 'Every scenario must value exactly every option')
        for option_id, value in values.items():
            number(value, f'{scenario["id"]}/{option_id}')
        core.require(isinstance(scenario.get('payoff_rationale'), dict)
                     and set(scenario['payoff_rationale']) == set(opts)
                     and all(isinstance(v, str) and v.strip() for v in scenario['payoff_rationale'].values()),
                     'Explain each assumed payoff, including baseline and closure')
    records(model.get('checks'), 'checks')
    for check in model['checks']:
        text_fields(check, ('name', 'question', 'method', 'cost_basis', 'duration', 'limitations'))
        core.require(check.get('observation_model') == 'authored_possibility_sets', 'Observation model must be explicit')
        for field in ('cost', 'delay_cost'):
            number(check.get(field), field, True)
        outcomes = check.get('outcomes')
        records(outcomes, 'outcomes', 1)
        covered = set()
        for outcome in outcomes:
            text_fields(outcome, ('label',))
            members = outcome.get('scenarios')
            core.require(isinstance(members, list) and members and all(isinstance(s, str) for s in members)
                         and len(set(members)) == len(members) and set(members) <= set(scenes), 'Invalid outcome scenarios')
            covered.update(members)
        core.require(covered == set(scenes), 'Every check must cover every scenario; include inconclusive outcomes when possible')
    return model


def solve(model, scenario_ids=None):
    """Minimize worst regret; keep ties visible instead of silently picking an ID."""
    scenarios = [s for s in model['scenarios'] if scenario_ids is None or s['id'] in scenario_ids]
    feasible = [o for o in model['options'] if not o['violations']]
    oracle = {s['id']: max(Decimal(str(s['payoffs'][o['id']])) for o in feasible) for s in scenarios}
    ranking = []
    for option in feasible:
        regrets = {s['id']: float(oracle[s['id']] - Decimal(str(s['payoffs'][option['id']]))) for s in scenarios}
        worst = max(regrets.values())
        ranking.append({'option': option['id'], 'worst_regret': worst, 'regrets': regrets,
                        'witness_scenarios': [k for k, v in regrets.items() if v == worst]})
    ranking.sort(key=lambda item: (item['worst_regret'], item['option']))
    optimum = ranking[0]['worst_regret']
    return {'candidates': [r['option'] for r in ranking if r['worst_regret'] == optimum],
            'worst_regret': optimum, 'ranking': ranking}


def analyze(model):
    validate(model)
    robust = solve(model)
    # The comparator is deliberately simple, not a simulated human/chat response.
    reference = solve(model, [model['reference_scenario']])
    baseline_regrets = {r['option']: r['worst_regret'] for r in robust['ranking'] if r['option'] in reference['candidates']}
    checks = []
    for check in model['checks']:
        outcomes = []
        for outcome in check['outcomes']:
            solved = solve(model, outcome['scenarios'])
            outcomes.append({'id': outcome['id'], 'label': outcome['label'], 'scenarios': outcome['scenarios'],
                             'candidates': solved['candidates'], 'worst_regret': solved['worst_regret']})
        residual = max(o['worst_regret'] for o in outcomes)
        total_cost = float(Decimal(str(check['cost'])) + Decimal(str(check['delay_cost'])))
        total_bound = float(Decimal(str(residual)) + Decimal(str(total_cost)))
        checks.append({'id': check['id'], 'name': check['name'], 'outcomes': outcomes,
                       'cost': check['cost'], 'delay_cost': check['delay_cost'], 'total_cost': total_cost,
                       'within_budget': total_cost <= model['research_budget'],
                       'residual_regret': residual, 'total_bound': total_bound,
                       'bound_reduction': float(Decimal(str(robust['worst_regret'])) - Decimal(str(total_bound)))})
    viable = [c for c in checks if c['within_budget'] and c['bound_reduction'] > 0]
    best = min((c['total_bound'] for c in viable), default=None)
    return {'method': 'finite_scenarios_minimax_regret_v1', 'payoff_status': 'assumption',
            'unit': model['unit'], 'horizon': model['horizon'], 'robust': robust,
            'reference_only': {'scenario': model['reference_scenario'], 'candidates': reference['candidates'],
                               'worst_regret_over_all_scenarios': baseline_regrets},
            'excluded_options': [o['id'] for o in model['options'] if o['violations']],
            'scenario_choices': [{'scenario': s['id'], **{k: v for k, v in solve(model, [s['id']]).items() if k != 'ranking'}} for s in model['scenarios']],
            'checks': checks, 'next_checks': [c['id'] for c in viable if c['total_bound'] == best],
            'stop_research': not bool(viable),
            'limits': ['Conditional on authored payoffs, scenario coverage, feasibility and observation sets.',
                       'Regret is an opportunity gap, not a forecast of actual losses; no probabilities or expected ROI.',
                       'Cost plus worst residual regret is compared with acting now against the same scenario oracle.',
                       'An inconclusive outcome can remove all guaranteed information value. Model it when possible.',
                       'A tool candidate is not a product-owner approval. Check semantic relevance and omitted scenarios.']}


def dependencies(state, model):
    core.require(core.approved(state, 'brief'), 'Approved brief required')
    for slot in ('research', 'options'):
        core.require(core.active_document(state, slot), f'Active {slot} required')
    doc_options = state['documents']['options']['content']['options']
    core.require({o['id']: o['kind'] for o in model['options']} == {o['id']: o['kind'] for o in doc_options},
                 'Lab options must match every strategy option and kind')
    refs = sorted({c for s in model['scenarios'] for c in s['claim_refs']})
    core.referenced_claims(state, refs, 1)
    return {'documents': {slot: state['documents'][slot]['sha256'] for slot in ('brief', 'research', 'options')},
            'claims': {cid: state['claims'][cid]['payload_hash'] for cid in refs}}


def commit(project, model):
    result = analyze(model)
    with core.transaction(project) as state:
        bound = dependencies(state, model)
        value = {'input': copy.deepcopy(model), 'result': result, 'dependencies': bound}
        sha = core.digest(core.canonical(value))
        old = state.get('decision_lab')
        if old and old['sha256'] == sha and old['status'] == 'active':
            return old
        blob, _ = core.put_blob(project, core.canonical(value), '.json')
        record = dict(value, sha256=sha, blob=blob, status='active', at=core.now())
        state['decision_lab'] = record
        # A different analysis must not silently inherit the previous human choice.
        core.invalidate(state, ('strategy',), 'Decision stress analysis changed; reconsider the proposed choice')
        state['approvals'].pop('decision', None)
        core.event(state, 'decision_lab_committed', {'sha256': sha, 'previous': old['sha256'] if old else None})
        return record


def verify(project, state):
    record = state.get('decision_lab')
    if not record:
        return {'status': 'absent'}
    core.require(record['status'] == 'active', 'Decision lab is stale; revise assumptions and rerun lab commit')
    value = {k: record[k] for k in ('input', 'result', 'dependencies')}
    core.require(core.digest(core.canonical(value)) == record['sha256'], 'Decision lab payload changed')
    core.require(core.project_file(project, record['blob']).read_bytes() == core.canonical(value), 'Decision lab blob changed')
    core.require(record['dependencies'] == dependencies(state, record['input']), 'Decision lab dependencies changed')
    core.require(record['result'] == analyze(record['input']), 'Decision lab calculation changed')
    events = [e for e in state['events'] if e['kind'] == 'decision_lab_committed']
    core.require(events and events[-1]['detail']['sha256'] == record['sha256'], 'Decision lab does not match its recorded event')
    return {'status': 'active', 'sha256': record['sha256'], 'candidates': record['result']['robust']['candidates'],
            'next_checks': record['result']['next_checks'], 'stop_research': record['result']['stop_research']}


def show(project):
    state = core.load(project)
    verification = verify(project, state)
    return {'verification': verification, 'analysis': state.get('decision_lab')}
