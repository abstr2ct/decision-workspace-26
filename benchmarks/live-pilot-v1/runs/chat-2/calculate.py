from pathlib import Path
import csv, json, math, hashlib

ROOT = Path(__file__).resolve().parent
MATERIALS = ROOT / 'materials'
rows = []
with (MATERIALS / 'cohorts.csv').open(encoding='utf-8-sig', newline='') as f:
    for line, source in enumerate(csv.DictReader(f), start=2):
        row = dict(source)
        row['source_line'] = line
        for key in ('eligible', 'activated', 'retained_d30', 'revenue_rub', 'variable_cost_rub', 'acquisition_cost_rub'):
            row[key] = int(row[key])
        row['matured_d30'] = row['matured_d30'].lower() == 'true'
        assert 0 <= row['retained_d30'] <= row['activated'] <= row['eligible']
        rows.append(row)

FIELDS = ('eligible', 'activated', 'retained_d30', 'revenue_rub', 'variable_cost_rub', 'acquisition_cost_rub')
def aggregate(group):
    values = {key: sum(r[key] for r in group) for key in FIELDS}
    values['source_lines'] = [r['source_line'] for r in group]
    values['activation_rate'] = values['activated'] / values['eligible']
    values['retention_d30_rate'] = values['retained_d30'] / values['activated']
    values['retained_per_eligible'] = values['retained_d30'] / values['eligible']
    values['contribution_before_acquisition_rub'] = values['revenue_rub'] - values['variable_cost_rub']
    values['contribution_after_acquisition_rub'] = values['contribution_before_acquisition_rub'] - values['acquisition_cost_rub']
    for name, value in (('revenue', values['revenue_rub']), ('variable_cost', values['variable_cost_rub']), ('acquisition_cost', values['acquisition_cost_rub']), ('contribution_after_acquisition', values['contribution_after_acquisition_rub'])):
        values[name + '_per_activated_rub'] = value / values['activated']
    values['contribution_after_acquisition_per_eligible_rub'] = values['contribution_after_acquisition_rub'] / values['eligible']
    return values

mature = [r for r in rows if r['matured_d30']]
by_month = {m: aggregate([r for r in mature if r['cohort'] == m]) for m in sorted({r['cohort'] for r in mature})}
by_segment = {s: aggregate([r for r in mature if r['segment'] == s]) for s in sorted({r['segment'] for r in mature})}
by_cell = {r['cohort'] + '/' + r['segment']: aggregate([r]) for r in mature}
aug, sep = by_month['2026-08'], by_month['2026-09']
segments = sorted(by_segment)
w_aug = {s: by_cell['2026-08/' + s]['activated'] / aug['activated'] for s in segments}
w_sep = {s: by_cell['2026-09/' + s]['activated'] / sep['activated'] for s in segments}
r_aug = {s: by_cell['2026-08/' + s]['retention_d30_rate'] for s in segments}
r_sep = {s: by_cell['2026-09/' + s]['retention_d30_rate'] for s in segments}
sep_standardized = sum(w_aug[s] * r_sep[s] for s in segments)
within = sum(w_aug[s] * (r_sep[s] - r_aug[s]) for s in segments)
mix = sum((w_sep[s] - w_aug[s]) * r_sep[s] for s in segments)
assert math.isclose(within + mix, sep['retention_d30_rate'] - aug['retention_d30_rate'])

# Planning approximation: independent equal-size two-proportion test,
# two-sided alpha .05, power .80. No attrition, clustering, or multiplicity.
p0, p1, z_alpha, z_beta = .60, .75, 1.959963984540054, .8416212335729143
pbar = (p0 + p1) / 2
n_exact = (z_alpha * math.sqrt(2*pbar*(1-pbar)) + z_beta * math.sqrt(p0*(1-p0) + p1*(1-p1)))**2 / (p1-p0)**2
n_arm = math.ceil(n_exact)
expected_activation = .5
eligible_weekly_cap = 20
trial_recruitment_weeks = 2*n_arm / (eligible_weekly_cap * expected_activation)
# Seven-day activation window means the last recruited accounts may activate
# seven days later; D30 is measured 30 days after activation, not enrollment.
trial_calendar_days = math.ceil(trial_recruitment_weeks * 7) + 7 + 30

unit_teams = by_segment['teams']['contribution_after_acquisition_per_activated_rub']
economics = {
    'monthly_fixed_cost_rub': 40000,
    'team_activated_break_even_at_blended_first30_contribution': math.ceil(40000/unit_teams),
    'team_eligible_break_even_at_50pct_activation': math.ceil(40000/(unit_teams*.5)),
    'four_week_intake_cap_eligible': 80,
    'four_week_intake_first30_contribution_rub': {
        'august_team_behavior': 80*by_cell['2026-08/teams']['contribution_after_acquisition_per_eligible_rub'],
        'september_team_behavior': 80*by_cell['2026-09/teams']['contribution_after_acquisition_per_eligible_rub'],
        'blended_team_behavior': 80*by_segment['teams']['contribution_after_acquisition_per_eligible_rub'],
    },
    'scope': 'Illustrative acquisition-flow coverage only; first 30 days are not LTV or calendar-month profit. Existing recurring revenue and fixed-cost attribution are unknown.',
}
budget = {'analytics_and_instrumentation':6000, 'ux_including_recruitment_and_incentives':8000, 'one_small_prototype':6000, 'message_comprehension_and_analysis':5000, 'reserve':5000}
assert sum(budget.values()) == 30000
results = {
    'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(MATERIALS.iterdir()) if p.is_file()},
    'rows': rows, 'mature_by_month': by_month, 'mature_by_segment': by_segment,
    'mature_by_cell': by_cell, 'mature_all': aggregate(mature),
    'immature_excluded': [{'source_line':r['source_line'],'cohort':r['cohort'],'reason':'D30 not mature; no final D30 estimate or economic comparison'} for r in rows if not r['matured_d30']],
    'decomposition': {'august_weights':w_aug, 'september_weights':w_sep, 'september_at_august_weights':sep_standardized, 'within_change_pp':within*100, 'mix_change_pp':mix*100, 'total_change_pp':(sep['retention_d30_rate']-aug['retention_d30_rate'])*100},
    'economics_scenarios': economics,
    'd30_power_planning': {'baseline':p0,'target':p1,'alpha_two_sided':.05,'power':.8,'sample_per_arm_unrounded':n_exact,'sample_per_arm':n_arm,'activated_total':2*n_arm,'assumed_activation':expected_activation,'eligible_per_week_total_cap':eligible_weekly_cap,'recruitment_weeks_at_cap':trial_recruitment_weeks,'activation_window_days':7,'observation_days_after_activation':30,'minimum_planning_calendar_days':trial_calendar_days,'interpretation':'Planning assumptions, not evidence of effect; exact design and actual recruitment may require more time.'},
    'fourteen_day_diagnostic': {'recruitment_days':7,'eligible_cap':20,'activation_window_days':7,'latest_activation_day':14,'latest_d30_day':44,'ux_subset_max':8,'statistical_efficacy_claim':False},
    'proposed_budget_rub':budget,
    'execution_costs': {'model_api_cost_rub':None,'human_labor_cost_rub':None,'billing_data_available':False,'note':'Unknown costs are not zero. No external actions or paid study were performed.'},
}
(ROOT/'calculations.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines = ['# Расчёты', '', 'Запуск: `python calculate.py`. Только стандартная библиотека Python; входы не изменяются.', '', 'D30 = retained_d30 / activated только при matured_d30=true; активация = activated / eligible.', 'Вклад = revenue_rub − variable_cost_rub − acquisition_cost_rub, до постоянных затрат.', '', '| Когорта / сегмент | eligible | activated | retained | Активация | D30 | Вклад, RUB |', '|---|---:|---:|---:|---:|---:|---:|']
for name, r in by_cell.items():
    lines.append(f"| {name} | {r['eligible']} | {r['activated']} | {r['retained_d30']} | {r['activation_rate']:.1%} | {r['retention_d30_rate']:.1%} | {r['contribution_after_acquisition_rub']:,} |")
for name, r in by_month.items():
    lines.append(f"| {name}, всего | {r['eligible']} | {r['activated']} | {r['retained_d30']} | {r['activation_rate']:.1%} | {r['retention_d30_rate']:.1%} | {r['contribution_after_acquisition_rub']:,} |")
lines += ['', f'Сентябрь при весах августа: {sep_standardized:.1%}. Изменение внутри сегментов: {within*100:+.1f} п.п.; изменение весов: {mix*100:+.1f} п.п.; сумма: {(within+mix)*100:+.1f} п.п.', '', f'Приближение размера выборки D30 60% → 75%: n = ceil((1.959964√(2p̄(1−p̄)) + 0.841621√(p₀(1−p₀)+p₁(1−p₁)))² / (p₁−p₀)²) = {n_arm} на группу.', f'При 20 подходящих аккаунтах/неделю суммарно и активации 50%: {trial_recruitment_weeks:.1f} недели набора + 7 суток активации + 30 суток наблюдения = около {trial_calendar_days} суток.', '', 'Экономические сценарии и все промежуточные значения: calculations.json.', 'Неизвестны: фактические тарифы труда, рекрутирования, стоимость закрытия, LTV, выручка действующей базы, стоимость ИИ-исполнения. Бюджет — предложенные лимиты, не понесённые расходы.']
(ROOT/'calculations.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'d30':{m:v['retention_d30_rate'] for m,v in by_month.items()},'n_per_arm':n_arm,'trial_days':trial_calendar_days,'break_even':economics},ensure_ascii=False,indent=2))
