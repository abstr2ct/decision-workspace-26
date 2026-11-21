# MCP: локальная интеграция без сервера в интернете

Поставляется read-only MCP stdio адаптер, закреплённый за одной папкой проекта. Он не принимает аргумент произвольного пути, не выполняет shell, не читает секреты и не меняет одобрения. Запись и содержательные решения остаются через CLI и диалог с владельцем.

Запуск из корня репозитория:

```text
python -X utf8 -m strategist.mcp_server --project examples/public-case
```

На stdout идут только JSON-RPC сообщения, не интерактивное меню. Сервер ожидает initialize, затем notifications/initialized. Поддерживаемая версия протокола - 2025-11-25; при другой версии сервер предлагает свою, а клиент решает, совместим ли он. Реализована локальная stdio часть, не HTTP/OAuth/tasks.

Семь инструментов: `strategy_resume`, `strategy_context`, `strategy_search`, `strategy_source`, `strategy_impact`, `strategy_audit`, `strategy_lab`. Последний проверяет актуальность сохранённой сценарной модели и возвращает её расчёт; допущения не считаются фактами. Источники явно обозначены как недоверенные данные. Read-only относится к файлам проекта; он не означает, что прочитанный текст можно исполнять.

В клиенте, который поддерживает стандартный блок mcpServers, укажите абсолютные пути. Конкретное место настройки зависит от выбранной IDE; этот пример не является универсальным файлом настроек всех редакторов:

```json
{
  "mcpServers": {
    "product-strategist": {
      "command": "ABSOLUTE_PATH_TO_PYTHON",
      "args": ["-X", "utf8", "-m", "strategist.mcp_server", "--project", "ABSOLUTE_PATH_TO_PROJECT"],
      "cwd": "ABSOLUTE_PATH_TO_REPOSITORY"
    }
  }
}
```

Если клиент не поддерживает cwd, выполните локальную установку пакета в выбранное окружение (`python -m pip install --no-build-isolation --no-deps .`) либо используйте wrapper, который сначала выбирает корень репозитория. Обычная работа CLI установки не требует. Не копируйте ключи IDE в репозиторий.

Проверен реальный обмен JSON-RPC в свежем subprocess: инициализация, список, вызов поиска и неизменность state.json. Подключение к каждому внешнему MCP-клиенту отдельно не проверялось.

Основания реализации: [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle), [tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools). Библиотека MCP SDK не является обязательной зависимостью.
