# KPI Traffic Report

Проект считает план/факт по трафику (по городам) и выгружает отчет в Google Sheets.

## Что нужно для запуска на новом компьютере

1. Python 3.11+ (рекомендуется 3.12/3.13/3.14).
2. Файл `.secrets/credentials.json` (OAuth credentials для Google Sheets API).
3. Файл `.env` (можно сделать из `.env.example`).

## Быстрый старт

1. Открыть папку проекта.
2. Создать и активировать виртуальное окружение:
   - Windows PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Установить зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
4. Создать `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Заполнить `.env`:
   - `KEY_INDICATORS_TOKEN`
   - `REPORT_SHEETS_URL`
   - при необходимости Telegram-переменные
6. Положить `credentials.json` в папку `.secrets/`.
7. Запустить:
   ```powershell
   python src/main.py
   ```

При первом запуске откроется OAuth-авторизация Google, после подтверждения создастся `.secrets/token.json`.

## Расписание

Скрипт сам по себе не планирует запуск.
Используйте Windows Task Scheduler (например, по понедельникам).

Команда для задачи:
```powershell
python c:\path\to\project\src\main.py
```

## Кэш прошлых месяцев

Фиксация полных месяцев хранится в `.cache/traffic_history.json`.

- Если кэш не переносить на новый ПК, он создастся заново.
- Если нужно пересчитать прошлые месяцы с нуля, удалите `.cache/traffic_history.json`.
