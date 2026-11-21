"""Compact decision-owner snapshot, built only from current validated state."""
import json
from html import escape as e
from pathlib import Path
from . import core
from .dashboard import rich
from .web_theme import styles


def generate(project):
    state = core.load(project)
    core.require(core.active_document(state, 'options') and state['decision'] and state['decision']['status'] == 'proposed',
                 'A current proposal with active options is required')
    result = core.audit(project)
    expected = {'Missing or stale document: strategy', 'Missing or stale human gate: decision'}
    errors = [x for x in result['errors'] if x not in expected]
    core.require(not errors, 'Resolve integrity/review issues first: ' + '; '.join(errors))
    options = state['documents']['options']['content']
    research = state['documents']['research']['content']
    decision = state['decision']
    approved = core.approved(state, 'decision')
    selected = next(o for o in options['options'] if o['id'] == decision['option_id'])
    claims = [state['claims'][cid] for cid in decision['claims']]
    packet = {'revision': state['revision'], 'created_at': core.now(), 'demo': state['demo'],
              'status': 'decision_approved' if approved else 'awaiting_owner_decision',
              'question': state['question'], 'recommended_option': selected['name'],
              'rationale': decision['rationale'], 'decision_hash': decision['sha256'],
              'strong_objections': selected['objections'], 'reversal_conditions': options['reversal_conditions'],
              'unknowns': research['unknowns'], 'why_not_others': options['why_not_others'],
              'options': options['options'], 'claims': claims, 'costs': core.cost_summary(state)}
    title = 'Выбор подтверждён владельцем' if approved else 'Решение на согласование'
    sections = '<div class="grid"><article><h2>Вопрос</h2><p>'+e(packet['question'])+'</p></article><article class="selected"><span>РЕКОМЕНДАЦИЯ</span><h2>'+e(packet['recommended_option'])+'</h2><p>'+e(packet['rationale'])+'</p></article></div>'
    for heading, value in [('Сильные возражения', packet['strong_objections']),
                           ('Что изменит решение', packet['reversal_conditions']),
                           ('Что ещё неизвестно', packet['unknowns'])]:
        sections += '<article><h2>'+heading+'</h2>'+rich(value)+'</article>'
    alternatives = '<div class="grid">'+''.join('<article><h3>'+e(o['name'])+'</h3>'+rich({'economics': o['economics'], 'objections': o['objections'], 'validation': o['validation']})+'</article>' for o in packet['options'])+'</div>'
    sections += '<details><summary>Все варианты и причины отказа</summary>'+alternatives+rich(packet['why_not_others'])+'</details>'
    evidence = ''
    for claim in claims:
        evidence += '<article><span>'+e(claim['type'])+'</span><p>'+e(claim['text'])+'</p>'
        for ev in claim.get('evidence', []):
            source = state['sources'][ev['source']]
            evidence += '<p class="small">'+e(ev['source']+' / '+ev['locator'])+': «'+e(ev['quote'])+'»</p>'
            evidence += '<p><a href="../'+e(source['blob'],quote=True)+'">Сохранённый источник</a></p>'
        evidence += '</article>'
    sections += '<details><summary>Проверяемые основания</summary>'+evidence+'</details><details><summary>Расходы и полнота измерения</summary>'+rich(packet['costs'])+'</details>'
    html='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'"><title>Карточка решения</title><style>''' + styles() + '''
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 var(--body)}
header{background-color:var(--surface);color:var(--ink);padding:30px max(20px,calc((100vw - 1040px)/2))}
header span{color:var(--pink);font-size:12px;letter-spacing:.12em}
h1{font-size:36px;line-height:1.15;margin:14px 0}
main{max-width:1080px;padding:24px 20px;margin:auto}
article{background:var(--surface);border:1px solid var(--border);border-radius:13px;padding:22px;margin-bottom:16px;overflow-wrap:anywhere}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.selected{border-left:3px solid var(--pink);background:var(--feature);color:var(--ink)}
.selected span{color:var(--pink);font-size:12px}
h2{font-size:21px;margin:0 0 12px}
h3{margin-top:0}
p{margin:8px 0}
details{padding:18px 0;border-top:1px solid var(--border)}
summary{cursor:pointer;font-weight:650;margin-bottom:15px}
a{color:var(--lilac)}
.small,footer{font-size:13px;color:var(--muted)}
dt{font-weight:600}
dd{margin:4px 0 14px}
ul{padding-left:22px}
.notice{background:var(--warning);padding:15px;border-radius:9px;margin-bottom:20px}
@media(max-width:700px){.grid{grid-template-columns:1fr}
h1{font-size:28px}}
@media print{details{display:block}
article{break-inside:avoid}}
</style></head><body>'''
    html += '<header><span>СТРАТЕГ / КАРТОЧКА ВЛАДЕЛЬЦА</span><h1>'+e(title)+'</h1><p>Снимок ревизии '+str(state['revision'])+'</p></header><main>'
    if state['demo']:
        html += '<div class="notice">Учебный сценарий: происхождение сведений указано у оснований; подтверждения владельца сценарные.</div>'
    html += sections+'<footer>Карточка — снимок. После новых данных выполните resume и создайте карточку заново. Решение владельца фиксируется отдельно через approve; просмотр карточки согласия не означает.</footer></main></body></html>'
    folder = Path(project)/'exports'
    core.atomic_write(folder/'decision-card.html', html.encode('utf-8'))
    core.atomic_write(folder/'decision-card.json', core.canonical(packet))
    return {'card': str(folder/'decision-card.html'), 'data': str(folder/'decision-card.json'),
            'status': packet['status'], 'revision': state['revision']}
