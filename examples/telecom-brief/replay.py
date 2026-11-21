"""Reproduce the telecom case through the same CLI available to an IDE agent."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]
sys.path.insert(0, str(ROOT))

from strategist import core
from render_review import render


QUESTION = 'Стоит ли пилотировать предупреждение о низком остатке и расширять охват после Q2?'
FRAME = {
    'question': QUESTION, 'objective': 'Снизить ограничения интернета из-за исчерпания общего пакета',
    'recipient': 'Руководитель направления и финансовая команда',
    'decision_owner': 'Руководитель направления вымышленного оператора',
    'constraints': ['Первый пилот на одном совместимом тарифе', 'Доступ по действующему согласию',
                    'Три предварительных человеко-месяца разработки в Q2'],
    'success_metric': 'Доля индексных номеров с ограничением в течение семи дней, среди всех распределённых семей',
    'data_available': ['Учебные исходные показатели и условия из примера брифа'],
    'next_question': 'Сколько новых подходящих семей и достоверных событий набирается за неделю?',
    'data_classification': 'public_or_own',
}


def evidence(source, locator, quote):
    return {'source':source,'locator':locator,'quote':quote}


def observation(cid, text, ev, reason):
    return {'id':cid,'text':text,'type':'demo_fact','confidence':'high','confidence_reason':reason,'evidence':ev}


def option(cid, kind, name, changes, economics, objections, validation, claims):
    return {'id':cid,'kind':kind,'name':name,'audience':'Семьи на совместимых тарифах с действующим согласием',
            'changes':changes,'economics':economics,'objections':objections,'validation':validation,'claims':claims}


def prepared_stage(revision, stage, assessment=None):
    capability = 'existing-operation'
    claims = [capability]
    if stage == 'q1':
        new_claims = [
            observation(capability, 'На совместимых тарифах уже можно выделить интернет из свободного остатка.',
                        [evidence('brief-extract','line:15','Возможность добавить интернет из свободного остатка уже существует')],
                        'Краткая выписка из примера брифа, стр. 1–3.'),
            observation('annual-gap', 'Валовая прибыль без изменений — 279 млн ₽, цель — 285 млн ₽.',
                        [evidence('brief-extract','line:9','| 282 | 275 | 279 | 285 |')],
                        'Строка исходной таблицы брифа, стр. 3.')]
        claims.append('annual-gap')
        status = 'Цели и механизм известны. Нужна сверка событий, прав и темпа набора.'
        conclusion = 'Сигнал может дополнять существующее действие, если сведения приходят вовремя.'
        unknown = 'Частота предотвратимых ограничений, пригодные тарифы и работа с отзывом разрешения'
        next_action = 'Проверить события и поток. Рассмотреть пилот на одном тарифе после проверки.'
        contrast = 'Плановые 285 млн ₽ и прогноз без изменений 279 млн ₽ задают разрыв. Связь с низким остатком пока гипотеза.'
        selected = 'pilot'
        rationale = 'Предложить проверку пилота на одном тарифе. Перед набором сверить права, окно данных и поток семей.'
    elif stage == 'reported':
        assert assessment['recommendation'] == 'hold_expansion_for_economics'
        new_claims = [observation('reported-readout',
            'В исходном срезе польза проходит порог. Экономика следующего охвата пока не подтверждена.',
            [evidence('assessment-reported','line:1','"recommendation":"hold_expansion_for_economics"')],
            'Расчёт использует первоначальный учебный срез.')]
        claims.append('reported-readout')
        status = 'На первоначальных данных снижение 3,47 п.п., интервал примерно 1,43–5,52 п.п.'
        conclusion = 'Данные отвечают правилу эффекта. Для решения об охвате нужны прямые расходы, инвестиции и оплаченные месяцы.'
        unknown = 'Нижний сценарий вклада с учётом всех дополнительных расходов'
        next_action = 'Финансист проверяет экономику следующего ограниченного охвата'
        contrast = 'Недельная польза и окупаемость отвечают на разные вопросы. Проверка пользы не устанавливает рост оплаченных месяцев.'
        selected = 'keep'
        rationale = 'Сохранить текущий охват. Перед расширением оценить экономику и согласовать нижний сценарий.'
    else:
        assert stage == 'reconciled' and assessment['recommendation'] == 'resolve_uncertainty'
        new_claims = [observation('reconciled-readout',
            'Сверка обнаружила 80 неизвестных исходов. Оценка только по известным строкам — 3,05 п.п. Диапазон по всем семьям: от −1,24 до +3,47 п.п.',
            [evidence('assessment-reconciled','line:1','"recommendation":"resolve_uncertainty"'),
             evidence('assessment-reconciled','line:1','"unknown_or_immature":{"control":0,"treatment":80}')],
            'Пересчёт на том же плане и тех же назначениях. Данные синтетические.')]
        claims.append('reconciled-readout')
        status = 'Эффект остаётся неопределённым при всех назначенных семьях.'
        conclusion = 'После восстановления реестра часть исходов неизвестна. Вывод о прохождении порога отозван. Приоритет — восстановление наблюдений.'
        unknown = 'Итог для 80 семей и подтверждённая экономика'
        next_action = 'Аналитик и владелец расчётной системы восстанавливают статусы. Финансист уточняет смету.'
        contrast = 'Оценка по известным строкам проходит 3 п.п. Нижний сценарий по всем назначенным допускает рост ограничений.'
        selected = 'repair'
        rationale = ('Сохранить охват и сначала восстановить 80 исходов. Повторить расчёт на тех же назначениях и порогах. '
                     'Решение о расширении вернуть владельцу после проверки пользы, операций и экономики.')

    if stage == 'q1':
        third_option = option('cabinet','other','Семейный кабинет',
                              'Собрать остатки, предупреждения и ручное выделение в одном разделе.',
                              'Нужны разработка кабинета, поддержка и дополнительная проверка прав доступа.',
                              ['Неизвестно, нужен ли семьям отдельный кабинет', 'Ещё одна точка доступа повышает цену ошибки'],
                              'Сравнить прохождение текущего пути и прототипа, прежде чем финансировать разработку.',claims)
    else:
        third_option = option('repair','other','Сверить данные и восстановить исходы',
                              'Согласовать реестр назначений и журнал ограничений, сохранив охват.',
                              'Дополнительная сверка занимает время аналитика и владельца расчётной системы.',
                              ['Часть исходов может быть невосстановима','Отложенный выбор может стоить срока до следующего тарифа'],
                              'Восстановить статусы и повторить проверку с той же рамкой.',claims)
    opts = [
        option('keep','status_quo','Обычное обслуживание' if stage == 'q1' else 'Сохранить охват',
               'Оставить действующее обслуживание на текущих тарифах.',
               'Дополнительное масштабирование не финансируется.',
               ['Предотвратимые перебои могут сохраниться','Польза следующего охвата проявится позже'],
               'Проверить экономику и пригодность нового охвата.',claims),
        option('pilot','focus','Сигнал и существующая операция',
               'Один тариф. Сигнал открывает существующее выделение объёма с повторной проверкой разрешения.',
               'Смету прямых расходов и ёмкость Q2 согласует владелец.',
               ['Событие может приходить слишком поздно','Польза может не покрывать расходы сопровождения'],
               'Сравнить семь дней после события. Порог, выбытия и стоп-условия зафиксированы в плане.',claims),
        third_option,
        option('close','shutdown','Остановить инициативу',
               'Вернуться к стандартному обслуживанию и оставить действующую ручную операцию.',
               'Сохранится обычная себестоимость. Освободится ресурс разработки.',
               ['Предотвратимые перебои останутся','Теряется возможность проверить недорогой сигнал'],
               'Рассмотреть при критическом инциденте без доступного исправления или устойчиво слабой экономике.',claims),
    ]
    research = {
        'questions':[{'question':'Подтверждены ли польза и экономика следующего охвата?',
                      'decision_impact':'Определяет Q1 пилот и Q2 расширение',
                      'method':'Фиксированный план и проверка агрегированных событий','status':status}],
        'findings':[{'conclusion':conclusion,'claims':claims,'limits':'Учебные данные. Прогноз оплаченных месяцев остаётся условным.'}],
        'unknowns':[{'unknown':unknown,'decision_impact':'Расширение требует надёжного основания','next_action':next_action}],
        'contradictions':[contrast],
        'stop_rule':'Пауза при критическом случае. До завершения окна и проверки данных решения об охвате не принимать.',
    }
    options = {'options':opts,'recommendation':selected,'comparison':'Один тариф и одинаковый период эффекта и затрат',
               'why_not_others':'Отдельный кабинет требует сравнения с сигналом. Расширение зависит от проверенных данных и экономики.',
               'reversal_conditions':['Восстановленные данные и экономика проходят правила — рассмотреть ограниченный следующий охват.',
                                      'Критический случай доступа или списания — приостановить пилот.']}
    return {'base_revision':revision,'claims':new_claims,'research':research,'options':options,
            'proposal':{'option_id':selected,'claims':claims,'rationale':rationale}}


def initial_strategy():
    return {
        'option_id':'pilot','claims':['existing-operation','annual-gap'],
        'product':{'audience':'Организатор семейной группы на совместимом тарифе','job':'Выделить близкому часть объёма вовремя',
                   'alternatives':['Ручная проверка в кабинете','Сообщение в семейном чате'],
                   'direction':'Проверить уведомление со ссылкой на действие',
                   'non_goals':['Автоматический перевод объёма','Начисления участника','Телеметрия устройств'],
                   'value':'Сократить долю ограничений после первого подходящего события',
                   'economics':'При ставке 500 ₽ на оплаченный номеро-месяц гипотеза о жизнеспособности требует измерений'},
        'communication':{'audience':'Организатор и участник','situation':'Мало интернета в выделенной доле',
                         'barrier':'Причина и доступное действие заранее могут быть не видны',
                         'message':'На подходящем тарифе вы можете выделить интернет из свободного общего пакета.',
                         'proof':[{'statement':'Выделение объёма доступно','claims':['existing-operation'],
                                   'qualification':'Тариф совместим. Есть право распоряжения и свободный объём.'}],
                         'channels':[{'channel':'Личный кабинет','role':'Управление группой и выполнение действия'},
                                     {'channel':'Поддержка','role':'Разбор операции и разрешений'}],
                         'promise_checks':[{'promise':'Выделить доступный интернет','product_capability':'Действующее ручное выделение',
                                            'claims':['existing-operation'],'restrictions':'Совместимый тариф, право, свободный объём'}]},
        'experiment':{'hypothesis':'Сигнал даст достаточно времени до ограничения',
                      'primary_metric':'Ограничение от исчерпания на индексном номере',
                      'comparison':'Существующее ручное действие без сигнала','allocation':'1:1 по семьям',
                      'observation_window':'7 дней с первого подходящего события',
                      'sample_plan':'1638 семей на плечо при условном 12% → 9%',
                      'success_rule':'Снижение не менее 3 п.п. по всем назначенным, нижняя граница интервала выше нуля',
                      'guardrails':['Доступ после отзыва','Двойное списание','Порог операций 99%'],
                      'stop_rule':'Приостановить при критическом случае. При нехватке исходов продлить проверку.',
                      'owner':'Руководитель направления'},
        'limitations':['Фиксированное окно и один индексный номер на семью. Все сведения учебные.',
                       'Предупреждение — проект пилота. Обещание ограничено существующей операцией.'],
    }


def run(destination):
    phase_paths = {'q1':destination/'q1', 'reported':destination/'q2-reported', 'reconciled':destination/'q2-reconciled'}
    if any(path.exists() for path in phase_paths.values()) or (destination/'trace.json').exists():
        raise ValueError('Choose a new destination for the replay')
    destination.mkdir(parents=True, exist_ok=True)
    trace = []
    started_run = time.perf_counter()

    def call(phase, project, command, *args, expected=0):
        if isinstance(command,str):
            command = [command]
        arguments = [*command,str(project),*map(str,args)]
        started = time.perf_counter()
        completed = subprocess.run([sys.executable,'-X','utf8','-m','strategist',*arguments],
                                   cwd=ROOT,capture_output=True,encoding='utf-8')
        def portable(text):
            return text.replace(str(destination).replace('\\','\\\\'), '<demo>').replace(str(ROOT).replace('\\','\\\\'), '<repo>').replace(str(destination),'<demo>').replace(str(ROOT),'<repo>')
        trace.append({'phase':phase,'args':[portable(a) for a in arguments],'exit':completed.returncode,
                      'seconds':time.perf_counter()-started,'stdout':portable(completed.stdout),
                      'stderr':portable(completed.stderr)})
        if completed.returncode != expected:
            raise RuntimeError(completed.stderr or completed.stdout)
        return json.loads(completed.stdout) if completed.stdout.strip() else None

    def store(project, name, value):
        path = project/name
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        return path

    def prepare(phase, project, assessment=None):
        revision = call(phase,project,'resume')['revision']
        bundle = store(project,'prepared.json',prepared_stage(revision,phase,assessment))
        return call(phase,project,'checkpoint',bundle)

    q1 = phase_paths['q1']
    call('q1',q1,'init','--name','Семейная связь','--question',QUESTION,'--demo')
    call('q1',q1,['source','add'],CASE/'source-notes.md','--id','brief-extract','--title','Выписка из примера брифа','--origin','synthetic')
    call('q1',q1,'commit','brief',store(q1,'brief.json',FRAME))
    call('q1',q1,'approve','brief','--by','Сценарный владелец','--reason','Воспроизведение согласования рамки из учебного примера','--simulation')
    plan = call('q1',q1,['pilot','plan'],CASE/'pilot-plan.json','--id','family-pilot','--origin','synthetic')
    prepare('q1',q1)
    approved = call('q1',q1,'approve','decision','--by','Сценарный владелец','--reason','Сценарное согласие на ограниченный пилот после проверки условий','--simulation')
    call('q1',q1,'commit','strategy',store(q1,'strategy.json',initial_strategy()))
    commitment = store(q1,'commitment.json',{'id':'verify-readout','decision_hash':approved['target'],
        'owner':'Аналитик и владелец расчётной системы','action':'Сверить назначения, статусы операций и ограничения до решения Q2',
        'due':'2027-06-30','metric':'Семидневный исход у всех назначенных семей и подтверждённые операции',
        'review_trigger':'Новая сверка меняет полноту событий или критический случай требует паузы'})
    call('q1',q1,['commitment','add'],commitment)
    call('q1',q1,'audit')
    call('q1',q1,'export')
    call('q1',q1,'decision-card')
    call('q1',q1,'pause','--reason','Контрольная точка до поступления результатов Q2')
    assert call('q1',q1,'resume')['paused']

    reported = phase_paths['reported']
    shutil.copytree(q1,reported)
    restored = call('reported',reported,'resume')
    assert restored['paused'] and restored['decision']['option_id'] == 'pilot'
    call('reported',reported,'continue')
    call('reported',reported,['source','add'],CASE/'observations/reported.json','--id','results-reported','--title',
         'Первоначальный учебный срез Q2','--origin','synthetic')
    first = call('reported',reported,['pilot','evaluate'],'--plan','family-pilot','--results','results-reported','--id','assessment-reported')
    prepare('reported',reported,first)
    call('reported',reported,'decision-card')

    reconciled = phase_paths['reconciled']
    shutil.copytree(reported,reconciled)
    impact = call('reconciled',reconciled,'impact','results-reported')
    assert impact['decision_directly_affected'] and 'assessment-reported' in impact['affected_sources']
    call('reconciled',reconciled,['source','add'],CASE/'observations/reconciled.json','--id','results-reconciled','--title',
         'Срез Q2 после сверки статусов','--origin','synthetic')
    withdrawal = call('reconciled',reconciled,['source','supersede'],'results-reported','--with','results-reconciled',
         '--reason','80 неизвестных исходов в пилотном плече были ошибочно отнесены к отсутствию ограничения')
    call('reconciled',reconciled,'decision-card',expected=2)
    final = call('reconciled',reconciled,['pilot','evaluate'],'--plan','family-pilot','--results','results-reconciled','--id','assessment-reconciled')
    checkpoint = prepare('reconciled',reconciled,final)
    call('reconciled',reconciled,'decision-card')
    call('reconciled',reconciled,'export','--draft')
    finish = call('reconciled',reconciled,'resume')
    assert not checkpoint['decision_approved'] and finish['decision']['option_id'] == 'repair'
    assert [item['id'] for item in finish['open_commitments'] if item['decision_stale']] == ['verify-readout']

    summary = {'kind':'Authored offline telecom replay with actual CLI outputs and synthetic observations',
               'plan':plan,'q1_revision':restored['revision'],'final_revision':finish['revision'],
               'first':first,'final':final,'impact':impact,'withdrawal':withdrawal,'commands':trace,
               'elapsed_seconds':time.perf_counter()-started_run,
               'cli_seconds':sum(line['seconds'] for line in trace)}
    store(destination,'trace.json',summary)
    (destination/'review.html').write_text(render(summary),encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args = parser.parse_args()
    result = run(args.destination.resolve())
    print(json.dumps({'status':'ok','commands':len(result['commands']),
                      'elapsed_seconds':round(result['elapsed_seconds'],3),
                      'recommendation':result['final']['recommendation']},ensure_ascii=False))
