from pathlib import Path
import csv,json,math
p=Path(__file__).resolve().parent
rows=list(csv.DictReader((p/'materials/cohorts.csv').open(encoding='utf-8-sig')))
for r in rows:
 for k in ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']: r[k]=int(r[k])
m=[r for r in rows if r['matured_d30']=='true']
def summary(rs):
 d={k:sum(r[k] for r in rs) for k in ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']}
 d.update(activation=d['activated']/d['eligible'],d30=d['retained_d30']/d['activated'],contribution_before_acquisition=d['revenue_rub']-d['variable_cost_rub'],contribution_after_acquisition=d['revenue_rub']-d['variable_cost_rub']-d['acquisition_cost_rub'])
 for name,num in [('cac',d['acquisition_cost_rub']),('revenue_per_activated',d['revenue_rub']),('contribution_after_acquisition_per_activated',d['contribution_after_acquisition'])]: d[name]=num/d['activated']
 d['contribution_after_acquisition_per_eligible']=d['contribution_after_acquisition']/d['eligible']
 return d
out={'matured_total':summary(m),'cohorts':{c:summary([r for r in m if r['cohort']==c]) for c in ['2026-08','2026-09']},'segments':{s:summary([r for r in m if r['segment']==s]) for s in ['teams','solo']},'rows':[{**r,**summary([r])} for r in m]}
aug=out['cohorts']['2026-08']['d30']; sep=out['cohorts']['2026-09']['d30']; standardized=.8*.65+.2*.25
out['decomposition']={'august':aug,'september':sep,'september_at_august_mix':standardized,'within_segment_effect_pp':100*(standardized-aug),'mix_effect_pp':100*(sep-standardized),'total_pp':100*(sep-aug)}
out['economics_sensitivity']={'teams_break_even_activated_per_month':math.ceil(40000/290),'mixed_break_even_activated_per_month':math.ceil(40000/95),'teams_break_even_eligible_per_month':math.ceil(40000/145),'max_eligible_month_52_over_12':20*52/12,'teams_contribution_at_cap_and_50pct_activation':20*52/12*.5*290,'warning':'Illustrative new-account contribution only; not revenue forecast, profit, or LTV.'}
def sample(p1,p2):
 mean=(p1+p2)/2
 n=math.ceil(((1.959964*math.sqrt(2*mean*(1-mean))+.841621*math.sqrt(p1*(1-p1)+p2*(1-p2))))**2/(p2-p1)**2)
 return {'baseline':p1,'target':p2,'per_arm_activated':n,'total_activated':n*2,'best_case_weeks_including_30d':2*n/20+30/7,'weeks_at_50pct_activation_including_30d':2*n/10+30/7}
out['sample_size_approximation']={'assumptions':'Two independent equal arms; two-sided alpha .05, power .80; normal approximation, no attrition or multiple testing correction. Enrollment rate cap applies to eligible accounts.','five_pp':sample(.60,.65),'ten_pp':sample(.60,.70)}
(p/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['cohort,segment,activation,d30,contribution_before_acquisition,contribution_after_acquisition,cac']
for r in out['rows']: lines.append(','.join(str(r[k]) for k in ['cohort','segment','activation','d30','contribution_before_acquisition','contribution_after_acquisition','cac']))
(p/'calculations.csv').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
