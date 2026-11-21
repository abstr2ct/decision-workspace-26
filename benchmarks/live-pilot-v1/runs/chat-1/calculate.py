"""Reproduce this run using Python 3 standard library only. No network or writes to inputs."""
from pathlib import Path
from statistics import NormalDist
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / "materials/cohorts.csv").open(encoding="utf-8-sig", newline="")))
numeric = ("eligible", "activated", "retained_d30", "revenue_rub", "variable_cost_rub", "acquisition_cost_rub")
for line, row in enumerate(rows, 2):
    row["source_line"] = line
    for key in numeric:
        row[key] = int(row[key])
    row["matured_d30"] = row["matured_d30"].lower() == "true"
    assert 0 <= row["retained_d30"] <= row["activated"] <= row["eligible"]

mature = [row for row in rows if row["matured_d30"]]

def aggregate(selected):
    result = {key: sum(row[key] for row in selected) for key in numeric}
    result["source_lines"] = [row["source_line"] for row in selected]
    result["activation_rate"] = result["activated"] / result["eligible"]
    result["d30_per_activated"] = result["retained_d30"] / result["activated"]
    result["retained_per_eligible"] = result["retained_d30"] / result["eligible"]
    result["contribution_before_acquisition_rub"] = result["revenue_rub"] - result["variable_cost_rub"]
    result["contribution_after_acquisition_rub"] = result["contribution_before_acquisition_rub"] - result["acquisition_cost_rub"]
    for metric in ("revenue_rub", "variable_cost_rub", "acquisition_cost_rub", "contribution_before_acquisition_rub", "contribution_after_acquisition_rub"):
        result[metric + "_per_activated"] = result[metric] / result["activated"]
    result["contribution_after_acquisition_rub_per_eligible"] = result["contribution_after_acquisition_rub"] / result["eligible"]
    return result

cohorts = {c: aggregate([r for r in mature if r["cohort"] == c]) for c in sorted({r["cohort"] for r in mature})}
segments = {s: aggregate([r for r in mature if r["segment"] == s]) for s in sorted({r["segment"] for r in mature})}
cells = {r["cohort"] + "/" + r["segment"]: aggregate([r]) for r in mature}
seg = sorted(segments)
weights = {c: {s: cells[c + "/" + s]["activated"] / cohorts[c]["activated"] for s in seg} for c in cohorts}
rates = {c: {s: cells[c + "/" + s]["d30_per_activated"] for s in seg} for c in cohorts}
c0, c1 = sorted(cohorts)
within = sum(weights[c0][s] * (rates[c1][s] - rates[c0][s]) for s in seg)
mix = sum((weights[c1][s] - weights[c0][s]) * rates[c1][s] for s in seg)
delta = cohorts[c1]["d30_per_activated"] - cohorts[c0]["d30_per_activated"]
assert abs(delta - within - mix) < 1e-12
assert len(mature) == 4 and abs(delta + .19) < 1e-12

# Approximate two-sided, equal-sized two-proportion test; no continuity correction.
# Planning assumption only: baseline 61%, target 76%, alpha=.05, power=.8.
p0, p1, alpha, power = .61, .76, .05, .8
pbar = (p0 + p1) / 2
za, zb = NormalDist().inv_cdf(1 - alpha / 2), NormalDist().inv_cdf(power)
n = math.ceil((za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / (p1 - p0) ** 2)
intake_limit = 20
sample = {"baseline": p0, "target": p1, "alpha_two_sided": alpha, "power": power,
          "activated_accounts_per_arm": n, "activated_accounts_total": 2 * n,
          "calendar_days_if_all_eligible_activate": math.ceil(2 * n / intake_limit) * 7 + 30,
          "calendar_days_at_50pct_activation": math.ceil((2 * n / .5) / intake_limit) * 7 + 30,
          "calendar_days_at_20pct_activation": math.ceil((2 * n / .2) / intake_limit) * 7 + 30,
          "max_eligible_in_14_days": intake_limit * 2,
          "last_d30_if_last_activation_on_day14": 44,
          "caveat": "Approximation, no attrition; recruitment then 30 full days after last activation. Activation delay adds time. Not authorized or funded."}
fixed = 40000
team_contribution = segments["teams"]["contribution_after_acquisition_rub_per_activated"]
budget = {"data_and_current_flow_review_cap_rub": 2000, "prototype_and_measurement_cap_rub": 3000,
          "research_recruitment_incentives_all_labor_cap_rub": 4000, "reserve_cap_rub": 2000}
budget["incremental_cap_rub"] = sum(budget.values())
budget["allocated_existing_fixed_14_of_30_days_rub"] = fixed * 14 / 30
budget["conservative_total_rub"] = budget["incremental_cap_rub"] + budget["allocated_existing_fixed_14_of_30_days_rub"]
assert budget["conservative_total_rub"] <= 30000
result = {
    "inputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "materials").iterdir()) if p.is_file()},
    "definitions": {"unit": "company account", "d30": "retained_d30 / activated, mature rows only", "contribution": "first-30-day revenue - variable costs - acquisition costs; before fixed costs, not LTV"},
    "mature_cohorts": cohorts, "mature_segments": segments, "mature_cells": cells, "mature_all": aggregate(mature),
    "excluded_immature_retention_rows": [r for r in rows if not r["matured_d30"]],
    "decomposition": {"activated_segment_weights": weights, "observed_delta_pp": delta * 100,
                      "within_segment_effect_pp_at_august_weights": within * 100,
                      "mix_effect_pp_at_september_rates": mix * 100,
                      "september_d30_at_august_weights": sum(weights[c0][s] * rates[c1][s] for s in seg),
                      "equal_segment_weight_rates": {c: sum(rates[c].values()) / len(seg) for c in cohorts}},
    "break_even_scenario": {"monthly_fixed_rub": fixed, "team_contribution_rub_per_activated": team_contribution,
                            "activated_team_accounts_for_fixed_coverage": math.ceil(fixed / team_contribution),
                            "eligible_at_pooled_50pct_activation": math.ceil(math.ceil(fixed / team_contribution) / .5),
                            "caveat": "Scenario of first-30-day contributions covering one monthly fixed amount. Historical pooled unit economics held constant; not recurring profit or LTV."},
    "future_sample_planning": sample, "proposed_budget_caps_not_quotes": budget,
    "unknowns": ["labor and contractor rates", "research and recruitment prices", "later revenue and churn", "channel mix and acquisition allocation", "activation definition and timing", "segment distribution of fixed costs", "avoidable fixed costs", "refunds, export and closure costs", "account-level uncertainty and seasonality"]
}
(ROOT / "calculations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = ["# Воспроизводимые вычисления", "", "Запуск: `python calculate.py` (Python 3, только стандартная библиотека). Источник — materials/cohorts.csv; строки 2–5 зрелые, строка 6 исключена из D30.", "", "D30 = retained_d30 / activated. Активация = activated / eligible. Вклад = revenue_rub − variable_cost_rub − acquisition_cost_rub; постоянные затраты сюда не входят.", "", "| Когорта / сегмент | Подходят | Активированы | Удержаны | Активация | D30 | Вклад, RUB |", "|---|---:|---:|---:|---:|---:|---:|"]
for label, x in list(cells.items()) + [("Итого " + k, v) for k, v in cohorts.items()] + [("Зрелые " + k, v) for k, v in segments.items()]:
    md.append(f"| {label} | {x['eligible']} | {x['activated']} | {x['retained_d30']} | {x['activation_rate']:.2%} | {x['d30_per_activated']:.2%} | {x['contribution_after_acquisition_rub']} |")
md += ["", "Разложение ΔR = Σw_авг × (r_сен − r_авг) + Σ(w_сен − w_авг) × r_сен = +5 п.п. −24 п.п. = −19 п.п. Альтернативная фиксированная смесь 50/50 даёт 40% → 45%.", "", "Команды: (61000−20000−12000)/100 = 290 RUB на активированный аккаунт. Solo: (30000−20000−20000)/100 = −100 RUB. Все зрелые строки вместе: 91000−40000−32000 = 19000 RUB до fixed за две когорты; это не месячная прибыль.", "", "Условное покрытие fixed: ceil(40000/290) = 138 активированных команд; при исторической совокупной активации 50% это 276 подходящих аккаунтов. Ни объём рынка, ни сохранение маржи не доказаны.", "", "Размер будущего A/B: n = ceil((z_(1−α/2)√(2p̄(1−p̄)) + z_power√(p0(1−p0)+p1(1−p1)))² / (p1−p0)²). При p0=.61, p1=.76, α=.05, power=.8: 150 активированных аккаунтов на вариант, 300 суммарно. Это ориентировочный расчёт без поправки на потери; эффект +15 п.п. выбран для планирования, а не установлен данными.", "", "При потолке 20 подходящих/неделю: 15 недель набора +30 суток =135 дней, если активируются все; при 50% —30 недель +30 суток =240 дней, при 20% —75 недель +30 суток =555 дней. Дополнительная задержка активации удлинит сроки. 14 дней дают максимум 40 подходящих; при активации в последний день D30 доступен только на день 44.", "", "Лимиты проверки: 2000+3000+4000+2000 =11000 RUB дополнительных расходов, включая труд. При условном отнесении 14/30 месячных fixed: 11000+40000×14/30 =29666.67 RUB. Это лимиты, не рыночные расценки; выполнимость закупок неизвестна. Ничего не потрачено и не запущено."]
(ROOT / "calculations.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("Wrote calculations.json and calculations.md; input and arithmetic checks passed.")

if __name__ == "__main__":
    pass
