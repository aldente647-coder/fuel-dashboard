# Дашборд — Управление бензином

Оперативный дашборд для рабочей группы по управлению бензином.

## Запуск локально

```bash
pip install flask gunicorn
python app.py
```

Открыть в браузере: http://localhost:5000

## Деплой на Railway

1. Загрузите все файлы на GitHub
2. Зайдите на railway.app → New Project → Deploy from GitHub
3. Выберите репозиторий → Railway сам всё настроит
4. Settings → Networking → Generate Domain

## Страницы

- `/` — главный дашборд
- `/input` — ввод данных оператором
- `/history` — архив по датам
