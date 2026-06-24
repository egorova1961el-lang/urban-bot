# Urban Tour Telegram Bot

Простой Telegram-бот для сбора заявок на консультацию по урбан-турам.

## Установка

1. Перейдите в папку проекта:
   ```powershell
   cd "c:\Users\Лиза\Downloads\Проект ИИ контроль показателей\urban_tour_bot"
   ```
2. Создайте виртуальное окружение:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Установите зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
4. Скопируйте `.env.example` в `.env` и заполните:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Вставьте токен бота и ID/юзернейм группы для получателя заявок.

## Запуск

```powershell
python bot.py
```

## Как работает

- `/start` — приветствие и меню.
- кнопка `Узнать об урбан-турах` — информация о программе.
- кнопка `Оставить заявку` — сбор заявки и отправка её в указанный чат.
- `/cancel` — отмена текущей заявки.
