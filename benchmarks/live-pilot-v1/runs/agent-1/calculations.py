"""Reproduce only synthetic case arithmetic. Run: python -X utf8 calculations.py."""
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workspace'))
from strategist.analytics import cohort_analysis, plan_ab, wilson

raw = (ROOT / 'materials/cohorts.csv').read_bytes()
rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
mature = [r for r in rows if r['matured_d30'] == 'true']
fields = ['eligible','activated','retained_d30','revenue_rub','variable_cost_rub','acquisition_cost_rub']

def group(rs):
    d = {f: sum(int(r[f]) for r in rs) for f in fields}
    d['activation'] = d['activated']/d['eligible']
    d['d30_per_activated'] = d['retained_d30']/d['activated']
    d['d30_per_eligible'] = d['retained_d30']/d['eligible']
    d['margin_before_acquisition'] = d['revenue_rub']-d['variable_cost_rub']
    d['margin_after_acquisition'] = d['margin_before_acquisition']-d['acquisition_cost_rub']
    d['margin_per_activated'] = d['margin_after_acquisition']/d['activated']
    d['cac_per_activated'] = d['acquisition_cost_rub']/d['activated']
    d['d30_wilson_95'] = wilson(d['retained_d30'],d['activated'])
    return d

monthly = {m: group([r for r in mature if r['cohort']==m]) for m in sorted({r['cohort'] for r in mature})}
segments = {s: group([r for r in mature if r['segment']==s]) for s in ('teams','solo')}
cells = {r['cohort']+'_'+r['segment']: group([r]) for r in mature}
aug, sep = monthly['2026-08'],monthly['2026-09']
standardized = sum(cells['2026-08_'+s]['activated']/aug['activated']*cells['2026-09_'+s]['d30_per_activated'] for s in segments)
ab = plan_ab(.65,.75,alpha=.05,power=.8)
ab['optimistic_enrollment_weeks_at_20_total_per_week'] = math.ceil(ab['total']/20)
ab['optimistic_full_followup_days'] = math.ceil(ab['total']/20)*7+30
ab['warning'] = 'Assumes every new eligible account activates and is teams. Real recruitment can be slower. Eligible is not activated.'
pilot = {'days':14, 'maximum_new_eligible':40, 'minimum_useful_primary_sample_total':20,
         'allocation':'1:1 account randomized; teams only; max 20 per arm over 14 days',
         'last_7day_endpoint_day_if_enrollment_to_day7':14,
         'max_eligible_enrolled_by_day7':20,
         'full_d30_followup_if_enrollment_to_day14':44,
         'example_10_of_20_wilson95':wilson(10,20),
         'note':'14 days cannot establish new D30 lift. 7-day pilot enrolls days 1-7 only; at most 10 accounts/arm.'}
budget = {'instrumentation_and_qa_rub':6000,'prototype_and_copy_rub':6000,'ux_sessions_rub':8000,'analysis_rub':6000,'reserve_rub':4000}
out = {'synthetic':True,'source':'materials/cohorts.csv physical lines 2-6; normalized row:N equals physical line N (header is row:1)',
       'formulas':{'activation':'activated/eligible','D30':'retained_d30/activated; mature only','net_contribution':'revenue-variable-acquisition; excludes fixed costs'},
       'library_analysis':cohort_analysis(raw),'monthly':monthly,'segments':segments,'cells':cells,'pooled':group(mature),
       'decomposition':{'base':'August activation weights; sequential decomposition, not causal',
          'september_d30_at_august_mix':standardized,'within_segment_effect_pp':100*(standardized-aug['d30_per_activated']),
          'mix_effect_pp':100*(sep['d30_per_activated']-standardized),'total_change_pp':100*(sep['d30_per_activated']-aug['d30_per_activated'])},
       'ab_plan':ab,'pilot':pilot,'proposed_budget_not_actual_spend':budget,'budget_total_rub':sum(budget.values()),
       'fixed_cost_context':{'monthly_rub':40000,'two_months_rub':80000,'cohort_net_sum_rub':19000,
          'illustrative_gap_rub':19000-80000,'warning':'Not observed calendar profit: first-30-day cohorts differ from monthly P&L; allocation, older revenue, exit cost unknown'},
       'delay_cost_scenario':{'14_days_fixed_at_30day_month_rub':40000*14/30,'status':'Assumption, not marginal research expenditure'},
       'missing':['LTV','later cashflows','segment allocation of fixed cost','avoidable shutdown cost','real demand','actual model/tool/human rates and token usage']}
(ROOT/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
