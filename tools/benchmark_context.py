"""Measured engineering ablation: read-all context vs bounded, explicit task context."""

import argparse
import json
import statistics
import time
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from strategist import core, retrieval


def benchmark(project,repeats=30):
    def all_context():
        state=core.load(project)
        return {'state':state,'sources':{sid:core.read_json(core.project_file(project,s['chunks'])) for sid,s in state['sources'].items()}}
    def packet():
        return retrieval.context_packet(project,6000)
    results={}
    for name,fn in [('read_all_state_and_sources',all_context),('bounded_resume_packet',packet)]:
        elapsed=[]
        for _ in range(repeats):
            start=time.perf_counter()
            data=json.dumps(fn(),ensure_ascii=False).encode('utf-8')
            elapsed.append(time.perf_counter()-start)
        results[name]={'utf8_bytes':len(data),'median_seconds':statistics.median(elapsed),'repeats':repeats}
    results['byte_reduction_fraction']=1-results['bounded_resume_packet']['utf8_bytes']/results['read_all_state_and_sources']['utf8_bytes']
    results['interpretation']='Engineering ablation only: fewer input bytes, not proven fewer billable tokens, better strategy, or analyst time savings. Excluded source content must be read on demand.'
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--output',required=True);a=p.parse_args()
    result=benchmark(a.project)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
