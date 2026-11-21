"""Reproduce a decision stress test and a correction to its observation model.

This is a deterministic fixture replay, not a live LLM evaluation.
"""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from strategist import core, decision_lab, report
from demo.lab_fixtures import make_model


def run(project):
    start = time.perf_counter()
    project = Path(project)
    core.require(not project.exists(), 'Use a new project path; replay never overwrites work')
    shutil.copytree(ROOT/'examples'/'replay', project)
    strategy = core.load(project)['documents']['strategy']['content']
    ideal = make_model(False)
    realistic = make_model(True)
    (project/'lab-input').mkdir()
    for name, value in [('idealized', ideal), ('with-inconclusive', realistic)]:
        core.atomic_write(project/'lab-input'/f'{name}.json', core.canonical(value))
    first = decision_lab.commit(project, ideal)
    first_result = first['result']
    # A same-model correction: admit a possible inconclusive result. No source is invented.
    second = decision_lab.commit(project, realistic)
    core.propose(project, 'focus', 'Учебный выбор: ограниченный командный пилот имеет меньшую максимальную цену ошибки в заданных сценариях. Исследование может оказаться неубедительным; гарантированная окупаемость проверки не заявляется.', ['teams-retention'])
    core.approve(project, 'decision', 'SCENARIO:owner', 'Авторский replay: условный выбор ограниченного пилота после просмотра цены ошибки, не реальное согласие владельца', simulation=True)
    core.commit_document(project, 'strategy', strategy)
    with core.transaction(project) as state:
        for cid, obligation in state['commitments'].items():
            if obligation['status'] == 'open':
                previous = obligation['decision_hash']
                obligation['decision_hash'] = state['decision']['sha256']
                core.event(state, 'commitment_carried_forward', {'id': cid, 'previous_decision_hash': previous,
                           'decision_hash': state['decision']['sha256'],
                           'reason': 'Scenario replay: demand still needs observation; no guaranteed information benefit is asserted'})
    elapsed = time.perf_counter() - start
    core.cost_add(project, 'tool', '0', 'RUB', str(elapsed), 'Measured local Python scenario replay only; excludes development, IDE, LLM and human work')
    result = report.export_report(project)
    summary = {'kind': 'authored_deterministic_replay_not_LLM_benchmark', 'seconds': elapsed,
               'idealized_next_checks': first_result['next_checks'], 'idealized_bound': first_result['checks'][0]['total_bound'],
               'corrected_next_checks': second['result']['next_checks'], 'corrected_bound': second['result']['checks'][0]['total_bound'],
               'correction': 'Added an inconclusive outcome compatible with all scenarios. This removes guaranteed information benefit, not all possible learning value.',
               'baseline_method': 'best option in reference scenario only, not a human or chat baseline',
               'reference_only': second['result']['reference_only'], 'robust': second['result']['robust'],
               'approval': 'simulated', 'audit_ok': result['ok']}
    core.atomic_write(project/'exports'/'lab-replay.json', core.canonical(summary))
    return summary


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=2))
