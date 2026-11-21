"""Portable, escaped HTML decision report. No server or external assets needed."""

from html import escape as e
from pathlib import Path

from .core import atomic_write, cost_summary, project_file, read_json, resume
from .web_theme import styles

LABELS = {
 'audience':'Аудитория','job':'Задача пользователя','alternatives':'Альтернативы','direction':'Направление','non_goals':'Осознанные отказы',
 'value':'Польза','economics':'Экономика','situation':'Ситуация','barrier':'Барьер выбора','message':'Сообщение','proof':'Основания обещаний',
 'changes':'Изменения','objections':'Сильные возражения','validation':'Проверка',
 'channels':'Роль каналов','promise_checks':'Проверка обещаний','hypothesis':'Гипотеза','primary_metric':'Основная метрика',
 'comparison':'Сравнение','allocation':'Распределение','observation_window':'Срок наблюдения','sample_plan':'План выборки',
 'success_rule':'Условие успеха','guardrails':'Нежелательные эффекты','stop_rule':'Правило остановки','owner':'Ответственный',
 'claims':'Выводы','statement':'Утверждение','qualification':'Ограничение','channel':'Канал','role':'Роль','promise':'Обещание',
 'product_capability':'Возможность продукта','restrictions':'Границы','unknown':'Что неизвестно','decision_impact':'Влияние на выбор',
 'next_action':'Следующий шаг','question':'Вопрос','method':'Метод','status':'Статус','conclusion':'Вывод','limits':'Ограничения',
 'action':'Обязательство','due':'Срок','metric':'Метрика','review_trigger':'Условие пересмотра','confidence':'Уверенность'}


def rich(value):
    if isinstance(value, dict):
        first=('unknown','question','conclusion','action','audience','job','situation','barrier','message','hypothesis','primary_metric')
        keys=sorted(value,key=lambda k:(first.index(k) if k in first else len(first),list(value).index(k)))
        return '<dl>'+''.join(f'<dt>{e(LABELS.get(k,k))}</dt><dd>{rich(value[k])}</dd>' for k in keys)+'</dl>'
    if isinstance(value, list):
        return '<ul>'+''.join(f'<li>{rich(v)}</li>' for v in value)+'</ul>'
    return e(str(value))


def generate(project, state, audit):
    summary = resume(project)
    docs = {k:v['content'] for k,v in state['documents'].items()}
    decision = state['decision'] or {}
    options = docs.get('options', {}).get('options', [])
    chosen = next((o for o in options if o['id']==decision.get('option_id')), {})
    panes = []

    def pane(id, title, content):
        panes.append((id,title,f'<section id="{id}" class="pane">{content}</section>'))

    def card(title, content):
        return f'<article class="card"><h2>{e(title)}</h2>{content}</article>'

    alerts = ''
    if state['demo']:
        alerts += '<div class="notice">Демонстрационный проект. Подтверждения владельца сценарные. Происхождение каждого источника показано отдельно.</div>'
    if not audit['ok']:
        alerts += '<div class="notice danger">Черновик: аудит не пройден. Использовать как утверждённую стратегию нельзя.</div>'
    overview = alerts + '<div class="grid">'
    if state.get('decision_lab'):
        overview = alerts + '<div class="notice"><b>Лаборатория решений</b>: <a href="decision-lab.html">сценарии, цена ошибки и следующая проверка</a>. Актуальность анализа проверяется audit; все значения являются допущениями.</div><div class="grid">'
    overview += card('Вопрос решения', f'<p class="lead">{e(state["question"])}</p>')
    overview += card('Рекомендация и выбор', f'<h3>{e(chosen.get("name","Выбор ещё не подтверждён"))}</h3><p>{e(decision.get("rationale", "Сначала исследование и сравнение вариантов"))}</p>')
    overview += '</div>' + card('Что способно изменить решение', rich(docs.get('options',{}).get('reversal_conditions', [])))
    overview += card('Что ещё неизвестно', rich(docs.get('research',{}).get('unknowns', [])))
    overview += card('Ограничения результата', rich(docs.get('strategy',{}).get('limitations', [])))
    pane('overview','Обзор',overview)
    option_cards = ''
    for o in options:
        option_cards += card(('✓ ' if o['id']==decision.get('option_id') else '')+o['name'], rich({k:o[k] for k in ('audience','changes','economics','objections','validation','claims')}))
    pane('options','Варианты', '<div class="grid">'+option_cards+'</div>'+card('Почему отвергнуты остальные', rich(docs.get('options',{}).get('why_not_others',''))))
    strategy = docs.get('strategy',{})
    pane('strategy','Стратегия', '<div class="grid">'+card('Продуктовая стратегия',rich(strategy.get('product',{})))+card('Коммуникационная стратегия',rich(strategy.get('communication',{})))+'</div>')
    pane('experiment','Проверка',card('План проверки',rich(strategy.get('experiment',{})))+card('Обязательства',rich(summary['open_commitments'])))
    claims = '<div class="filters"><input id="claim-search" placeholder="Найти вывод или источник" aria-label="Поиск выводов"><select id="claim-type" aria-label="Тип вывода"><option value="">Все типы</option><option>fact</option><option>demo_fact</option><option>hypothesis</option><option>forecast</option></select></div>'
    for cid,c in state['claims'].items():
        refs = ''
        for ev in c.get('evidence',[]):
            refs += f'<p><a href="#source-{e(ev["source"])}" class="source-ref">{e(ev["source"])} / {e(ev["locator"])}</a></p>'
        claims += f'<article class="card claim" data-type="{e(c["type"])}"><span class="badge">{e(c["type"])} · {e(c["status"])}</span><h2>{e(cid)}</h2><p>{e(c["text"])}</p><p class="muted">{e(c["confidence"])}: {e(c["confidence_reason"])}</p>{refs}</article>'
    pane('claims','Основания',claims)
    sources = ''
    for sid,s in state['sources'].items():
        url = f'<a href="{e(s["url"],quote=True)}" target="_blank" rel="noopener noreferrer">Оригинальный источник ↗</a>' if (s['url'] or '').startswith('https://') else ''
        chunks = read_json(project_file(project,s['chunks']))
        sources += f'<article class="card" id="source-{e(sid)}"><span class="badge">{e(s["origin"])} · {e(s["status"])}</span><h2>{e(s["title"])}</h2><p>{url}</p><p class="hash">SHA-256: {e(s["sha256"])}</p><details><summary>Сохранённый текст — недоверенные данные</summary>'
        sources += ''.join(f'<p><code>{e(c["locator"])}</code> {e(c["text"])}</p>' for c in chunks)
        sources += '</details></article>'
    pane('sources','Источники',sources)
    pane('cost','Расходы и журнал',card('Полнота расходов',rich(cost_summary(state)))+card('Записи расходов',rich(state['costs']))+card('Последние события',rich(state['events'][-10:]))+card('Проверка',rich(audit)))
    buttons = ''.join(f'<button class="tab" data-panel="{id}">{e(title)}</button>' for id,title,_ in panes)
    body = ''.join(content for _,_,content in panes)
    html = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; font-src data:; img-src data:; base-uri 'none'; form-action 'none'">
<title>Стратег · Решение и основания</title><style>''' + styles() + '''
:root{font:16px/1.6 var(--body);color:var(--ink);background:var(--page)}
*{box-sizing:border-box}
body{margin:0}
header{background-color:var(--surface);color:var(--ink);padding:34px max(24px,calc((100vw - 1180px)/2))}
header .eyebrow{font-size:12px;letter-spacing:.18em;color:var(--pink)}
h1{font-size:clamp(28px,4vw,45px);line-height:1.22;margin:12px 0}
header p{margin:6px 0;opacity:.8}
nav{max-width:1180px;margin:22px auto;display:flex;gap:6px;flex-wrap:wrap;padding:0 20px}
.tab{font:inherit;border:1px solid var(--border);padding:10px 14px;border-radius:8px;cursor:pointer;background:var(--surface);color:var(--ink)}
.tab.active{background:var(--feature);border-color:var(--pink);color:var(--ink)}
main{max-width:1180px;padding:0 20px 40px;margin:auto}
.pane{display:none}
.pane.active{display:block}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.card{background:var(--surface);border:1px solid var(--border);padding:22px;border-radius:12px;margin:0 0 18px;overflow-wrap:anywhere}
.grid .card{height:calc(100% - 18px)}
h2{font-size:19px;margin:0 0 12px;color:var(--pink)}
h3{font-size:20px;margin:8px 0}
p{margin:8px 0}
.lead{font-size:20px}
.muted,.hash{font-size:13px;color:var(--muted)}
.hash{font-family:ui-monospace,monospace}
.badge{font-size:12px;display:inline-block;padding:3px 9px;border-radius:20px;background:var(--raised);margin-bottom:10px}
a{color:var(--lilac)}
dl{margin:0}
dt{font-weight:650;margin-top:14px}
dd{margin:3px 0 12px}
ul{padding-left:22px;margin:6px 0}
.notice{color:var(--ink);padding:16px 20px;background:var(--warning);border-left:4px solid var(--lilac);border-radius:8px;margin-bottom:20px}
.danger{background:var(--danger);border-color:var(--coral)}
.filters{display:flex;gap:10px;margin-bottom:18px}
input,select{font:inherit;background:var(--surface);color:var(--ink);padding:10px;border:1px solid var(--border);border-radius:8px}
input{flex:1;min-width:0}
details{border-top:1px solid var(--border);padding-top:10px}
summary{cursor:pointer}
footer{color:var(--muted);font-size:12px;padding-top:20px}
@media(max-width:700px){.grid{grid-template-columns:1fr}
h1{font-size:26px}
.card{padding:18px}
header{padding:28px 20px}
.filters{flex-direction:column}}
@media print{nav,.filters{display:none}
.pane{display:block!important}
.card{break-inside:avoid}
.grid{display:block}
header{background-color:var(--surface);color:var(--surface);padding:0}
body{background:var(--surface)}}
</style></head><body>'''
    html += f'<header><div class="eyebrow">СТРАТЕГ ФАБРИКИ ПРОДУКТОВ</div><h1>{e(state["name"])}</h1><p>Снимок ревизии {state["revision"]} · {"аудит пройден" if audit["ok"] else "требует пересмотра"} · статус решения в журнале</p></header><nav aria-label="Разделы отчёта">{buttons}</nav><main>{body}<footer>Отчёт — снимок. Перед использованием после новых данных запустите resume и audit. Источники проверяют атрибуцию, а не истинность интерпретации.</footer></main>'
    html += '''<script>
const tabs=[...document.querySelectorAll('.tab')];function show(id){tabs.forEach(t=>{const on=t.dataset.panel===id;t.classList.toggle('active',on);t.setAttribute('aria-selected',String(on))});document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('active',p.id===id))}tabs.forEach(t=>t.addEventListener('click',()=>show(t.dataset.panel)));show('overview');document.querySelectorAll('.source-ref').forEach(a=>a.addEventListener('click',()=>{show('sources');const el=document.querySelector(a.getAttribute('href'));if(el){el.querySelector('details').open=true;setTimeout(()=>el.scrollIntoView({behavior:'smooth'}),0)}}));function filter(){const q=document.querySelector('#claim-search').value.toLocaleLowerCase(),type=document.querySelector('#claim-type').value;document.querySelectorAll('.claim').forEach(c=>c.hidden=(!c.textContent.toLocaleLowerCase().includes(q)||(type&&c.dataset.type!==type)))}document.querySelector('#claim-search').addEventListener('input',filter);document.querySelector('#claim-type').addEventListener('change',filter);
</script></body></html>'''
    path = Path(project)/'exports'/'dashboard.html'
    atomic_write(path, html.encode('utf-8'))
    return path
