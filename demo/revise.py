"""Inject corrected synthetic input, prove invalidation, then replay an explicit revised choice."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.fixtures import OPTIONS, RESEARCH, STRATEGY


def revise(project):
    project = Path(project).resolve()
    folder = project/'revision-fixtures'
    if folder.exists():
        raise SystemExit('Revision replay already exists. Use a fresh demo; nothing was overwritten.')
    folder.mkdir()
    trace = []

    def cli(*args, expected=0):
        p = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'strategist', *map(str, args)],
                           cwd=ROOT, encoding='utf-8', capture_output=True, env={**os.environ, 'PYTHONUTF8': '1'})
        if p.returncode != expected:
            raise RuntimeError(p.stderr or p.stdout)
        result = json.loads(p.stdout or p.stderr)
        trace.append({'command': list(map(str, args)), 'returncode': p.returncode, 'result': result})
        return result

    def fixture(name, value):
        p = folder/(name+'.json')
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        return p

    prior = cli('resume', project)
    if not prior['demo'] or 'follow_up' not in prior['next_action']:
        raise SystemExit('Start with a completed synthetic demo, not a live project')
    # Preserve the report snapshot before correction. Never treat it as source evidence.
    old_report = project/'exports'/'strategy.md'
    (project/'exports'/'strategy-before-revision.md').write_bytes(old_report.read_bytes())
    data = (ROOT/'demo'/'inputs'/'cohorts.csv').read_text(encoding='utf-8')
    data = data.replace('400,200,120,true,36000,12000,10000', '400,200,40,true,16000,12000,10000')
    corrected = folder/'corrected-cohorts.csv'
    corrected.write_text(data, encoding='utf-8')
    cli('source', 'add', project, corrected, '--id', 'cohorts-v2', '--title', 'Синтетическая исправленная выгрузка', '--origin', 'synthetic')
    impact = cli('source', 'supersede', project, 'cohorts', '--with', 'cohorts-v2', '--reason', 'В учебной выгрузке исправлены возвращения и выручка teams')
    blocked = cli('audit', project, expected=2)
    if blocked['ok'] or 'metrics' not in impact['sources']:
        raise RuntimeError('Dependency invalidation failed')
    cli('export', project, expected=2)
    cli('analyze-cohorts', project, '--source', 'cohorts-v2', '--id', 'metrics-v2')
    claims = [
        {'id': 'teams-retention-v2', 'type': 'demo_fact', 'text': 'После исправления синтетической выгрузки teams: D30 = 80/400 = 20%, solo остаётся 30%. Причинность неизвестна.',
         'evidence': [{'source': 'metrics-v2', 'locator': 'line:1', 'quote': '"d30_per_activated":0.2'}], 'confidence': 'medium', 'confidence_reason': 'Воспроизводимая арифметика учебного исправления; не реальное измерение.'},
        {'id': 'unit-economics-v2', 'type': 'demo_fact', 'text': 'Исправленный синтетический вклад teams: 32 000 - 24 000 - 20 000 = -12 000 RUB до fixed costs; solo -6 000 RUB.',
         'evidence': [{'source': 'metrics-v2', 'locator': 'line:1', 'quote': '"contribution_after_acquisition_rub":-12000.0'}], 'confidence': 'medium', 'confidence_reason': 'Fixed costs и стоимость закрытия всё ещё неизвестны.'}]
    for claim in claims:
        cli('claim', 'add', project, fixture(claim['id'], claim))

    def references(value):
        if isinstance(value, dict):
            return {k: references(v) for k, v in value.items()}
        if isinstance(value, list):
            return [references(v) for v in value]
        return {'teams-retention': 'teams-retention-v2', 'unit-economics': 'unit-economics-v2'}.get(value, value) if isinstance(value, str) else value

    research = references(copy.deepcopy(RESEARCH))
    research['findings'][0]['conclusion'] = 'Аргумент в пользу узкого пилота ослаб: после исправления teams имеет D30 20% и отрицательный вклад. Сначала остановить расширение и решить вопрос допустимых затрат.'
    research['contradictions'].append('Предыдущая выгрузка отозвана, не усредняется с исправленной; прежние claims сохранены как review_required.')
    cli('commit', project, 'research', fixture('research', research))
    options = references(copy.deepcopy(OPTIONS))
    options['options'][0]['economics'] = 'Оба сегмента имеют отрицательный 30-дневный вклад до fixed costs; keep требует нового основания и лимита потерь.'
    options['options'][1]['economics'] = 'Teams: -12 000 RUB до fixed costs; прежний аргумент +28 000 RUB отозван. Пилот можно защищать только явно ограниченной ценностью новой информации.'
    options['recommendation'] = 'close'
    options['why_not_others'] = 'Учебный владелец не принимает дополнительные необоснованные потери; переход к плану закрытия условный, без автоматического отключения пользователей.'
    options['comparison'] = 'Исправление снимает прежнее преимущество teams. Выбор между ограниченным поиском новой информации и подготовкой закрытия зависит от допускаемых потерь; в сценарии владелец выбирает подготовку закрытия.'
    cli('commit', project, 'options', fixture('options', options))
    decision = cli('propose', project, '--option', 'close', '--rationale', 'Сценарный переход к управляемой подготовке закрытия при отрицательном вкладе обоих сегментов; фактический выход после оценки обязательств', '--claims', 'teams-retention-v2', 'unit-economics-v2')
    cli('approve', project, 'decision', '--by', 'DEMO:user', '--reason', 'Сценарный пересмотр на исправленных основаниях; не реальное согласие', '--simulation')
    strategy = references(copy.deepcopy(STRATEGY))
    strategy['option_id'] = 'close'
    strategy['product'].update(direction='Подготовить управляемое закрытие: инвентаризация обязательств и экспорта, новые продажи не расширять; не отключать пользователей без отдельного решения',
                               non_goals=['Рост и разработка enterprise-функций', 'Немедленное отключение пользователей'],
                               value='Снизить будущие потери, сохранив управляемость выхода для текущих команд',
                               economics='Оба учебных сегмента отрицательны до fixed costs. Стоимость выхода и обязательства неизвестны; получить их до исполнения закрытия.')
    strategy['product']['audience'] = 'Текущие команды и владелец портфеля'
    strategy['communication'].update(audience='Текущие команды', situation='Подготовка перехода при возможном завершении сервиса',
                                     barrier='Неясны сроки и способ забрать рабочие файлы',
                                     message='Готовится план дальнейшего обслуживания; сроки и способ переноса сообщим после проверки. Текущая возможность — общая папка внутри организации.',
                                     channels=[{'channel': 'Личный кабинет и согласованное уведомление', 'role': 'Сообщить проверенные сроки; отправка не выполнена'}])
    strategy['experiment'].update(hypothesis='До исполнения закрытия необходимо подтвердить выполнимость выхода и полноту обязательств',
                                  primary_metric='Доля текущих обязательств с владельцем и безопасным сценарием завершения',
                                  comparison='Текущий реестр обязательств против проверенного плана выхода; это операционная проверка, не A/B',
                                  allocation='Все обязательства и типы команд; без рандомизации', observation_window='10 рабочих дней на подготовку плана, фактический срок выхода отдельно',
                                  sample_plan='Полная инвентаризация договорных обязательств; при отсутствии реестра закрытие не исполнять',
                                  success_rule='Нет обязательств без владельца и срока; стоимость выхода оценена и отдельно одобрена',
                                  guardrails=['Не потерять пользовательские файлы', 'Не обещать экспорт, который не проверен'],
                                  stop_rule='Остановить исполнение при неизвестных обязательствах или непроверенной возможности переноса')
    strategy['limitations'].append('Новый выбор — сценарное решение после коррекции; старый отчёт сохранён как снимок прежних оснований, не актуальная рекомендация.')
    cli('commit', project, 'strategy', fixture('strategy', strategy))
    cli('commitment', 'add', project, fixture('exit-commitment', {
        'id': 'check-exit', 'owner': 'DEMO:владелец продукта', 'action': 'Оценить обязательства и стоимость управляемого завершения',
        'due': '2026-11-25', 'metric': 'Все обязательства имеют владельца и сценарий завершения',
        'review_trigger': 'Стоимость выхода выше консервативного продолжения или выход технически не обеспечен', 'decision_hash': decision['sha256']}))
    cli('audit', project)
    result = cli('export', project)
    def portable(value):
        if isinstance(value, dict):
            return {k: portable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [portable(v) for v in value]
        if isinstance(value, str):
            for path, label in ((str(project), '<PROJECT>'), (str(ROOT), '<REPO>')):
                value = value.replace(path, label).replace(path.replace('\\', '\\\\'), label)
        return value
    text = json.dumps(portable({'mode': 'authored_synthetic_revision', 'trace': trace}), ensure_ascii=False, indent=2)
    (project/'exports'/'revision-replay.json').write_text(text, encoding='utf-8')
    print(json.dumps({'ok': result['ok'], 'revised_option': 'close', 'affected': impact, 'prior_gate_was_blocked': True}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    revise(sys.argv[1])
