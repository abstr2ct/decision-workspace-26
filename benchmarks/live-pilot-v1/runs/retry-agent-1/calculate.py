from pathlib import Path
import csv,json,sys,math
from statistics import NormalDist
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'workspace'))
from strategist.analytics import cohort_analysis,plan_ab,wilson
rows=list(csv.DictReader((R/'materials/cohorts.csv').read_text(encoding='utf-8-sig').splitlines()))
result=cohort_analysis((R/'materials/cohorts.csv').read_bytes())
result['months']={}
for month in ('2026-08','2026-09'):
 rr=[r for r in rows if r['cohort']==month]
 totals={k:sum(float(r[k]) for r in rr) for k in ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']}
 totals['activation']=totals['activated']/totals['eligible']
 totals['d30']=totals['retained_d30']/totals['activated']
 totals['d30_eligible']=totals['retained_d30']/totals['eligible']
 totals['d30_wilson']=wilson(totals['retained_d30'],totals['activated'])
 totals['contribution_after_acquisition']=totals['revenue_rub']-totals['variable_cost_rub']-totals['acquisition_cost_rub']
 result['months'][month]=totals
result['row_metrics']=[]
for i,r in enumerate(rows,2):
 if r['matured_d30']!='true':continue
 e,a,d=[int(r[k]) for k in ['eligible','activated','retained_d30']]
 result['row_metrics'].append({'row':i,'activation':a/e,'d30':d/a,'d30_eligible':d/e,'wilson':wilson(d,a)})
result['mix_decomposition']={'august':.8*.6+.2*.2,'september_at_august_mix':.8*.65+.2*.25,'september':.2*.65+.8*.25,'within_rate_effect_pp':5,'mix_effect_pp':-24,'total_pp':-19}
result['ab']=plan_ab(.61,.71)
result['ab']['minimum_recruitment_weeks']=math.ceil(result['ab']['total']/20)
result['ab']['minimum_calendar_days']=result['ab']['minimum_recruitment_weeks']*7+30
result['ab']['note']='20 eligible accounts/week maximum across segments: activated teams accrual is lower; optimistic calendar bound only. No D30 at day 14.'
result['economics']={'teams_contribution_per_activated':290,'solo_contribution_per_activated':-100,'teams_steady_state_accounts_to_cover_40000':math.ceil(40000/290),'two_month_first_window_contribution':19000,'illustrative_two_month_fixed_cost':80000,'illustrative_difference':-61000,'warning':'Not accounting profit: cohort windows differ from calendar fixed-cost months; repeat revenues, allocation, exit costs and realization unknown.'}
(R/'calculations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
