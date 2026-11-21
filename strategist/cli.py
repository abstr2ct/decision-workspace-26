"""Small tools for an IDE-hosted LLM agent, not an autonomous LLM runtime."""

import argparse
import json
import sys
from pathlib import Path
from xml.etree.ElementTree import ParseError

from . import analytics, core, ingest, report, retrieval, decision_lab


def parser():
    p = argparse.ArgumentParser(prog='python -m strategist', description='Evidence-led product strategy workspace')
    commands = p.add_subparsers(dest='cmd', required=True)
    init = commands.add_parser('init', help='Create a project; no API key required')
    init.add_argument('project')
    init.add_argument('--name', required=True)
    init.add_argument('--question', required=True)
    init.add_argument('--demo', action='store_true')
    for name in ('resume', 'audit', 'continue'):
        c = commands.add_parser(name)
        c.add_argument('project')
    pause = commands.add_parser('pause')
    pause.add_argument('project')
    pause.add_argument('--reason', required=True)
    source = commands.add_parser('source')
    sc = source.add_subparsers(dest='action', required=True)
    add = sc.add_parser('add')
    add.add_argument('project')
    add.add_argument('file')
    add.add_argument('--id', required=True)
    add.add_argument('--title', required=True)
    add.add_argument('--origin', choices=('own', 'public', 'synthetic'), default='own')
    add.add_argument('--url')
    show = sc.add_parser('show')
    show.add_argument('project')
    show.add_argument('id')
    for action in ('supersede', 'withdraw'):
        s = sc.add_parser(action)
        s.add_argument('project')
        s.add_argument('id')
        if action == 'supersede':
            s.add_argument('--with', dest='replacement', required=True)
        s.add_argument('--reason', required=True)
    web = commands.add_parser('web')
    wc = web.add_subparsers(dest='action', required=True)
    allow = wc.add_parser('allow-host')
    allow.add_argument('project')
    allow.add_argument('host')
    fetch = wc.add_parser('fetch')
    fetch.add_argument('project')
    fetch.add_argument('url')
    fetch.add_argument('--id', required=True)
    fetch.add_argument('--title', required=True)
    claim = commands.add_parser('claim')
    cc = claim.add_subparsers(dest='action', required=True)
    ca = cc.add_parser('add')
    ca.add_argument('project')
    ca.add_argument('file')
    cr = cc.add_parser('retract')
    cr.add_argument('project')
    cr.add_argument('id')
    cr.add_argument('--reason', required=True)
    document = commands.add_parser('commit')
    document.add_argument('project')
    document.add_argument('slot', choices=core.SLOTS)
    document.add_argument('file')
    decision = commands.add_parser('propose')
    decision.add_argument('project')
    decision.add_argument('--option', required=True)
    decision.add_argument('--rationale', required=True)
    decision.add_argument('--claims', nargs='+', required=True)
    approve = commands.add_parser('approve')
    approve.add_argument('project')
    approve.add_argument('gate', choices=('brief', 'decision'))
    approve.add_argument('--by', dest='actor', required=True)
    approve.add_argument('--reason', required=True)
    approve.add_argument('--simulation', action='store_true')
    search = commands.add_parser('search')
    search.add_argument('project')
    search.add_argument('query')
    analyze = commands.add_parser('analyze-cohorts')
    analyze.add_argument('project')
    analyze.add_argument('--source', required=True)
    analyze.add_argument('--id', required=True)
    analyze.add_argument('--compare', nargs=2, metavar=('BASELINE', 'CURRENT'), help='Compare two mature cohort IDs and separate within-segment from mix changes')
    cost = commands.add_parser('cost')
    cost.add_argument('project')
    cost.add_argument('--category', choices=('model', 'search', 'tool', 'human'), required=True)
    cost.add_argument('--amount', required=True)
    cost.add_argument('--currency', choices=('RUB', 'USD', 'EUR'), required=True)
    cost.add_argument('--seconds', default='0')
    cost.add_argument('--basis', required=True)
    cost.add_argument('--estimated', action='store_true')
    commitment = commands.add_parser('commitment')
    cm = commitment.add_subparsers(dest='action', required=True)
    cmadd = cm.add_parser('add')
    cmadd.add_argument('project')
    cmadd.add_argument('file')
    cmclose = cm.add_parser('close')
    cmclose.add_argument('project')
    cmclose.add_argument('id')
    cmclose.add_argument('--evidence', required=True, help='Active claim ID demonstrating completion')
    cmcarry = cm.add_parser('carry-forward')
    cmcarry.add_argument('project')
    cmcarry.add_argument('id')
    cmcarry.add_argument('--reason', required=True)
    export = commands.add_parser('export')
    export.add_argument('project')
    export.add_argument('--draft', action='store_true')
    route = commands.add_parser('route')
    route.add_argument('--task', choices=('extract', 'calculate', 'synthesize', 'challenge', 'revise'), required=True)
    route.add_argument('--risk', choices=('low', 'high'), default='low')
    ab = commands.add_parser('plan-ab')
    ab.add_argument('--baseline', type=float, required=True)
    ab.add_argument('--target', type=float, required=True)
    ab.add_argument('--alpha', type=float, default=.05)
    ab.add_argument('--power', type=float, default=.8)
    pilot = commands.add_parser('pilot', help='Freeze a two-arm plan and evaluate an aggregate readout')
    pc = pilot.add_subparsers(dest='action', required=True)
    freeze = pc.add_parser('plan', help='Validate and freeze thresholds before importing results')
    freeze.add_argument('project')
    freeze.add_argument('file')
    freeze.add_argument('--id', required=True)
    freeze.add_argument('--origin', choices=('own', 'synthetic'), default='own')
    assess = pc.add_parser('evaluate', help='Check sample, missing outcomes, guardrails and economics')
    assess.add_argument('project')
    assess.add_argument('--plan', required=True)
    assess.add_argument('--results', required=True)
    assess.add_argument('--id', required=True)
    ctx = commands.add_parser('context', help='Bounded resume packet without loading the entire task')
    ctx.add_argument('project')
    ctx.add_argument('--max-chars', type=int, default=6000)
    find = commands.add_parser('retrieve', help='BM25 with bilingual concept expansion and claim links')
    find.add_argument('project')
    find.add_argument('query')
    find.add_argument('--limit', type=int, default=10)
    impact = commands.add_parser('impact', help='Preview the consequences of a source correction')
    impact.add_argument('project')
    impact.add_argument('source_id')
    checkpoint = commands.add_parser('checkpoint', help='Save prepared claims, research, options and proposal in one atomic checkpoint; no approvals')
    checkpoint.add_argument('project')
    checkpoint.add_argument('file')
    card = commands.add_parser('decision-card', help='Create a compact owner decision snapshot with objections and evidence')
    card.add_argument('project')
    lab = commands.add_parser('lab', help='Stress-test a decision under explicitly authored scenarios')
    lc = lab.add_subparsers(dest='action', required=True)
    analyze = lc.add_parser('analyze', help='Read-only calculation; no project approval or saved state')
    analyze.add_argument('file')
    commit = lc.add_parser('commit', help='Bind assumptions to the current evidence and options')
    commit.add_argument('project')
    commit.add_argument('file')
    show = lc.add_parser('show', help='Verify saved calculation and evidence dependencies')
    show.add_argument('project')
    page = lc.add_parser('export', help='Export an interactive offline scenario report')
    page.add_argument('project')
    return p


def run(a):
    if a.cmd == 'pilot':
        from . import pilot
        if a.action == 'plan':
            require_readable_size(Path(a.file))
            return pilot.save_plan(a.project, a.id, core.read_json(a.file), a.origin)
        return pilot.save_assessment(a.project, a.plan, a.results, a.id)
    if a.cmd == 'checkpoint':
        from .checkpoint import save
        require_readable_size(Path(a.file))
        return save(a.project, core.read_json(a.file))
    if a.cmd == 'decision-card':
        from .decision_card import generate
        return generate(a.project)
    if a.cmd == 'lab':
        if a.action == 'analyze':
            require_readable_size(Path(a.file))
            return decision_lab.analyze(core.read_json(a.file))
        if a.action == 'commit':
            require_readable_size(Path(a.file))
            return decision_lab.commit(a.project, core.read_json(a.file))
        if a.action == 'show':
            return decision_lab.show(a.project)
        from .lab_report import generate
        return {'report': str(generate(a.project))}
    if a.cmd == 'context':
        return retrieval.context_packet(a.project, a.max_chars)
    if a.cmd == 'retrieve':
        return retrieval.retrieve(a.project, a.query, a.limit)
    if a.cmd == 'impact':
        return retrieval.impact(a.project, a.source_id)
    if a.cmd == 'plan-ab':
        return analytics.plan_ab(a.baseline, a.target, a.alpha, a.power)
    if a.cmd == 'init':
        core.init_project(a.project, a.name, a.question, a.demo)
        return core.resume(a.project)
    if a.cmd == 'resume':
        return core.resume(a.project)
    if a.cmd == 'audit':
        return core.audit(a.project)
    if a.cmd in ('pause', 'continue'):
        with core.transaction(a.project, allow_paused=True) as s:
            s['paused'] = a.cmd == 'pause'
            s['pause_reason'] = a.reason if s['paused'] else ''
            core.event(s, a.cmd, {'reason': s['pause_reason']})
        return core.resume(a.project)
    if a.cmd == 'source':
        if a.action == 'add':
            path = Path(a.file)
            require_readable_size(path)
            core.require(path.resolve() != (Path(a.project)/'state.json').resolve() and not path.resolve().is_relative_to((Path(a.project)/'exports').resolve()),
                         'Project state and generated exports cannot be imported as independent evidence')
            return core.source_add(a.project, a.id, path.read_bytes(), path.suffix, a.title, a.origin, a.url)
        if a.action == 'show':
            s = core.load(a.project)
            core.require(a.id in s['sources'], 'Unknown source')
            source = s['sources'][a.id]
            return {'source': source, 'untrusted_content': core.read_json(core.project_file(a.project, source['chunks']))}
        return core.source_status(a.project, a.id, getattr(a, 'replacement', None), a.reason)
    if a.cmd == 'web':
        if a.action == 'allow-host':
            host = a.host.lower().rstrip('.')
            core.require(bool(ingest.re.fullmatch(r'[a-z0-9.-]+', host)) and '.' in host, 'Provide a host only, without path or scheme')
            with core.transaction(a.project) as s:
                if host not in s['allowed_hosts']:
                    s['allowed_hosts'].append(host)
                    core.event(s, 'host_allowed', {'host': host})
            return {'allowed_host': host}
        s = core.load(a.project)
        core.require(not s['paused'], 'Project paused; network access stopped')
        core.check_id(a.id)
        core.require(a.id not in s['sources'], 'Fetch ID already exists. Use source show; retries must not silently refetch.')
        data, suffix, final = ingest.fetch(a.url, s['allowed_hosts'])
        return core.source_add(a.project, a.id, data, suffix, a.title, 'public', final)
    if a.cmd == 'claim':
        if a.action == 'add':
            return core.claim_add(a.project, core.read_json(a.file))
        with core.transaction(a.project) as s:
            core.require(a.id in s['claims'], 'Unknown claim')
            s['claims'][a.id]['status'] = 'retracted'
            core.invalidate(s, ('research', 'options', 'strategy'), a.reason)
            core.event(s, 'claim_retracted', {'id': a.id, 'reason': a.reason})
        return {'retracted': a.id}
    if a.cmd == 'commit':
        return core.commit_document(a.project, a.slot, core.read_json(a.file))
    if a.cmd == 'propose':
        return core.propose(a.project, a.option, a.rationale, a.claims)
    if a.cmd == 'approve':
        return core.approve(a.project, a.gate, a.actor, a.reason, a.simulation)
    if a.cmd == 'search':
        return core.search(a.project, a.query)
    if a.cmd == 'analyze-cohorts':
        s = core.load(a.project)
        core.require(a.source in s['sources'] and s['sources'][a.source]['status'] == 'active', 'Active source required')
        src = s['sources'][a.source]
        core.require(Path(src['blob']).suffix == '.csv', 'Cohort tool expects comma-separated UTF-8 CSV')
        raw = core.project_file(a.project, src['blob']).read_bytes()
        data = analytics.compare_cohorts(raw, *a.compare) if a.compare else analytics.cohort_analysis(raw)
        return core.source_add(a.project, a.id, core.canonical(data), '.json', 'Reproducible cohort analysis', 'derived', parents=[a.source])
    if a.cmd == 'cost':
        return core.cost_add(a.project, a.category, a.amount, a.currency, a.seconds, a.basis, a.estimated)
    if a.cmd == 'commitment':
        if a.action == 'add':
            return core.commitment_add(a.project, core.read_json(a.file))
        if a.action == 'carry-forward':
            with core.transaction(a.project) as s:
                core.require(core.approved(s,'decision'), 'Current approved decision required')
                core.require(a.id in s['commitments'] and s['commitments'][a.id]['status']=='open','Open commitment required')
                core.require(bool(a.reason.strip()),'Explain why the obligation remains relevant')
                old=s['commitments'][a.id]['decision_hash']
                s['commitments'][a.id]['decision_hash']=s['decision']['sha256']
                core.event(s,'commitment_carried_forward',{'id':a.id,'previous_decision_hash':old,'decision_hash':s['decision']['sha256'],'reason':a.reason})
            return {'carried_forward':a.id,'decision_hash':s['decision']['sha256']}
        with core.transaction(a.project) as s:
            core.require(a.id in s['commitments'], 'Unknown commitment')
            core.referenced_claims(s, [a.evidence], 1)
            core.require(s['claims'][a.evidence]['type'] in ('fact', 'demo_fact'), 'Completion requires observed evidence')
            s['commitments'][a.id].update(status='closed', completion_evidence=a.evidence, closed_at=core.now())
            core.event(s, 'commitment_closed', {'id': a.id, 'evidence': a.evidence})
        return {'closed': a.id}
    if a.cmd == 'export':
        return report.export_report(a.project, a.draft)
    if a.cmd == 'route':
        # This selects the procedure, not an API model. The host controls model availability.
        rules = {
            'extract': ('source show / search / ingest', 'host default', 'Exact anchors; escalate unreadable content to an explicit conversion step'),
            'calculate': ('analyze-cohorts', 'no LLM for arithmetic', 'Stop on unit, denominator or maturity errors'),
            'synthesize': ('knowledge/strategy.md', 'host default; stronger available model for high-stakes synthesis', 'Cite claims; do not invent missing market evidence'),
            'challenge': ('.agents/skills/strategy-review/SKILL.md', 'host default in a separate review pass', 'Test strongest opposing interpretation; no claim of independent agents'),
            'revise': ('.agents/skills/decision-revision/SKILL.md', 'host default', 'Invalidate affected evidence, inspect lineage, reopen the human gate'),
        }
        process, model, fallback = rules[a.task]
        return {'task': a.task, 'risk': a.risk, 'process': process, 'model_policy': model, 'fallback': fallback,
                'model_switched': False, 'note': 'Advisory routing only. No model API is invoked by this CLI.'}
    raise ingest.InputError('Unsupported command')


def require_readable_size(path):
    core.require(path.is_file() and path.stat().st_size <= ingest.MAX_BYTES, 'Source must be a file up to 8 MiB')


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        value = run(a)
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
        if a.cmd == 'audit' and not value['ok']:
            return 2
        return 0
    except (ingest.InputError, OSError, ValueError, KeyError, TypeError, ParseError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'command': a.cmd,
                          'recovery': 'Inspect resume. No automatic retry, approval or external action was performed.'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
