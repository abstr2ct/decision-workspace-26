import csv, json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT/'materials/cohorts.csv').open(encoding='utf-8-sig')))
nums = ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']
for row in rows:
    for k in nums: row[k] = int(row[k])
mature = [r for r in rows if r['matured_d30']=='true']
def summary(rs):
    s={k:sum(r[k] for r in rs) for k in nums}
    s.update(activation=s['activated']/s['eligible'], d30=s['retained_d30']/s['activated'], contribution=s['revenue_rub']-s['variable_cost_rub'])
    s.update(after_acquisition=s['contribution']-s['acquisition_cost_rub'], cac_per_activated=s['acquisition_cost_rub']/s['activated'], contribution_per_activated=s['contribution']/s['activated'])
    return s
out={'definitions':{'d30':'retained_d30 / activated; matured only','activation':'activated / eligible','contribution':'revenue - variable_cost; first 30 days','cac':'acquisition_cost / activated; accounting proxy, not causal CAC'},'by_cohort':{},'by_segment':{},'excluded': [r for r in rows if r['matured_d30']!='true']}
for cohort in sorted(set(r['cohort'] for r in mature)):
    out['by_cohort'][cohort]=summary([r for r in mature if r['cohort']==cohort])
for seg in ['teams','solo']:
    out['by_segment'][seg]=summary([r for r in mature if r['segment']==seg])
out['mature_total']=summary(mature)
out['segment_cohorts']=[dict(cohort=r['cohort'],segment=r['segment'],**summary([r])) for r in mature]
aug={r['segment']:r for r in mature if r['cohort']=='2026-08'}
sep={r['segment']:r for r in mature if r['cohort']=='2026-09'}
w={s:aug[s]['activated']/100 for s in aug}
std_sep=sum(w[s]*sep[s]['retained_d30']/sep[s]['activated'] for s in w)
out['mix']={'aug_weights':w,'sep_standardized_to_aug':std_sep,'within_effect_pp':(std_sep-.52)*100,'mix_effect_pp':(.33-std_sep)*100,'total_change_pp':-19}
out['fixed_cost_scenario']={'assumption':'Only listed mature cohorts recognized across two months; not complete company P&L. Cohort windows and calendar costs may differ.','fixed_two_months':80000,'residual':out['mature_total']['after_acquisition']-80000}
p1,p2=.6,.7
pb=(p1+p2)/2
n=math.ceil(((1.95996398454*math.sqrt(2*pb*(1-pb))+.84162123357*math.sqrt(p1*(1-p1)+p2*(1-p2))))**2/(p2-p1)**2)
out['test_planning']={'assumption':'Two-sided alpha .05, power .8, independent equal groups, normal approximation, 60% to 70%; illustrative only','per_arm':n,'total':n*2,'min_recruitment_weeks_at_20':n*2/20,'min_elapsed_days_including_d30':n*2/20*7+30,'max_14_day_recruits':40,'last_day14_activation_matures_day':44}
out['capacity_scenario']={'assumption':'Constant blended teams 30-day residual; no subsequent revenue; 52 weeks / 12 months; all eligible activate','residual_per_team':290,'break_even_activated_per_month':math.ceil(40000/290),'max_eligible_average_month':20*52/12,'max_new_account_residual_average_month':20*52/12*290}
(ROOT/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'metrics.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(out['segment_cohorts'][0]))
    writer.writeheader(); writer.writerows(out['segment_cohorts'])
print(json.dumps(out,ensure_ascii=False,indent=2))
