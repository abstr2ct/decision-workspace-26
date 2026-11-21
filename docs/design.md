# Дизайн описания для жюри

PDF переработан в редакционный документ на 11 страницах: обложка, ценность, архитектура, демонстрация, стратегический выбор, лаборатория, критика диагностики, доказательства, использование и спецификация.

В PDF используются тёмно-фиолетовый фон, розовые и сиреневые акценты, шрифты Unbounded и Manrope и абстрактные векторные формы. Скриншоты отчётов показывают фактический вид интерфейса. Цвет в диаграммах выделяет сравниваемые величины.

HTML-отчёты, карточки и лаборатория используют ту же палитру. Шрифты WOFF2 и CSS встраиваются при экспорте. Отчёты открываются из файловой системы без сетевых запросов за оформлением. Лицензии шрифтов лежат рядом с файлами в `strategist/assets/`.

## Повторная сборка

Для сборки `tools/build_submission_pdf.py` использует `reportlab` и `Pillow`. По умолчанию берёт Segoe UI и Consolas из каталога Windows. Для шрифтов конкурсного PDF задайте `STRATEGIST_FONT_DIR` с файлами `Unbounded-SemiBold.ttf` (вес 650) и `Manrope-Regular.ttf`, `Manrope-Medium.ttf`, `Manrope-Bold.ttf` (веса 400, 500 и 750). Статические версии можно собрать из исходных переменных шрифтов через `fontTools.varLib.instancer`. Для пути вывода можно указать `STRATEGIST_PDF_OUTPUT`. Запуск агента и учебного прогона не требует этих зависимостей. [Unbounded](https://github.com/google/fonts/tree/main/ofl/unbounded), [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope).

```text
python tools/build_submission_pdf.py
```

Входы: verification-v0.6.json, checkpoint-benchmark.json, submission-video.json, examples/telecom-brief/demo-run/trace.json, screenshots/family-pilot-card.png, screenshots/family-pilot-plot.png. Матрица Лаборатории сверена с demo/lab_fixtures.py и examples/decision-lab/exports/lab-replay.json. Выход — contest-description.pdf. Шрифты встроены, ссылки на первичные источники кликабельны.

При изменении содержания повторно отрисуйте все страницы в PNG и проверьте переносы, подписи, поля и порядок чтения. Метаданные последней проверки - pdf-design-verification.json. Для финальной отправки обновляйте реальные результаты, состав моделей и стоимость по факту завершённого прогона; оформление не делает непроведённые проверки выполненными.
