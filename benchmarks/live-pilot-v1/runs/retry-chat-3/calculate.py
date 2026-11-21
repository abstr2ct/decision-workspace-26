import csv,json
from pathlib import Path
p=Path(__file__).resolve().parent
rows=list(csv.DictReader((p/'materials/cohorts.csv').open(encoding='utf-8-sig')))
nums=['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']
for r in rows:
 for k in nums:r[k]=int(r[k])
m=[r for r in rows if r['matured_d30']=='true']
def agg(rs):
 s={k:sum(r[k] for r in rs) for k in nums}
 s.update(activation=s['activated']/s['eligible'],d30=s['retained_d30']/s['activated'],contribution=s['revenue_rub']-s['variable_cost_rub'])
 s['after_acquisition']=s['contribution']-s['acquisition_cost_rub']
 s['per_activated']={k:s[k]/s['activated'] for k in ['revenue_rub','variable_cost_rub','acquisition_cost_rub','contribution','after_acquisition']}
 return s
out={'scope':'Only matured rows; D30 denominator = activated; RUB, first 30 days','monthly':{c:agg([r for r in m if r['cohort']==c]) for c in ['2026-08','2026-09']},'segments':{s:agg([r for r in m if r['segment']==s]) for s in ['teams','solo']},'all_mature':agg(m),'segment_d30':{r['cohort']+' '+r['segment']:r['retained_d30']/r['activated'] for r in m},'september_standardized_august_mix':.8*(13/20)+.2*(20/80),'decomposition_pp':{'within_at_aug_mix':5,'mix_at_sep_rates':-24,'total':-19},'break_even_teams_activated':40000/290,'max_recruited_14_days':40,'full_d30_earliest_last_recruit_day':44,'illustrative_fixed_cost_bridge':{'august':22000-40000,'september':-3000-40000,'two_months':19000-80000}}
(p/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
