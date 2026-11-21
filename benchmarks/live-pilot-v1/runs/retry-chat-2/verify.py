from pathlib import Path
import json, math
p = Path(__file__).resolve().parent
file = p/'calculate.py'
s=file.read_text(encoding='utf-8-sig')
s=s.replace("(ROOT/'calculations.json').write_text", "out['capacity_scenario']={'assumption':'Constant blended teams 30-day residual; no subsequent revenue; 52 weeks / 12 months; all eligible activate','residual_per_team':290,'break_even_activated_per_month':math.ceil(40000/290),'max_eligible_average_month':20*52/12,'max_new_account_residual_average_month':20*52/12*290}\n(ROOT/'calculations.json').write_text")
file.write_text(s,encoding='utf-8')
exec(compile(s,str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
o=json.loads((p/'calculations.json').read_text(encoding='utf-8'))
assert o['mature_total']['after_acquisition']==19000
assert o['by_segment']['teams']['d30']==.61
assert len(o['excluded'])==1
assert o['test_planning']['per_arm']==356
count=len((p/'report.md').read_text(encoding='utf-8-sig').split())
assert count<=1400
(p/'verification.json').write_text(json.dumps({'report_words_whitespace':count,'checks':'passed','source_rows_mature':4,'source_rows_excluded':1},ensure_ascii=False,indent=2),encoding='utf-8')
