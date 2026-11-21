# Смена — учебная стратегия

Сформировано: 2026-11-18T05:53:20+00:00. Ревизия: 23.

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

Статус: active. Контрольная сумма: `6d32dc421aadded9f9496cca33367040acc43d3c9590fa0aa398ff6e846d3bd5`.


### contradictions

- Исправление строки отменяет оценку сентябрьского D30 команд в 65% и положительный вклад +5 000 ₽. Исходная версия хранится в истории.


### findings


#### claims

- corrected-d30
- correction-confirmed

**conclusion:** В исправленной таблице изменение внутри сегментов объясняет −27 п.п. в выбранном разложении.

**limits:** Описательный расчёт, малая выборка, причины не установлены


---


#### claims

- corrected-contribution

**conclusion:** Сентябрьский вклад команд после привлечения отрицателен.

**limits:** 30 дней и три статьи, без постоянных расходов и повторных доходов


---



### questions

**decision impact:** Меняет целесообразность увеличения закупок

**method:** Повторить расчёт на исправленной таблице

**question:** Сохраняется ли объяснение через состав аудитории?

**status:** Расчёт выполнен, ожидается сверка событий


---


**stop rule:** День 14 или достижение лимита сверки 8 000 ₽ после согласования владельцем


### unknowns

**decision impact:** Определяет условия пилота, продолжения и закрытия

**next action:** Сверить события и учёт, собрать сопоставимые зрелые когорты

**unknown:** Причины снижения и экономика повторных месяцев


---


## Варианты

Статус: active. Контрольная сумма: `19efc8aa8efaa889fbb911fba723a54a7ff52496172ef8e3fb5145faa4240f12`.

**comparison:** Одинаковый горизонт первичного решения 14 дней, приоритет обратимых действий.


### Варианты

**audience:** Администраторы команд до 20 сотрудников

**changes:** Сохранить путь и текущий объём. Отложить дополнительное привлечение.


#### claims

- corrected-d30
- corrected-contribution

**economics:** Предложенный потолок сверки 8 000 ₽ на 14 дней.

**id:** keep

**kind:** status_quo

**name:** Статус-кво продукта и сверка


#### objections

- Задержка при настоящем барьере
- Текущие расходы сохраняются

**validation:** Сверить события и три статьи вклада; решение владельца на дне 14.


---

**audience:** Администраторы команд до 20 сотрудников

**changes:** Проверить существующий путь от первой смены до приглашения.


#### claims

- capability
- ux
- corrected-contribution

**economics:** Запрашивать финансирование пилота после сверки.

**id:** focus

**kind:** focus

**name:** Диагностика пути команд


#### objections

- Сбой может быть в канале или трекинге
- Улучшение UX может не окупиться

**validation:** Воспроизвести барьер и оценить цену проверки.


---

**audience:** Администраторы команд до 20 сотрудников

**changes:** Обновить весь путь для сегментов.


#### claims

- capability
- roadmap
- correction-confirmed

**economics:** Стоимость разработки и влияние неизвестны.

**id:** rewrite

**kind:** other

**name:** Полная переделка онбординга


#### objections

- Интерактивный пример уже есть
- Не устранит учётную ошибку

**validation:** Подтвердить повторяемую проблему в нескольких шагах и оценить затраты.


---

**audience:** Администраторы команд до 20 сотрудников

**changes:** Проверить план выхода и поддержку клиентов.


#### claims

- fixed
- corrected-contribution

**economics:** Экономия зависит от устранимых расходов и стоимости выхода.

**id:** close

**kind:** shutdown

**name:** Закрытие направления


#### objections

- Одна исправленная когорта не определяет будущий вклад
- Выход может оказаться дороже продолжения

**validation:** Сравнить повторные доходы, затраты и обязательства на одном горизонте.


---


**recommendation:** keep


### reversal conditions

- События подтверждают устойчивый барьер — рассмотреть ограниченный UX-пилот.
- Сопоставимые зрелые когорты подтверждают приемлемый вклад — вернуться к вопросу закупок.
- Продолжение устойчиво слабее выхода на едином горизонте — вынести закрытие на выбор владельца.

**why not others:** Пилот требует сверки, переделка требует подтверждённого барьера, закрытие требует экономики выхода.

## Реестр выводов

### capability — demo_fact / active

В учебном продукте есть ручное расписание, повтор и приглашения.

Уверенность: high. Точная строка учебного материала; вне сценария не подтверждено.

- Источник `product`, `line:2`: «Доступно: ручное расписание, повтор смен, приглашения сотрудников, предупреждения о пересечении смен.»; [снимок](../blobs/8a83ab7e7b4fbcdafd81a4e5b24b68a376f7c0e522410c3df3ece6cb09b0b8b9.md).

### cohort-summary — demo_fact / review_required

Зрелые команды 61/100 D30 и вклад 29000 RUB; solo 24/100 и -10000 RUB.

Уверенность: high. Производный расчёт из синтетического CSV; не причинность и не реальный рынок.

- Источник `cohort-metrics`, `line:1`: «{"currency":"RUB","excluded":[{"cohort":"2026-10","reason":"D30 not matured","row":6,"segment":"teams"}],"limits":["Synthetic input stays synthetic","Descriptive segment differences are not causal effects","Wilson intervals assume independent Bernoulli observations; repeated users/clusters invalidate them","Contribution excludes fixed costs, taxes and later cash flows; this is not profit or LTV"],"method":"Sum mutually exclusive matured cohorts by segment; ratios of sums, Wilson 95% for D30/activated","segments":{"solo":{"acquisition_cost_rub":20000.0,"activated":100.0,"activation_rate":0.3333333333333333,"cohorts":["2026-08","2026-09"],"contribution_after_acquisition_rub":-10000.0,"contribution_before_acquisition_rub":10000.0,"d30_95pct_wilson":[0.16691325556948772,0.33232336349814473],"d30_per_activated":0.24,"d30_per_eligible":0.08,"eligible":300.0,"retained_d30":24.0,"revenue_rub":30000.0,"variable_cost_rub":20000.0},"teams":{"acquisition_cost_rub":12000.0,"activated":100.0,"activation_rate":0.5,"cohorts":["2026-08","2026-09"],"contribution_after_acquisition_rub":29000.0,"contribution_before_acquisition_rub":41000.0,"d30_95pct_wilson":[0.5120301704584073,0.6998312599360558],"d30_per_activated":0.61,"d30_per_eligible":0.305,"eligible":200.0,"retained_d30":61.0,"revenue_rub":61000.0,"variable_cost_rub":20000.0}},"window":"first 30 days; no LTV extrapolation"}»; [снимок](../blobs/0d95a9db3f9a38af6ddee6e09b82452f6dcb13305d8312d99b207ce475b553d7.json).

### corrected-contribution — demo_fact / active

Вклад команд за сентябрь после привлечения равен −15 000 ₽: 5 000 − 16 000 − 4 000.

Уверенность: high. Три статьи одной зрелой строки. Постоянные расходы и будущие потоки не включены.

- Источник `cohorts-corrected`, `row:4`: «2026-09»; [снимок](../blobs/67142fe72cc11003d96ff82d3f23911d80a5b22a38c400e4f8b841c4b2757d14.csv).

### corrected-d30 — demo_fact / active

Сентябрьский D30 равен 25%. Разложение относительно августа: внутри сегментов −27 п.п., изменение состава 0 п.п.

Уверенность: high. Расчёт на заданной учебной таблице. Причины не установлены.

- Источник `corrected-period-comparison`, `line:1`: «"current_d30":0.25»; [снимок](../blobs/fdd87a9845938a822aa0a92857973c6e1b8109db93822968d3159b6c4cf1b195.json).
- Источник `corrected-period-comparison`, `line:1`: «"within_segment_change_pp":-27.0»; [снимок](../blobs/fdd87a9845938a822aa0a92857973c6e1b8109db93822968d3159b6c4cf1b195.json).

### correction-confirmed — demo_fact / active

Учебный аналитик исправил одну строку за сентябрь.

Уверенность: high. Сценарное исправление зафиксировано в записке.

- Источник `analyst-correction`, `line:2`: «Исправление только строки 2026-09, teams в cohorts.csv: retained_d30 равно 5, а не 13; revenue_rub равно 5000, а не 13000; variable_cost_rub равно 16000, а не 4000. activated=20, eligible=100, acquisition_cost_rub=4000 остаются прежними. Ошибка выгрузки подтверждена внутри учебного сценария.»; [снимок](../blobs/6cc86ba52157b771e2511d7ab853b23b5c252377bcce48a3062f3297ddf037c3.md).

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

**at:** 2026-11-18T05:53:20+00:00


#### claims

- corrected-d30
- corrected-contribution
- capability

**option id:** keep

**options hash:** 19efc8aa8efaa889fbb911fba723a54a7ff52496172ef8e3fb5145faa4240f12

**rationale:** Отложить увеличение закупок и изменения продукта. Сверить зрелые когорты и экономику за 14 дней с предложенным лимитом 8 000 ₽.

**sha256:** 5f0db732159ab610ed6f9c01af654b7c2595dafe1773ea0987ac5ccff376e4a8

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

- cohort-summary: review_required; retained as history, not usable evidence
- DEMO: synthetic evidence and simulated approvals; not a real business validation
- Incomplete cost coverage: human, model, search, tool
- Structural audit verifies citations and workflow, not truth, causality, strategy quality or identity of the approving human

**revision:** 23

Поиск: BM25 с расширением по двуязычному словарю и явные связи. Embeddings, автоматическая смена LLM, фоновый мониторинг, PDF/OCR и мультимодальные модели не реализованы. Записи состояния не являются независимыми источниками.
