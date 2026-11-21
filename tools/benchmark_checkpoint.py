"""Local CLI ablation only. No LLM, strategy-quality or billable-token claims."""
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from strategist import core
from demo.fixtures import BRIEF, CLAIMS, RESEARCH, OPTIONS


def benchmark(repeats=3):
    records=[]
    with tempfile.TemporaryDirectory(prefix='.checkpoint-benchmark-',dir=ROOT) as temporary:
        temp=Path(temporary).resolve()
        assert temp.parent==ROOT and temp.name.startswith('.checkpoint-benchmark-')
        base=temp/'base'
        core.init_project(base,'CLI measurement','Which option should be reviewed?',True)
        previous=core.load(ROOT/'examples/replay')
        remaining=dict(previous['sources'])
        while remaining:
            ready=[k for k,v in remaining.items() if set(v['parents'])<=set(core.load(base)['sources'])]
            assert ready,'Source dependency cycle'
            for sid in ready:
                src=remaining.pop(sid)
                core.source_add(base,sid,core.project_file(ROOT/'examples/replay',src['blob']).read_bytes(),Path(src['blob']).suffix,
                                src['title'],src['origin'],src['url'],src['parents'])
        core.commit_document(base,'brief',BRIEF)
        core.approve(base,'brief','SCENARIO:owner','Authored technical ablation only',simulation=True)
        inputs=temp/'authored';inputs.mkdir()
        proposal={'option_id':'focus','rationale':'Conditional team pilot for owner review','claims':['teams-retention','unit-economics']}
        bundle={'base_revision':core.load(base)['revision'],'claims':CLAIMS,'research':RESEARCH,'options':OPTIONS,'proposal':proposal}
        for name,data in [('checkpoint',bundle),('research',RESEARCH),('options',OPTIONS)]+[(c['id'],c) for c in CLAIMS]:
            core.atomic_write(inputs/f'{name}.json',core.canonical(data))
        fingerprints=[]
        for repeat in range(repeats):
            for arm in (('separate','checkpoint') if repeat%2==0 else ('checkpoint','separate')):
                project=temp/f'{arm}-{repeat}'
                shutil.copytree(base,project)
                commands=([['checkpoint',str(project),str(inputs/'checkpoint.json')]] if arm=='checkpoint' else
                          [['claim','add',str(project),str(inputs/f'{c["id"]}.json')] for c in CLAIMS]+
                          [['commit',str(project),'research',str(inputs/'research.json')],
                           ['commit',str(project),'options',str(inputs/'options.json')],
                           ['propose',str(project),'--option','focus','--rationale',proposal['rationale'],'--claims',*proposal['claims']]])
                start=time.perf_counter();output=0
                for args in commands:
                    p=subprocess.run([sys.executable,'-X','utf8','-m','strategist',*args],cwd=ROOT,capture_output=True,encoding='utf-8')
                    assert p.returncode==0,p.stderr
                    output+=len(p.stdout.encode('utf-8'))
                elapsed=time.perf_counter()-start
                state=core.load(project)
                fingerprints.append({'claims':{k:v['payload_hash'] for k,v in state['claims'].items()},
                                     'documents':{k:v['sha256'] for k,v in state['documents'].items()},
                                     'decision':state['decision']['sha256'],'approved':core.approved(state,'decision')})
                records.append({'repeat':repeat+1,'arm':arm,'seconds':elapsed,'cli_calls':len(commands),'stdout_utf8_bytes':output})
        assert all(f==fingerprints[0] for f in fingerprints) and not fingerprints[0]['approved']
    summary={arm:{'cli_calls':next(r['cli_calls'] for r in records if r['arm']==arm),
                  'median_seconds':statistics.median(r['seconds'] for r in records if r['arm']==arm),
                  'median_stdout_utf8_bytes':statistics.median(r['stdout_utf8_bytes'] for r in records if r['arm']==arm)} for arm in ('separate','checkpoint')}
    return {'kind':'technical_CLI_ablation_not_LLM_benchmark','repeats_per_arm':repeats,'records':records,'summary':summary,
            'identical_business_payloads':True,'human_decision_not_approved':True,
            'stdout_reduction_fraction':1-summary['checkpoint']['median_stdout_utf8_bytes']/summary['separate']['median_stdout_utf8_bytes'],
            'limits':['CLI wall time only; excludes LLM reasoning, preparation and human review',
                      'Input/output bytes are not billed tokens or quality metrics',
                      'Staging copies source blobs; large projects may cost more disk time',
                      'Atomicity concerns state; unreferenced immutable blobs may remain after disk failure']}


if __name__=='__main__':
    value=benchmark()
    core.atomic_write(ROOT/'docs/checkpoint-benchmark.json',json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8'))
    print(json.dumps(value['summary'],ensure_ascii=False,indent=2))
