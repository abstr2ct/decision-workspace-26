"""Human-readable exports, without promoting generated prose to evidence."""

import json
from pathlib import Path

from .core import atomic_write, audit, cost_summary, load, now

LABELS = {'brief': 'Бриф', 'research': 'Исследование', 'options': 'Варианты', 'strategy': 'Стратегия',
          'product': 'Продуктовая стратегия', 'communication': 'Коммуникационная стратегия', 'experiment': 'План проверки'}


def render_value(value, level=3):
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = LABELS.get(key, key.replace('_', ' '))
            if isinstance(item, (dict, list)):
                lines += ['', '#' * min(level, 6) + ' ' + label, '']
                lines.extend(render_value(item, level+1))
            else:
                lines += [f'**{label}:** {item}', '']
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(render_value(item, level))
                lines += ['', '---', '']
            else:
                lines.append(f'- {item}')
        lines.append('')
    else:
        lines.append(str(value))
    return lines


def export_report(project, draft=False):
    state = load(project)
    result = audit(project)
    if not result['ok'] and not draft:
        from .ingest import InputError
        raise InputError('Audit failed; resolve errors or explicitly use --draft. ' + '; '.join(result['errors']))
    lines = [f'# {state["name"]}', '', f'Сформировано: {now()}. Ревизия: {state["revision"]}.', '']
    if state['demo']:
        provenance = 'Есть синтетические данные.' if any(s['synthetic'] for s in state['sources'].values()) else 'Использованы открытые или собственные материалы; происхождение указано у источников.'
        lines += ['> УЧЕБНЫЙ ПРИМЕР. ' + provenance + ' Подтверждения выбора имитированы.',
                  '> Это иллюстративный кейс для задания МегаФона. Отдельный демобриф не используется.', '']
    if not result['ok']:
        lines += ['> ЧЕРНОВИК: проверка не пройдена. Нельзя использовать как актуальную рекомендацию.', '']
    for slot in ('brief', 'research', 'options', 'strategy'):
        if slot in state['documents']:
            doc = state['documents'][slot]
            lines += [f'## {LABELS[slot]}', '', f'Статус: {doc["status"]}. Контрольная сумма: `{doc["sha256"]}`.', '']
            lines.extend(render_value(doc['content']))
    lines += ['## Реестр выводов', '']
    for cid, c in state['claims'].items():
        lines += [f'### {cid} — {c["type"]} / {c["status"]}', '', c['text'], '',
                  f'Уверенность: {c["confidence"]}. {c["confidence_reason"]}', '']
        for e in c.get('evidence', []):
            src = state['sources'][e['source']]
            lines += [f'- Источник `{e["source"]}`, `{e["locator"]}`: «{e["quote"]}»; '
                      f'[снимок](../{src["blob"]}).' + (f' [Оригинал]({src["url"]}).' if src['url'] else '')]
        lines.append('')
    lines += ['## Решение и подтверждения', ''] + render_value({'decision': state['decision'], 'approvals': state['approvals']})
    lines += ['## Обязательства', ''] + render_value(list(state['commitments'].values()))
    lines += ['## Время и стоимость', ''] + render_value(cost_summary(state))
    lines += render_value(state['costs'])
    lines += ['## Проверка и ограничения', ''] + render_value(result)
    lines += ['Поиск: BM25 с расширением по двуязычному словарю и явные связи. Embeddings, автоматическая смена LLM, фоновый мониторинг, '
              'PDF/OCR и мультимодальные модели не реализованы. Записи состояния не являются независимыми источниками.', '']
    report = Path(project)/'exports'/'strategy.md'
    atomic_write(report, '\n'.join(lines).encode('utf-8'))
    atomic_write(report.parent/'audit.json', json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
    graph = ['flowchart LR']
    for sid in state['sources']:
        graph.append(f'  s_{sid}["Источник: {sid}"]')
    for cid, c in state['claims'].items():
        graph.append(f'  c_{cid}["{cid}: {c["type"]}"]')
        for e in c.get('evidence', []):
            graph.append(f'  s_{e["source"]} --> c_{cid}')
    for sid, source in state['sources'].items():
        for parent in source['parents']:
            graph.append(f'  s_{parent} --> s_{sid}')
    if state['decision']:
        graph.append('  decision["Решение"]')
        for cid in state['decision']['claims']:
            graph.append(f'  c_{cid} --> decision')
    atomic_write(report.parent/'lineage.mmd', '\n'.join(graph).encode('utf-8'))
    from .dashboard import generate
    dashboard = generate(project, state, result)
    if state.get('decision_lab'):
        if state['decision_lab']['status'] == 'active' and result['ok']:
            from .lab_report import generate as lab_generate
            lab_generate(project)
        else:
            # Never leave an old interactive recommendation linked from a new draft.
            atomic_write(Path(project)/'exports'/'decision-lab.html',
                         '<!doctype html><meta charset="utf-8"><h1>Анализ требует пересмотра</h1><p>Выполните lab show и обновите допущения.</p>'.encode('utf-8'))
    return {'report': str(report), 'dashboard': str(dashboard), 'audit': str(report.parent/'audit.json'), 'ok': result['ok']}
