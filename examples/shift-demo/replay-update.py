"""Replay the authored continuation from a saved LLM run using real CLI tools."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = ROOT / 'benchmarks/live-pilot-v1/inputs'
BEFORE = ROOT / 'examples/owner-review'


def run(project):
    if project.exists():
        raise ValueError('Choose a new project folder')
    shutil.copytree(BEFORE, project)
    trace = []

    def call(*args, expected=0):
        command = [sys.executable, '-X', 'utf8', '-m', 'strategist', *args]
        start = time.perf_counter()
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8')
        trace.append({'args': ['python', '-m', 'strategist', *[str(a).replace(str(project), '<project>').replace(str(ROOT), '<repo>') for a in args]],
                      'process_exit_code': proc.returncode, 'seconds': time.perf_counter()-start,
                      'stdout': proc.stdout.replace(str(project).replace('\\', '\\\\'), '<project>'), 'stderr': proc.stderr})
        if proc.returncode != expected:
            raise RuntimeError(proc.stderr or proc.stdout)
        return json.loads(proc.stdout) if proc.stdout.strip() else None

    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    project = project.resolve()
    resumed = call('resume', str(project))
    impact = call('impact', str(project), 'cohorts')
    initial = json.loads((project/'state.json').read_text(encoding='utf-8'))
    original_csv = INPUTS/'cohorts.csv'
    assert hashlib.sha256(original_csv.read_bytes()).hexdigest() == initial['sources']['cohorts']['sha256']
    source_note = INPUTS/'correction.md'
    note = source_note.read_text(encoding='utf-8').splitlines()[1]
    with original_csv.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fields = reader.fieldnames
    target = [row for row in rows if (row['cohort'], row['segment']) == ('2026-09', 'teams')]
    assert len(target) == 1
    row = target[0]
    assert [row[k] for k in ('retained_d30', 'revenue_rub', 'variable_cost_rub')] == ['13', '13000', '4000']
    updated_csv = project/'corrected-cohorts.csv'
    row.update(retained_d30='5', revenue_rub='5000', variable_cost_rub='16000')
    with updated_csv.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    call('source', 'add', str(project), str(source_note), '--id', 'analyst-correction', '--title', 'Учебное исправление аналитика', '--origin', 'synthetic')
    call('source', 'add', str(project), str(updated_csv), '--id', 'cohorts-corrected', '--title', 'Когорты после исправления', '--origin', 'synthetic')
    call('source', 'supersede', str(project), 'cohorts', '--with', 'cohorts-corrected', '--reason', 'Исправлены удержание, выручка и затраты строки 2026-09 teams по записке аналитика')
    call('decision-card', str(project), expected=2)
    mix_record = call('analyze-cohorts', str(project), '--source', 'cohorts-corrected', '--id', 'corrected-period-comparison', '--compare', '2026-08', '2026-09')
    mix = json.loads((project/mix_record['blob']).read_text(encoding='utf-8'))
    assert (mix['current_d30'], mix['within_segment_change_pp'], mix['mix_change_pp']) == (.25, -27, 0)
    def contribution(item):
        return int(item['revenue_rub']) - int(item['variable_cost_rub']) - int(item['acquisition_cost_rub'])
    team_contribution = contribution(row)
    september = sum(contribution(item) for item in rows if item['cohort'] == '2026-09')
    assert (team_contribution, september) == (-15000, -23000)
    write(project/'recalculation.json', {'d30_bridge':mix, 'september_teams_contribution_rub':team_contribution,
                                       'september_total_contribution_rub':september, 'corrected_row':row})
    evidence = [
        {'id':'correction-confirmed', 'type':'demo_fact', 'text':'Учебный аналитик исправил одну строку за сентябрь.', 'confidence':'high',
         'confidence_reason':'Сценарное исправление зафиксировано в записке.',
         'evidence':[{'source':'analyst-correction','locator':'line:2','quote':note}]},
        {'id':'corrected-d30', 'type':'demo_fact', 'text':'Сентябрьский D30 равен 25%. Разложение относительно августа: внутри сегментов −27 п.п., изменение состава 0 п.п.',
         'confidence':'high','confidence_reason':'Расчёт на заданной учебной таблице. Причины не установлены.',
         'evidence':[{'source':'corrected-period-comparison','locator':'line:1','quote':'"current_d30":0.25'},
                     {'source':'corrected-period-comparison','locator':'line:1','quote':'"within_segment_change_pp":-27.0'}]},
        {'id':'corrected-contribution', 'type':'demo_fact', 'text':'Вклад команд за сентябрь после привлечения равен −15 000 ₽: 5 000 − 16 000 − 4 000.',
         'confidence':'high','confidence_reason':'Три статьи одной зрелой строки. Постоянные расходы и будущие потоки не включены.',
         'evidence':[{'source':'cohorts-corrected','locator':'row:4','quote':'2026-09'}]}
    ]
    research = {'questions':[{'question':'Сохраняется ли объяснение через состав аудитории?','decision_impact':'Меняет целесообразность увеличения закупок','method':'Повторить расчёт на исправленной таблице','status':'Расчёт выполнен, ожидается сверка событий'}],
                'findings':[{'conclusion':'В исправленной таблице изменение внутри сегментов объясняет −27 п.п. в выбранном разложении.',
                             'claims':['corrected-d30','correction-confirmed'],'limits':'Описательный расчёт, малая выборка, причины не установлены'},
                            {'conclusion':'Сентябрьский вклад команд после привлечения отрицателен.',
                             'claims':['corrected-contribution'],'limits':'30 дней и три статьи, без постоянных расходов и повторных доходов'}],
                'unknowns':[{'unknown':'Причины снижения и экономика повторных месяцев','decision_impact':'Определяет условия пилота, продолжения и закрытия',
                             'next_action':'Сверить события и учёт, собрать сопоставимые зрелые когорты'}],
                'contradictions':['Исправление строки отменяет оценку сентябрьского D30 команд в 65% и положительный вклад +5 000 ₽. Исходная версия хранится в истории.'],
                'stop_rule':'День 14 или достижение лимита сверки 8 000 ₽ после согласования владельцем'}
    def option(oid, kind, name, changes, economics, objections, validation, claims):
        return dict(id=oid,kind=kind,name=name,audience='Администраторы команд до 20 сотрудников',changes=changes,
                    economics=economics,objections=objections,validation=validation,claims=claims)
    options = {'options':[
        option('keep','status_quo','Статус-кво продукта и сверка','Сохранить путь и текущий объём. Отложить дополнительное привлечение.',
               'Предложенный потолок сверки 8 000 ₽ на 14 дней.',
               ['Задержка при настоящем барьере','Текущие расходы сохраняются'],'Сверить события и три статьи вклада; решение владельца на дне 14.',
               ['corrected-d30','corrected-contribution']),
        option('focus','focus','Диагностика пути команд','Проверить существующий путь от первой смены до приглашения.',
               'Запрашивать финансирование пилота после сверки.',
               ['Сбой может быть в канале или трекинге','Улучшение UX может не окупиться'],'Воспроизвести барьер и оценить цену проверки.',
               ['capability','ux','corrected-contribution']),
        option('rewrite','other','Полная переделка онбординга','Обновить весь путь для сегментов.',
               'Стоимость разработки и влияние неизвестны.',
               ['Интерактивный пример уже есть','Не устранит учётную ошибку'],'Подтвердить повторяемую проблему в нескольких шагах и оценить затраты.',
               ['capability','roadmap','correction-confirmed']),
        option('close','shutdown','Закрытие направления','Проверить план выхода и поддержку клиентов.',
               'Экономия зависит от устранимых расходов и стоимости выхода.',
               ['Одна исправленная когорта не определяет будущий вклад','Выход может оказаться дороже продолжения'],'Сравнить повторные доходы, затраты и обязательства на одном горизонте.',
               ['fixed','corrected-contribution'])],
        'recommendation':'keep','comparison':'Одинаковый горизонт первичного решения 14 дней, приоритет обратимых действий.',
        'why_not_others':'Пилот требует сверки, переделка требует подтверждённого барьера, закрытие требует экономики выхода.',
        'reversal_conditions':['События подтверждают устойчивый барьер — рассмотреть ограниченный UX-пилот.',
                               'Сопоставимые зрелые когорты подтверждают приемлемый вклад — вернуться к вопросу закупок.',
                               'Продолжение устойчиво слабее выхода на едином горизонте — вынести закрытие на выбор владельца.']}
    revision = call('resume', str(project))['revision']
    bundle = {'base_revision':revision,'claims':evidence,'research':research,'options':options,
              'proposal':{'option_id':'keep','claims':['corrected-d30','corrected-contribution','capability'],
                          'rationale':'Отложить увеличение закупок и изменения продукта. Сверить зрелые когорты и экономику за 14 дней с предложенным лимитом 8 000 ₽.'}}
    bundle_file = project/'prepared-update.json'
    write(bundle_file,bundle)
    call('checkpoint', str(project), str(bundle_file))
    call('decision-card', str(project))
    call('export', str(project), '--draft')
    final = call('resume', str(project))
    assert final['decision']['option_id'] == 'keep'
    saved = json.loads((project/'state.json').read_text(encoding='utf-8'))
    assert 'decision' not in saved['approvals']
    assert saved['sources']['cohorts']['status'] == 'superseded'
    assert saved['claims']['cohort-summary']['status'] == 'review_required'
    write(project/'submission-trace.json', {'kind':'CLI continuation from a saved LLM run with authored revision',
                                            'starting_revision':resumed['revision'],'final_revision':final['revision'],
                                            'impact':impact,'commands':trace})
    return len(trace), sum(item['seconds'] for item in trace)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    args = parser.parse_args()
    calls, seconds = run(args.project.resolve())
    print(json.dumps({'commands':calls,'cli_seconds':round(seconds,3)}))
