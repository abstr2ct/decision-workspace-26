"""Reproduce the conditional scenarios and trial size for the supplied example."""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from strategist.analytics import plan_ab

D = Decimal
TARGET = {'profit_rub':285_000_000, 'active_groups':8_000, 'connected_groups':12_000,
          'multi_number_owners':2_000, 'q4_activation_pp':60}
BASE = {'profit_rub':279_000_000, 'active_groups':5_000, 'connected_groups':8_000,
        'multi_number_owners':1_000, 'q4_activation_pp':45}


def rounded(value):
    return int(value.quantize(D('1'), rounding=ROUND_HALF_UP))


def scenario(channels, invited, year_end_retention, active_share, activation_pp,
             cohorts, paid_month_increment_pp, quarterly_costs):
    funnel = []
    for channel, shown, treatment_pp, control_pp in channels:
        starts = D(shown) * treatment_pp / 100
        extra = D(shown) * (treatment_pp-control_pp) / 100
        funnel.append({'channel':channel, 'unique_exposure_assumption':shown,
                       'created_treatment':str(starts), 'connected_treatment':str(starts*invited),
                       'activated_treatment_at_q4_rate':str(starts*activation_pp/100),
                       'extra_created_vs_control':str(extra), 'extra_connected_in_dec':str(extra*invited*year_end_retention)})
    additional_groups = rounded(sum(D(s['extra_connected_in_dec']) for s in funnel))
    active = rounded(D(BASE['connected_groups']+additional_groups)*active_share)
    quarterly = []
    cumulative = 0
    paid_months = D(0)
    for quarter, cost in enumerate(quarterly_costs, 1):
        start, end = 3*quarter-2, 3*quarter
        months_in_quarter = sum(numbers*max(0, end-max(start, entry)+1) for numbers, entry in cohorts)
        extra = D(months_in_quarter)*paid_month_increment_pp/100
        paid_months += extra
        increment = int(500*extra)-cost
        cumulative += increment
        quarterly.append({'quarter':quarter,'paid_months':str(extra),'direct_cost_rub':cost,
                          'increment_rub':increment,'cumulative_rub':cumulative})
    direct_cost = sum(quarterly_costs)
    direct_increment = cumulative
    result = dict(BASE, profit_rub=BASE['profit_rub']+direct_increment, active_groups=active,
                  connected_groups=BASE['connected_groups']+additional_groups, q4_activation_pp=activation_pp)
    return {'scenario_funnel':funnel, 'monthly_entry_cohort_size_and_month_number':cohorts, 'quarterly':quarterly,
            'paid_month_gap_assumption_pp':paid_month_increment_pp, 'incremental_paid_months':str(paid_months),
            'new_direct_cost_rub':direct_cost, 'profit_increment_before_build_rub':direct_increment,
            'annual_build_break_even_ceiling_rub':max(0,direct_increment),
            'months_needed_for_285m':(TARGET['profit_rub']-BASE['profit_rub']+direct_cost+499)//500,
            'forecast':result, 'gap_to_goal':{k:TARGET[k]-v for k,v in result.items()}}


if __name__ == '__main__':
    main = scenario([('app',10000,7,3),('support',1500,8,5),('sales',2500,4,2)],
                    D('.75'),D('.90'),D('.65'),52,
                    [(1000,7),(1000,9),(1000,10),(1000,11)],3,[0,30_000,45_000,45_000])
    weak = scenario([('app',5000,5,3),('support',750,6,5),('sales',1250,3,2)],
                    D('.60'),D('.80'),D('.625'),45,
                    [(500,7),(500,9),(500,10),(500,11)],1,[0,25_000,35_000,40_000])
    trial = plan_ab(.12,.09)
    result = {'semantics':'Synthetic conditional assumptions, not real outcomes',
              'brief_baseline':BASE,'brief_goal':TARGET,'main':main,'weak':weak,'trial':trial,
              'group_per_week_for_12_weeks':(trial['total']+11)//12}
    assert main['forecast'] == {'profit_rub':279105000,'active_groups':5417,'connected_groups':8334,
                                'multi_number_owners':1000,'q4_activation_pp':52}
    assert weak['forecast']['profit_rub'] == 278937500
    print(json.dumps(result,ensure_ascii=False,indent=2))
