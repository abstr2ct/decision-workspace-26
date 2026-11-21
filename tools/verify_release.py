"""Reproducible local release checks, with measured results rather than badges."""
import json
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from strategist import __version__


def main():
    started = time.perf_counter()
    checks = []

    def run(args, label):
        start = time.perf_counter()
        p = subprocess.run([sys.executable, '-X', 'utf8', *args], cwd=ROOT, capture_output=True, encoding='utf-8')
        checks.append({'check': label, 'exit_code': p.returncode, 'seconds': time.perf_counter()-start,
                       'stdout': p.stdout, 'stderr': p.stderr})
        if p.returncode:
            raise RuntimeError(label + ': ' + p.stderr + p.stdout)
        return p

    tests = run(['-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'unit_and_integration_tests')
    test_count = int(re.search(r'Ran (\d+) tests', tests.stderr).group(1))
    for name in ('replay', 'revision', 'public-case', 'decision-lab'):
        run(['-m', 'strategist', 'audit', 'examples/'+name], 'audit_'+name)
    with tempfile.TemporaryDirectory(prefix='strategist-v03-') as temporary:
        p = Path(temporary)/'fresh'
        run(['demo/lab.py', str(p)], 'fresh_lab_replay')
        run(['-m', 'strategist', 'pause', str(p), '--reason', 'Release check: new process and relocation'], 'pause')
        resume = json.loads(run(['-m', 'strategist', 'resume', str(p)], 'resume_in_new_process').stdout)
        assert resume['paused'] and resume['decision_lab']['status'] == 'active'
        moved = Path(temporary)/'another-IDE'
        shutil.copytree(p, moved)
        run(['-m', 'strategist', 'continue', str(moved)], 'continue_relocated_project')
        result = json.loads(run(['-m', 'strategist', 'lab', 'show', str(moved)], 'verify_relocated_lab').stdout)
        assert result['verification']['candidates'] == ['focus']
        run(['-m', 'strategist', 'export', str(moved)], 'export_relocated_project')
    report = {'version': __version__, 'python': platform.python_version(), 'platform': platform.platform(),
              'test_count': test_count, 'elapsed_seconds': time.perf_counter()-started, 'checks': checks,
              'limits': 'Technical checks and authored replays; no independent live LLM evaluation, real customer validation or complete cost comparison.'}
    version_label = '.'.join(__version__.split('.')[:2])
    (ROOT/'docs'/f'verification-v{version_label}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'test_count': test_count, 'checks': len(checks), 'elapsed_seconds': report['elapsed_seconds'], 'ok': True}))


if __name__ == '__main__':
    main()
