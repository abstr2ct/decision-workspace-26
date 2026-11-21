"""Replay authored synthetic fixtures through the real CLI, each step in a new process."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.fixtures import BRIEF, CLAIMS, OPTIONS, RESEARCH, STRATEGY


def run_demo(project):
    project = Path(project).resolve()
    if project.exists() and any(project.iterdir()):
        raise SystemExit('Demo target must be new/empty; existing work is never overwritten')
    trace = []
    start = time.perf_counter()

    def cli(*args):
        cmd = [sys.executable, '-X', 'utf8', '-m', 'strategist', *map(str, args)]
        t = time.perf_counter()
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})
        trace.append({'command': ['python', '-m', 'strategist', *map(str, args)], 'seconds': round(time.perf_counter()-t, 6),
                      'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise RuntimeError(result.stderr)
        print('OK ' + ' '.join(map(str, args[:2])))
        return json.loads(result.stdout)

    cli('init', project, '--name', 'Командный диск — учебный кейс', '--question', BRIEF['question'], '--demo')
    staging = project/'authored-fixtures'
    staging.mkdir()

    def fixture(name, value):
        path = staging/(name+'.json')
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    cli('commit', project, 'brief', fixture('brief', BRIEF))
    cli('approve', project, 'brief', '--by', 'DEMO:user', '--reason', 'Сценарное подтверждение брифа, не согласие реального пользователя', '--simulation')
    for sid, name in [('product', 'product.md'), ('cohorts', 'cohorts.csv'), ('interview', 'synthetic-interview.md')]:
        cli('source', 'add', project, ROOT/'demo'/'inputs'/name, '--id', sid, '--title', name, '--origin', 'synthetic')
    cli('analyze-cohorts', project, '--source', 'cohorts', '--id', 'metrics')
    for claim in CLAIMS:
        cli('claim', 'add', project, fixture(claim['id'], claim))
    cli('commit', project, 'research', fixture('research', RESEARCH))
    cli('pause', project, '--reason', 'Учебный перерыв перед сравнением вариантов')
    snapshot = cli('resume', project)
    if not snapshot['paused'] or 'options' not in snapshot['next_action']:
        raise RuntimeError('Resume did not preserve the expected stage')
    cli('continue', project)
    cli('commit', project, 'options', fixture('options', OPTIONS))
    decision = cli('propose', project, '--option', 'focus', '--rationale', 'Ограниченная обратимая проверка teams до масштабирования; причинность и спрос ещё не установлены', '--claims', 'teams-retention', 'unit-economics', 'restrictions')
    cli('approve', project, 'decision', '--by', 'DEMO:user', '--reason', 'Сценарный выбор ограниченного пилота, не реальное одобрение', '--simulation')
    cli('commit', project, 'strategy', fixture('strategy', STRATEGY))
    cli('commitment', 'add', project, fixture('commitment', {
        'id': 'check-demand', 'owner': 'DEMO:руководитель продукта', 'action': 'Подтвердить реальную задачу и оценить затраты до запуска',
        'due': '2026-11-18', 'metric': 'Наблюдения по реальным задачам; не менее 6 интервью — план, а не полученное доказательство',
        'review_trigger': 'Задача не подтверждена или fixed costs превышают консервативный вклад', 'decision_hash': decision['sha256']}))
    elapsed = round(time.perf_counter()-start, 6)
    cli('cost', project, '--category', 'tool', '--amount', '0', '--currency', 'RUB', '--seconds', elapsed,
        '--basis', 'Measured local offline fixture replay wall time before export; stdlib CLI has no per-call fee. IDE/model, search and human costs are unreported, not zero.')
    cli('audit', project)
    output = cli('export', project)
    def portable(value):
        if isinstance(value, dict):
            return {k: portable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [portable(v) for v in value]
        if isinstance(value, str):
            for path, label in ((str(project), '<PROJECT>'), (str(ROOT), '<REPO>')):
                value = value.replace(path, label).replace(path.replace('\\', '\\\\'), label)
        return value
    portable_trace = portable(trace)
    manifest = {'mode': 'authored_synthetic_fixture_replay', 'llm_calls': 0, 'elapsed_seconds_including_export': round(time.perf_counter()-start, 6),
                'model_and_human_costs': 'unreported', 'trace': portable_trace}
    (project/'exports'/'replay.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False))
    return project


if __name__ == '__main__':
    run_demo(sys.argv[1] if len(sys.argv) > 1 else ROOT/'projects'/'demo')
