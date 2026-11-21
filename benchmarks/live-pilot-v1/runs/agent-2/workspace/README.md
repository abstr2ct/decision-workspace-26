# Стратег Фабрики продуктов

**Версия 0.3.** Агент показывает, что заставит изменить решение и какую проверку стоит провести следующей. Начните с [Лаборатории решений](examples/decision-lab/exports/decision-lab.html): переключите сценарий и посмотрите, как меняются варианты. Затем откройте [кейс на первичных открытых источниках](examples/public-case/exports/dashboard.html): согласованные стратегии, найденное расхождение документации и пересмотр после критики. Числа лаборатории учебные; подтверждения владельца в примерах сценарные. Отдельного демобрифа не ждём.

Главное дополнение v0.3 — сценарная проверка выбора с жёсткими ограничениями, ценой ошибки, стоимостью исследования, задержкой и неоднозначными исходами. Анализ связан с текущими основаниями и устаревает при новых данных. Это применение известных методов принятия решений, не новый математический алгоритм. [Метод и границы](docs/decision-lab.md), [проверки](docs/verification-v0.3.json), [что изменилось](docs/changes-v0.3.md).

Описание для жюри — [дизайнерский PDF](docs/contest-description.pdf): 10 страниц, архитектура, кейс, варианты, лаборатория и доказательства. Исходник вёрстки и требования к её сборке — [docs/design.md](docs/design.md). [Проверка за 90 секунд](docs/jury-tour.md) помогает быстро оценить работу без изучения кода.

Папка агента для руководителя цифрового продукта: от неоднозначного запроса до проверяемой продуктовой и коммуникационной стратегий, с продолжением работы после решения.

LLM работает в вашей IDE, читает инструкции и сама выбирает следующие инструменты. Python CLI хранит основания, считает показатели и проверяет инварианты. Это не отдельное автономное приложение и не скрипт, автоматически сочиняющий стратегию.

## Запуск за две минуты

Нужны **Python 3.10+** и терминал в корне этой папки. Для учебной проверки не нужны сеть, API-ключи или сторонние библиотеки. Для реальной агентной работы нужна IDE с LLM и разрешением читать файлы/запускать команды; подписка или API оплачиваются отдельно по условиям выбранной среды. Python должен быть установлен отдельно.

```text
python --version
python -X utf8 -m strategist --help
python -X utf8 demo/run.py projects/demo
python -X utf8 -m strategist resume projects/demo
```

Результат: `projects/demo/exports/dashboard.html`, `strategy.md`, `audit.json`, `lineage.mmd`, `replay.json`. Откройте dashboard.html обычным браузером; сервер и сеть для просмотра не нужны.

Demo — **авторский сценарный replay** синтетических материалов через реальные инструменты. Он проверяет полный проход, перерыв и сохранность состояния. Он не вызывает LLM и не измеряет качество живого агентного исследования. Источник, выводы, одобрения и итог явно помечены как учебные. Повторный запуск в непустую папку не перезаписывает работу: выберите новый путь.

Для реальной работы откройте папку в Codex/Cursor/другой IDE и вставьте стартовый запрос из [START.md](START.md). Codex читает AGENTS.md; для Cursor есть входной файл `.cursor/rules/strategist.mdc`. В других средах явно укажите AGENTS.md. Совместимость с каждой конкретной версией IDE отдельно не проверялась. Ручной `pip install` не нужен; `python -m strategist` запускается из корня.

## Что готово

- Стадии «бриф → исследование → варианты → выбор → стратегия → сопровождение» и два содержательных решения человека.
- Импорт UTF-8 TXT/MD/JSON, CSV/TSV, DOCX, XLSX без формул и публичных HTTPS-страниц с разрешённых доменов.
- Снимки с SHA-256, локаторы и проверка точных цитат; факты, гипотезы, прогнозы и учебные наблюдения хранятся раздельно.
- Минимум три варианта с обязательными статус-кво и закрытием, возражения, экономика, согласование продуктовых возможностей и обещаний.
- Когортные расчёты, исключение незрелых когорт, проверка знаменателей и единиц, Wilson CI и планирование A/B.
- Атомарные записи, блокировка конкурентной записи, идемпотентный импорт, pause/resume в новом процессе.
- Трассировка отзыва источников через производные сведения; снятие прежнего выбора; обязательства, сроки и признаки устаревшего основания.
- Учёт известных расходов по категориям и валютам, явное отображение неизвестных затрат.
- Три skills, события валидации/инвалидации и отдельный критический проход модели.
- «Лаборатория решений»: что меняет выбор, когда исследование не оправдывает затраты, почему неубедительный исход важен; проверяемая связь с текущими документами и claims.

Чего здесь пока нет: фонового мониторинга, автоматического переключения моделей, независимых субагентов, векторного поиска, PDF/OCR-извлечения, аудио/видео-анализа и автоматической проверки истинности. Эти возможности не заявляются ради количества компонентов. MCP доступен как локальный read-only stdio адаптер; [инструкция](docs/mcp.md).

## Основные команды

Все пути в примерах — относительно корня репозитория. Используйте кавычки для путей с пробелами. Пустые JSON-формы предназначены для заполнения; для работающего примера смотрите `demo/fixtures.py` и созданную папку `authored-fixtures`.

```text
python -m strategist init projects/case --name "Мой продукт" --question "Почему снижается удержание?"
python -m strategist commit projects/case brief projects/case/brief.json
python -m strategist approve projects/case brief --by "Владелец продукта" --reason "Подтверждение в чате: цель и ограничения согласованы"
python -m strategist source add projects/case materials/brief.docx --id interview-notes --title "Обезличенные собственные заметки"
python -m strategist source show projects/case interview-notes
python -m strategist search projects/case "первое использование"
python -m strategist retrieve projects/case "удержание"
python -m strategist context projects/case --max-chars 6000
python -m strategist impact projects/case interview-notes
python -m strategist claim add projects/case projects/case/claim.json
python -m strategist commit projects/case research projects/case/research.json
python -m strategist commit projects/case options projects/case/options.json
python -m strategist propose projects/case --option change --rationale "Основания рекомендации" --claims claim-id
python -m strategist approve projects/case decision --by "Владелец продукта" --reason "Явный выбор в чате"
python -m strategist commit projects/case strategy projects/case/strategy.json
python -m strategist audit projects/case
python -m strategist export projects/case
```

`approve` технически записывает согласие, а не проверяет личность. Агенту запрещено подписывать выбор за человека; в demo используется отдельный флаг `--simulation`. Одобрение не даёт разрешения отправлять письма, публиковать рекламу или тратить деньги.

Сайты включаются отдельно для конкретного проекта. Разрешать нужно точные домены, включая домен после перенаправления:

```text
python -m strategist web allow-host projects/case www.iana.org
python -m strategist web fetch projects/case https://www.iana.org/help/example-domains --id web-example --title "Пример импорта публичной страницы; не источник рынка"
```

Могут потребоваться доступ в интернет и разрешение терминала со стороны среды. При недоступности сайта не подменяйте его содержимое догадками. Явно импортированный вручную публичный снимок получает `--origin public --url <оригинал>`; сам по себе URL не доказывает подлинность снимка.

Перерыв, расчёты, стоимость и пересмотр:

```text
python -m strategist pause projects/case --reason "Ждём уточнения владельца"
python -m strategist resume projects/case
python -m strategist continue projects/case
python -m strategist analyze-cohorts projects/case --source cohort-data --id cohort-metrics
python -m strategist plan-ab --baseline 0.6 --target 0.7
python -m strategist cost projects/case --category model --amount 0.12 --currency USD --seconds 20 --basis "Пример команды; замените на реальные usage и тариф" --estimated
python -m strategist source supersede projects/case old-source --with corrected-source --reason "Исправлен знаменатель"
python -m strategist source withdraw projects/case unreliable-source --reason "Отозванное основание"
python -m strategist commitment carry-forward projects/case check-demand --reason "Обязательство сохраняет смысл при новом согласованном выборе"
```

Если audit не пройден, обычный export остановится. `export --draft` создаёт явно помеченный черновик. Отозванные claims остаются в истории; добавить новую исправленную запись нужно с новым ID. Изменение брифа/исследования/вариантов снимает зависимые подтверждения. Нельзя редактировать state для обхода проверки.

## Структура

```text
AGENTS.md                 постоянные инструкции
.cursor/rules/            входная точка Cursor
.agents/skills/           критический обзор и пересмотр решения
knowledge/                исследование, стратегия, эксплуатация
templates/                формы новых артефактов
strategist/               инструменты CLI, расчёты и состояние
demo/                     синтетические входы и явные сценарные fixtures
examples/replay/           сохранённый учебный проход (в поставке)
examples/revision/         исправление данных и сценарный новый выбор
examples/public-case/      анализ первичных открытых источников в текущей LLM-сессии
tests/                    проверки инвариантов и восстановления
tools/                    сравнение измеренных прогонов
docs/                     архитектура, ограничения, сценарий видео, подготовка к сдаче
projects/                 локальные рабочие проекты (не коммитятся)
```

Для переноса задачи скопируйте весь репозиторий и всю папку проекта, включая blobs. Относительные ссылки продолжат работать; CLI не требует исходного абсолютного пути. Не переносите `.env` и секреты.

## Проверка

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 demo/run.py projects/recheck
python -X utf8 -m strategist audit projects/recheck
python -X utf8 demo/revise.py projects/recheck
```

Описание архитектуры — [docs/architecture.md](docs/architecture.md). Статус сдачи — [docs/submission.md](docs/submission.md). Сравнение с обычным чатом ещё не измерено. Измерена инженерная альтернатива: весь state и источники против ограниченного пакета продолжения. Это не оценка стоимости LLM или качества стратегии; полный протокол — docs/evaluation.md.
