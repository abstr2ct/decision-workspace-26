from pathlib import Path
import json,subprocess,sys,shutil
R=Path(__file__).resolve().parent;W=R/'workspace';P=R/'project';A=R/'authored'
log=json.loads((R/'workflow-log.json').read_text(encoding='utf-8'))
def cli(*args,allowed=(0,)):
 p=subprocess.run([sys.executable,'-X','utf8','-m','strategist',*map(str,args)],cwd=W,capture_output=True,encoding='utf-8');log.append({'args':list(map(str,args)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(R/'workflow-log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
 if p.returncode not in allowed: raise RuntimeError(p.stdout+p.stderr)
 return p
source=json.loads(cli('source','show',P,'cohort-metrics').stdout)
quote=source['untrusted_content'][0]['text']
claim={'id':'cohort-summary','type':'demo_fact','text':'Зрелые команды 61/100 D30 и вклад 29000 RUB; solo 24/100 и -10000 RUB.','evidence':[{'source':'cohort-metrics','locator':'line:1','quote':quote}],'confidence':'high','confidence_reason':'Производный расчёт из синтетического CSV; не причинность и не реальный рынок.'}
p=A/'cohort-summary.json';p.write_text(json.dumps(claim,ensure_ascii=False,indent=2),encoding='utf-8');cli('claim','add',P,p)
p=A/'research.json';d=json.loads(p.read_text(encoding='utf-8'));d['findings'][0]['claims']=['cohort-summary'];p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');cli('commit',P,'research',p)
p=A/'options.json';d=json.loads(p.read_text(encoding='utf-8'))
for o in d['options']: o['claims'].append('cohort-summary')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');cli('commit',P,'options',p)
cli('propose',P,'--option','focus','--rationale','Условная диагностика до 30000 RUB и решения на дне 14. Только рекомендация, бизнес-решение не одобрено. Подробная стратегия в report.md.','--claims','cohort-summary','capability','roadmap','fixed','ux')
audit=cli('audit',P,allowed=(0,1,2));(R/'audit.json').write_text(audit.stdout,encoding='utf-8')
cli('export',P,'--draft')
resume=cli('resume',P);(R/'resume.json').write_text(resume.stdout,encoding='utf-8')
context=cli('context',P,'--max-chars','6000');(R/'context.json').write_text(context.stdout,encoding='utf-8')
print(audit.stdout)
shutil.copytree(P,R/'checkpoint',dirs_exist_ok=True)
print('Checkpoint copied; decision proposed, no business approval.')
