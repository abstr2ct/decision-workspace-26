from pathlib import Path
import csv,json,math
from statistics import NormalDist
ROOT=Path(__file__).resolve().parent
rows=list(csv.DictReader((ROOT/'materials/cohorts.csv').open(encoding='utf-8-sig')))
for r in rows:
 for k in ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']:r[k]=int(r[k])
def summarize(rs):
 t={k:sum(r[k] for r in rs) for k in ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']}
 t.update(activation=t['activated']/t['eligible'],d30=t['retained_d30']/t['activated'],contribution_before_acquisition=t['revenue_rub']-t['variable_cost_rub'],contribution_after_acquisition=t['revenue_rub']-t['variable_cost_rub']-t['acquisition_cost_rub'])
 t['contribution_after_acquisition_per_activated']=t['contribution_after_acquisition']/t['activated']
 n=t['activated'];p=t['d30'];z=NormalDist().inv_cdf(.975);a=(p+z*z/(2*n))/(1+z*z/n);b=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n);t['d30_wilson95']=[a-b,a+b]
 return t
m=[r for r in rows if r['matured_d30']=='true']
out={'mature_by_month':{month:summarize([r for r in m if r['cohort']==month]) for month in ['2026-08','2026-09']},'mature_by_segment':{s:summarize([r for r in m if r['segment']==s]) for s in ['teams','solo']},'rows':[dict(r,activation=r['activated']/r['eligible'],d30=r['retained_d30']/r['activated'] if r['matured_d30']=='true' else None,contribution_after_acquisition=r['revenue_rub']-r['variable_cost_rub']-r['acquisition_cost_rub']) for r in rows]}
out['standardized_september_at_august_mix']=.8*(13/20)+.2*(20/80)
out['decomposition_pp']={'within_at_august_mix':100*(out['standardized_september_at_august_mix']-.52),'mix_at_september_rates':100*(.33-out['standardized_september_at_august_mix'])}
p1,p2=.6,.7;p=(p1+p2)/2;z=NormalDist().inv_cdf(.975);zb=NormalDist().inv_cdf(.8)
n=math.ceil((z*math.sqrt(2*p*(1-p))+zb*math.sqrt(p1*(1-p1)+p2*(1-p2)))**2/(p2-p1)**2)
out['ab']={'baseline':p1,'target':p2,'alpha_two_sided':.05,'power':.8,'per_arm':n,'total':2*n,'best_case_recruitment_days':math.ceil(2*n/20*7),'plus_d30_days':math.ceil(2*n/20*7)+30,'assumption':'All eligible accounts activate; otherwise longer'}
out['teams_only_monthly_break_even_activated_at_observed_contribution']=math.ceil(40000/out['mature_by_segment']['teams']['contribution_after_acquisition_per_activated'])
(ROOT/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
