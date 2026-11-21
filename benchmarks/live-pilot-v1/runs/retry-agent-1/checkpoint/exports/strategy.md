# Смена — учебная стратегия

Сформировано: 2026-11-14T06:16:45+00:00. Ревизия: 18.

> УЧЕБНЫЙ ПРИМЕР. Есть синтетические данные. Подтверждения выбора имитированы.
> Это иллюстративный кейс для задания МегаФона. Отдельный демобриф не используется.

> ЧЕРНОВИК: проверка не пройдена. Нельзя использовать как актуальную рекомендацию.

## Бриф

Статус: active. Контрольная сумма: `51411f3fdceac3d7661e866a084664c89365abfa11a70bb68c45ca44acc873f4`.


### constraints

- 30000 RUB
- 14 дней
- нет внешних действий
- только синтетические материалы
- не обещать roadmap


### data available

- cohorts.csv
- product.md
- notes.md
- request.md

**data classification:** public_or_own

**decision owner:** Сценарный владелец, бизнес-выбор не одобрен

**next question:** Вопросы недоступны; неизвестны каналы, повторная выручка, устранимые расходы.

**objective:** Выбрать проверяемую продуктовую и коммуникационную стратегию

**question:** Почему упал общий D30 и какой путь рекомендовать?

**recipient:** Владелец Смены

**success metric:** Сегментный зрелый D30, активация, вклад после привлечения

## Исследование

Статус: active. Контрольная сумма: `6dba1d335849407cddedfd84108103762c09af0987e7a234bfa4f475417c588e`.


### contradictions

- Общий D30 падает при росте внутрисегментного; обещание автопланирования противоречит roadmap.


### findings


#### claims

- cohort-summary

**conclusion:** Общий D30 52→33%, в обоих сегментах +5 п.п.; команды активируются 80→20%. См. calculations.json и report.md.

**limits:** UX не доказывает причину; вычисления отдельно прослеживаются к cohorts.csv:2–5.


---


#### claims

- capability
- roadmap

**conclusion:** Рекламный текст не соответствует функциям

**limits:** Учебный снимок, нет рыночной проверки


---



### questions

**decision impact:** Не переделывать весь onboarding без диагноза

**method:** Зрелые когорты по сегментам и диагностика событий

**question:** Mix или ухудшение пути?

**status:** Описательный расчёт выполнен; причина неизвестна


---


**stop rule:** 14 дней или 30000 RUB; неубедительный результат не разрешает расширение.


### unknowns

**decision impact:** Может изменить фокус или привести к закрытию

**next action:** Диагностика и финансовый сценарий до дня 14

**unknown:** Каналы, события, LTV, устранимые расходы


---


## Варианты

Статус: active. Контрольная сумма: `0636a08e3614b232b5fdab3fb774f49da6ac3e0b7b39f26990feefb7482dca0c`.

**comparison:** Общий горизонт финансового сценария три месяца; данных пока мало для числового рейтинга. Подробности report.md.


### Варианты

**audience:** Текущие аккаунты

**changes:** Без развития и рекламы


#### claims

- capability
- roadmap
- fixed
- ux
- cohort-summary

**economics:** 40000/месяц сохраняются

**id:** keep

**kind:** status_quo

**name:** Статус-кво


#### objections

- Потеря активации команд
- Отрицательный вклад solo

**validation:** Проверка измерений и зрелых когорт


---

**audience:** Команды до 20

**changes:** Проверка текущего пути и точечный прототип


#### claims

- capability
- roadmap
- fixed
- ux
- cohort-summary

**economics:** Потолок 30000, эффект неизвестен

**id:** focus

**kind:** focus

**name:** Диагностика команд


#### objections

- Причина может быть в канале
- Потеря будущей ценности solo

**validation:** Логи, до 8 UX, повторная выручка


---

**audience:** Все аккаунты

**changes:** Перестройка обучения


#### claims

- capability
- roadmap
- fixed
- ux
- cohort-summary

**economics:** Стоимость неизвестна

**id:** rewrite

**kind:** other

**name:** Полный onboarding


#### objections

- Дублирование существующего примера
- Не решает качество потока

**validation:** Сначала диагностика


---

**audience:** Все текущие клиенты

**changes:** Остановка развития и план выхода


#### claims

- capability
- roadmap
- fixed
- ux
- cohort-summary

**economics:** Экономия устранимой части постоянных затрат минус стоимость выхода

**id:** close

**kind:** shutdown

**name:** Закрытие


#### objections

- Потеря будущих потоков команд
- Миграция и обязательства могут быть дороже

**validation:** Трёхмесячное сравнение продолжения и выхода


---


**recommendation:** focus


### reversal conditions

- Проблема событий или каналов — сохранять интерфейс
- Устойчиво отрицательный будущий вклад и нет дешёвого восстановления — рассмотреть закрытие
- Нет ясного результата на дне 14 — не масштабировать

**why not others:** Сначала установить причину и стоимость обратимого шага; статус-кво оставляет активацию, переписывание не обосновано, закрытие преждевременно.

## Реестр выводов

### capability — demo_fact / active

В учебном продукте есть ручное расписание, повтор и приглашения.

Уверенность: high. Точная строка учебного материала; вне сценария не подтверждено.

- Источник `product`, `line:2`: «Доступно: ручное расписание, повтор смен, приглашения сотрудников, предупреждения о пересечении смен.»; [снимок](../blobs/8a83ab7e7b4fbcdafd81a4e5b24b68a376f7c0e522410c3df3ece6cb09b0b8b9.md).

### cohort-summary — demo_fact / active

Зрелые команды 61/100 D30 и вклад 29000 RUB; solo 24/100 и -10000 RUB.

Уверенность: high. Производный расчёт из синтетического CSV; не причинность и не реальный рынок.

- Источник `cohort-metrics`, `line:1`: «{"currency":"RUB","excluded":[{"cohort":"2026-10","reason":"D30 not matured","row":6,"segment":"teams"}],"limits":["Synthetic input stays synthetic","Descriptive segment differences are not causal effects","Wilson intervals assume independent Bernoulli observations; repeated users/clusters invalidate them","Contribution excludes fixed costs, taxes and later cash flows; this is not profit or LTV"],"method":"Sum mutually exclusive matured cohorts by segment; ratios of sums, Wilson 95% for D30/activated","segments":{"solo":{"acquisition_cost_rub":20000.0,"activated":100.0,"activation_rate":0.3333333333333333,"cohorts":["2026-08","2026-09"],"contribution_after_acquisition_rub":-10000.0,"contribution_before_acquisition_rub":10000.0,"d30_95pct_wilson":[0.16691325556948772,0.33232336349814473],"d30_per_activated":0.24,"d30_per_eligible":0.08,"eligible":300.0,"retained_d30":24.0,"revenue_rub":30000.0,"variable_cost_rub":20000.0},"teams":{"acquisition_cost_rub":12000.0,"activated":100.0,"activation_rate":0.5,"cohorts":["2026-08","2026-09"],"contribution_after_acquisition_rub":29000.0,"contribution_before_acquisition_rub":41000.0,"d30_95pct_wilson":[0.5120301704584073,0.6998312599360558],"d30_per_activated":0.61,"d30_per_eligible":0.305,"eligible":200.0,"retained_d30":61.0,"revenue_rub":61000.0,"variable_cost_rub":20000.0}},"window":"first 30 days; no LTV extrapolation"}»; [снимок](../blobs/0d95a9db3f9a38af6ddee6e09b82452f6dcb13305d8312d99b207ce475b553d7.json).

### fixed — demo_fact / active

Фиксированные затраты 40000 RUB/месяц, таблица не LTV.

Уверенность: high. Точная строка учебного материала; вне сценария не подтверждено.

- Источник `product`, `line:7`: «Постоянные затраты продукта за месяц 40000 RUB, распределение по сегментам не определено. Таблица содержит первые 30 дней выручки и переменных затрат, не годовую прибыль и не LTV.»; [снимок](../blobs/8a83ab7e7b4fbcdafd81a4e5b24b68a376f7c0e522410c3df3ece6cb09b0b8b9.md).

### roadmap — demo_fact / active

Автопланирование не выпущено.

Уверенность: high. Точная строка учебного материала; вне сценария не подтверждено.

- Источник `product`, `line:3`: «Автоматическое составление расписания находится в roadmap. Оно не выпущено и дата релиза не утверждена.»; [снимок](../blobs/8a83ab7e7b4fbcdafd81a4e5b24b68a376f7c0e522410c3df3ece6cb09b0b8b9.md).

### ux — demo_fact / active

Два учебных сеанса не оценивают частоту проблемы.

Уверенность: high. Точная строка учебного материала; вне сценария не подтверждено.

- Источник `notes`, `line:3`: «Два собственных обезличенных наблюдения сценарного UX-сеанса: участники создали смену; один не нашёл кнопку приглашения. Это учебные наблюдения двух человек, не оценка распространённости проблемы.»; [снимок](../blobs/5cc1d1c5f446e58095d4eb227bd0129f9cd382bef030c44791106246f82aa92b.md).

## Решение и подтверждения


### decision

**at:** 2026-11-14T06:16:44+00:00


#### claims

- cohort-summary
- capability
- roadmap
- fixed
- ux

**option id:** focus

**options hash:** 0636a08e3614b232b5fdab3fb774f49da6ac3e0b7b39f26990feefb7482dca0c

**rationale:** Условная диагностика до 30000 RUB и решения на дне 14. Только рекомендация, бизнес-решение не одобрено. Подробная стратегия в report.md.

**sha256:** ea2a73be37edfe1e8be429d24478771dd370710cfb0497966443260354dd58ea

**status:** proposed


### approvals


#### Бриф

**actor:** Сценарный владелец

**at:** 2026-11-14T06:16:13+00:00

**reason:** materials/request.md:6 подтверждает рамку, исключительно workflow; не бизнес-решение

**simulation:** True

**target:** 51411f3fdceac3d7661e866a084664c89365abfa11a70bb68c45ca44acc873f4

## Обязательства


## Время и стоимость


### totals


### unreported categories

- human
- model
- search
- tool

**note:** Unreported is not zero. Recorded durations may overlap; do not add them as elapsed time.


## Проверка и ограничения

**ok:** False


### errors

- Missing or stale document: strategy
- Missing or stale human gate: decision


### warnings

- DEMO: synthetic evidence and simulated approvals; not a real business validation
- Incomplete cost coverage: human, model, search, tool
- Structural audit verifies citations and workflow, not truth, causality, strategy quality or identity of the approving human

**revision:** 18

Поиск: BM25 с расширением по двуязычному словарю и явные связи. Embeddings, автоматическая смена LLM, фоновый мониторинг, PDF/OCR и мультимодальные модели не реализованы. Записи состояния не являются независимыми источниками.
