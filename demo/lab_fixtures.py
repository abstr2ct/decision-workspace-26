"""Authored numerical assumptions, NOT data observed in the cohort fixture."""
import copy

OPTIONS = [
    {'id': 'keep', 'name': 'Сохранить текущий подход', 'kind': 'status_quo', 'violations': []},
    {'id': 'focus', 'name': 'Ограничить пилот командами', 'kind': 'focus', 'violations': []},
    {'id': 'expand', 'name': 'Масштабировать привлечение', 'kind': 'expand', 'violations': []},
    {'id': 'close', 'name': 'Закрыть направление', 'kind': 'shutdown', 'violations': []},
]


def make_model(ambiguous=True):
    # Monetary values are pedagogical assumptions. No ROI is inferred from fixtures.
    scenarios = [
        ('broad-demand', 'Широкий спрос', 'Спрос выходит за пределы команд, экономика масштабирования положительна.',
         [20000, 60000, 100000, 0], 'Сравнимая зрелая когорта нового сегмента не удерживается или вклад после привлечения отрицателен.'),
        ('team-niche', 'Только команды', 'Польза подтверждается лишь у команд; широкий канал не окупается.',
         [5000, 45000, 10000, 0], 'Внешний сегмент показывает сопоставимую пользу и вклад при одинаковом окне.'),
        ('no-need', 'Нет достаточной пользы', 'Наблюдаемое удержание не превращается в достаточную готовность платить.',
         [-10000, -20000, -70000, 0], 'Появляется наблюдаемое повторное платное использование в выбранном сегменте.'),
        ('bad-margin', 'Расходы недооценены', 'Полная стоимость поддержки и привлечения съедает вклад.',
         [-25000, -35000, -110000, -5000], 'Полная проверяемая калькуляция и реальные повторные оплаты подтверждают положительный вклад.'),
    ]
    result = {'schema_version': 1, 'title': 'Командный диск: продолжать пилот, масштабировать или закрывать?',
              'unit': 'RUB', 'metric_definition': 'Условный дополнительный денежный вклад за горизонт после затрат варианта; не прибыль, не LTV и не измеренная экономика',
              'horizon': '8 недель; сравнивается один и тот же объём инициативы', 'higher_is_better': True,
              'payoff_status': 'assumption', 'research_budget': 15000, 'reference_scenario': 'broad-demand',
              'coverage_limits': 'Четыре авторских сценария не покрывают все будущие состояния. Числа учебные; когорты объясняют вопрос, но не доказывают эти значения. Вероятности неизвестны.',
              'constraints': [], 'options': copy.deepcopy(OPTIONS), 'scenarios': [], 'checks': []}
    for sid, name, assumption, values, falsifier in scenarios:
        payoffs = dict(zip([o['id'] for o in OPTIONS], values))
        result['scenarios'].append({'id': sid, 'name': name, 'assumption': assumption, 'falsifier': falsifier,
                                   'claim_refs': ['teams-retention'], 'payoffs': payoffs,
                                   'payoff_rationale': {oid: f'Авторское допущение {value} RUB: иллюстрация результата варианта в сценарии «{name}» после условных затрат. Не рассчитано из когорт.' for oid, value in payoffs.items()}})
    ids = [s['id'] for s in result['scenarios']]
    full = [{'id': 'broad', 'label': 'Подтверждён широкий спрос и экономика', 'scenarios': [ids[0]]},
            {'id': 'niche', 'label': 'Подтверждена только командная ниша', 'scenarios': [ids[1]]},
            {'id': 'negative', 'label': 'Недостаточная польза или экономика', 'scenarios': ids[2:]}]
    if ambiguous:
        full.append({'id': 'inconclusive', 'label': 'Результат не позволяет различить сценарии', 'scenarios': ids})
    common = {'observation_model': 'authored_possibility_sets', 'duration': 'До 2 недель в модели; срок не измерен',
              'cost_basis': 'Авторская оценка в RUB для сравнения, не счёт подрядчика. Цена задержки входит отдельно.',
              'limitations': 'Связь результата со сценариями задана автором; диагностическая способность не проверена. Это не данные исследования.'}
    result['checks'] = [
        dict(common, id='targeted-pilot', name='Проверка поведения и полной экономики',
             question='Можно ли различить широкий спрос, командную нишу и отсутствие устойчивой пользы?',
             method='Наблюдать оплачиваемое использование и собрать полные затраты для сравнимых когорт. Без реальных данных результат может быть неубедительным.',
             cost=10000, delay_cost=2000, outcomes=full),
        dict(common, id='broad-survey', name='Широкое исследование рынка',
             question='Даже при идеальном ответе оправдана ли цена полного обзора?',
             method='Идеализированная полная диагностика для верхней границы пользы; обычный опрос такой гарантии не даёт.',
             cost=55000, delay_cost=5000, outcomes=copy.deepcopy(full[:3])),
        dict(common, id='opinion-interviews', name='Интервью только о намерениях',
             question='Различают ли декларируемые намерения спрос и экономику?',
             method='Ответы о намерениях без наблюдений платежей и затрат не устраняют ни один из четырёх сценариев.',
             cost=2000, delay_cost=1000, outcomes=[{'id': 'opinions', 'label': 'Мнения собраны, поведение и расходы неизвестны', 'scenarios': ids}]),
    ]
    return result
