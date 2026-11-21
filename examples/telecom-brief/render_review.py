"""Generate a portable readout from the replay's two computed assessments."""

import argparse
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from strategist.web_theme import styles


def pp(value):
    if value is None:
        return 'не определено'
    return f'{100*value:+.2f}'.replace('-', '−').replace('.', ',')


def span(bounds):
    low, high = map(pp, bounds)
    return low if low == high else f'{low} … {high}'


def rows(assessment):
    primary = assessment['primary']
    return (
        ('Снижение по известным исходам', pp(primary['observed_only_reduction']) + ' п.п.'),
        ('Диапазон по всем назначенным', span(primary['all_assigned_reduction_bounds']) + ' п.п.'),
        ('Внешний интервал чувствительности', span(primary['outer_score_interval']) + ' п.п.'),
        ('Неизвестно в плече сигнала', str(primary['unknown_or_immature']['treatment'])),
        ('Подтверждённые операции в срок', f"{100*assessment['operation_success_rate']:.2f}%".replace('.', ',')),
        ('Критические случаи в срезе', str(sum(assessment['critical_incidents'].values()))),
    )


def chart(first, final):
    values = [v*100 for a in (first,final) for v in a['primary']['outer_score_interval']]
    low, high = min(-4, int(min(values))-1), max(6, int(max(values))+1)

    def x(percentage_points):
        return (percentage_points-low)*100/(high-low)

    def track(result):
        a, b = [x(p*100) for p in result['primary']['outer_score_interval']]
        c, d = [x(p*100) for p in result['primary']['all_assigned_reduction_bounds']]
        return (f'<div class="track"><span class="outer" style="left:{a:.4f}%;width:{b-a:.4f}%"></span>'
                f'<span class="bound" style="left:{c:.4f}%;width:{max(.45,d-c):.4f}%"></span>'
                f'<span class="tick" style="left:{x(0):.4f}%"></span>'
                f'<span class="tick target" style="left:{x(3):.4f}%"></span></div>')

    return ('<div class="plot"><h2>Снижение ограничений интернета, п.п.</h2>'
            '<div class="legend"><span>Диапазон из-за неизвестных исходов</span><span>Внешний интервал</span></div>'
            '<div class="plotrow"><strong>Первый срез</strong>'+track(first)+'</div>'
            '<div class="plotrow"><strong>После сверки</strong>'+track(final)+'</div>'
            f'<div class="scale"><span style="left:{x(0):.4f}%">0</span>'
            f'<span style="left:{x(3):.4f}%">+3 · порог</span></div></div>')


CSS = """
*{box-sizing:border-box} body{margin:0;background:var(--page);color:var(--ink);font:16px/1.5 var(--body)}
main,header>div{width:min(1100px,calc(100% - 42px));margin:auto} header{background-color:var(--surface);color:var(--ink);padding:35px 0}
.meta{font-size:13px;color:var(--pink);font-weight:650;letter-spacing:.05em} h1{font-size:clamp(29px,4.4vw,48px);line-height:1.12;margin:10px 0 14px}
header p{max-width:810px;margin:0;color:var(--muted)} main{padding:24px 0 40px}
.links{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 24px}
a{color:var(--lilac)}
 .links a{border:1px solid var(--border);border-radius:8px;padding:8px 12px;background:var(--surface)}
.duo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.case,.plot,.next{border:1px solid var(--border);border-radius:12px;padding:20px;background:var(--surface)}
.case.revised{border-color:var(--pink);background:var(--raised)}
.case h2,.plot h2,.next h2{margin:0 0 11px;font-size:23px;line-height:1.25}
.decision{font-weight:650;min-height:48px;margin:.15em 0 .85em}
.case dl{display:grid;grid-template-columns:1fr max-content;margin:0;gap:0 12px}
dt,dd{padding:7px 0;border-top:1px solid var(--border);margin:0} dd{text-align:right;font-variant-numeric:tabular-nums;font-weight:650}
.plot,.next{margin-top:16px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.legend span:before{content:'';width:13px;height:9px;display:inline-block;margin-right:5px;background:var(--pink)}
.legend span+span:before{background:#825eae}
.plotrow{display:grid;grid-template-columns:120px 1fr;align-items:center;margin:14px 0}
.track{height:20px;background:var(--raised);position:relative;border-radius:4px}
.outer,.bound,.tick{position:absolute}
.outer{height:14px;top:3px;background:#825eae;border-radius:4px}
.bound{height:6px;top:7px;background:var(--pink);border-radius:3px}
.tick{height:22px;top:-1px;width:1px;background:var(--lilac)}
.target{background:var(--coral)}
.scale{margin-left:120px;position:relative;height:20px;font-size:12px}
.scale span{position:absolute;transform:translateX(-50%);white-space:nowrap}
.next p{margin:0;color:var(--muted)}
.next ol{padding-left:21px}
.next li{margin:.4em 0}
details{margin-top:14px}
summary{cursor:pointer;font-weight:650}
code{overflow-wrap:anywhere}
footer{margin-top:16px;font-size:13px;color:var(--muted)}
@media(max-width:720px){.duo{grid-template-columns:1fr}
 .decision{min-height:0}
.case dl{grid-template-columns:minmax(110px,1fr) auto;gap:0 6px}
.plotrow{grid-template-columns:100px 1fr;font-size:13px}
.scale{margin-left:100px}
.case,.plot,.next{padding:14px}
dd{font-size:14px}}
"""


def render(trace):
    first, final = trace['first'], trace['final']
    bounds = span(final['primary']['all_assigned_reduction_bounds'])
    unknown = final['primary']['unknown_or_immature']['treatment']

    def case(title, recommendation, data, rel, style=''):
        metrics = ''.join(f'<dt>{escape(k)}</dt><dd>{escape(v)}</dd>' for k,v in rows(data))
        return (f'<article class="case {style}"><h2>{title}</h2><p class="decision">{recommendation}</p>'
                f'<dl>{metrics}</dl><p><a href="{rel}/exports/decision-card.html">Карточка и основания</a></p></article>')

    left = case('До сверки', 'Уточнить экономику следующего охвата', first, 'q2-reported')
    right = case('После сверки', 'Восстановить исходы и сохранить охват', final, 'q2-reconciled', 'revised')
    return f'''<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'">
<title>Семейная связь · результаты пилота</title><style>{styles()}{CSS}</style>
<header><div><div class="meta">СЕМЕЙНАЯ СВЯЗЬ / РЕШЕНИЕ Q2 / УЧЕБНЫЕ ДАННЫЕ</div>
<h1>У {unknown} семей исход неизвестен.</h1>
<p>По известным исходам улучшение составляет {pp(final['primary']['observed_only_reduction'])} п.п.
По всем назначенным семьям диапазон {bounds} п.п. Решение об охвате ждёт сверки.</p></div></header>
<main><nav class="links"><a href="q1/exports/dashboard.html">Стратегия и пилот Q1</a>
<a href="q2-reconciled/exports/dashboard.html">Отчёт после сверки</a>
<a href="trace.json">Фактический журнал CLI</a></nav>
<div class="duo">{left}{right}</div>
{chart(first,final)}
<section class="next"><h2>Что предстоит владельцу</h2>
<ol><li>Аналитик и владелец расчётной системы сверяют 80 исходов.</li>
<li>Финансист подтверждает расходы и диапазон вклада на одном горизонте.</li>
<li>Владелец выбирает ограниченный следующий охват, продление или остановку.</li></ol>
<p>Условия оценки зафиксированы до импорта среза. Поступление исправления отозвало старый расчёт.
Попытка выпустить карточку по старому состоянию завершилась отказом.</p>
<details><summary>Порог, контроль и статистика</summary>
<p>1 700 семей в каждом плече. Один индексный номер на семью и семь суток от первого события.
Контроль получает обычное обслуживание. Порог снижения — 3 п.п., нижняя граница интервала должна быть выше нуля.
Розовый отрезок показывает диапазон разницы при крайних исходах пропусков. Сиреневый отрезок добавляет выборочную неопределённость.
Оценка интервала — метод Ньюкомба, номинальный уровень 95% для каждого крайнего заполнения.</p>
<p>Хеш плана: <code>{escape(trace['plan']['sha256'])}</code></p></details></section>
<footer>Учебные наблюдения. В Q1 согласование сыграно в сценарии. После Q2 проект ожидает решения владельца.</footer></main></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('demo',type=Path)
    args = parser.parse_args()
    trace = json.loads((args.demo/'trace.json').read_text(encoding='utf-8'))
    (args.demo/'review.html').write_text(render(trace),encoding='utf-8')
