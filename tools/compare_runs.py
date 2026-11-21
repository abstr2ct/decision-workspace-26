"""Compare measured baseline and agent runs. No fabricated LLM benchmark."""

import argparse
import json
from decimal import Decimal
from pathlib import Path


def compare(agent, baseline):
    required = ('task_id', 'input_sha256', 'evaluation_protocol', 'reviewer', 'wall_seconds', 'human_seconds', 'quality_checks_passed', 'quality_checks_total', 'costs', 'cost_coverage_complete')
    for run in (agent, baseline):
        if run.get('record_status') == 'UNMEASURED_TEMPLATE_NOT_A_BENCHMARK':
            raise ValueError('This is an unmeasured template; collect actual observations first')
        if any(k not in run for k in required):
            raise ValueError('Missing measurement fields: ' + ', '.join(required))
        if run['quality_checks_total'] <= 0 or not 0 <= run['quality_checks_passed'] <= run['quality_checks_total']:
            raise ValueError('Invalid quality checks')
        for key in ('wall_seconds', 'human_seconds'):
            if run[key] is None:
                continue
            v = Decimal(str(run[key]))
            if not v.is_finite() or v < 0:
                raise ValueError('Durations must be finite and nonnegative')
    for k in ('task_id', 'input_sha256', 'evaluation_protocol', 'quality_checks_total'):
        if agent[k] != baseline[k]:
            raise ValueError('Runs are not comparable: ' + k)

    def costs(run):
        total = {}
        for c in run['costs']:
            v = Decimal(str(c['amount']))
            if not v.is_finite() or v < 0:
                raise ValueError('Invalid cost')
            total[c['currency']] = total.get(c['currency'], Decimal(0)) + v
        return total

    ac, bc = costs(agent), costs(baseline)
    complete = agent['cost_coverage_complete'] is True and baseline['cost_coverage_complete'] is True
    def difference(key):
        return baseline[key]-agent[key] if baseline[key] is not None and agent[key] is not None else None

    return {'task_id': agent['task_id'], 'wall_seconds_saved': difference('wall_seconds'),
            'human_seconds_saved': difference('human_seconds'),
            'quality_checks_agent': [agent['quality_checks_passed'], agent['quality_checks_total']],
            'quality_checks_baseline': [baseline['quality_checks_passed'], baseline['quality_checks_total']],
            'cost_difference_baseline_minus_agent': {k: str(bc[k]-ac[k]) for k in ac.keys() & bc.keys()} if complete else None,
            'cost_coverage_complete': complete,
            'limits': ['Compare repeated runs and review output blind; one run is not a general performance claim',
                       'Negative savings means the agent was slower or more expensive',
                       'Unknown timing stays null; it is not zero human effort',
                       'Currencies are not converted; incomplete costs cannot establish total savings']}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--agent', required=True)
    p.add_argument('--baseline', required=True)
    a = p.parse_args()
    try:
        load = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
        print(json.dumps(compare(load(a.agent), load(a.baseline)), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.exit(2, str(e)+'\n')
