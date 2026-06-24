Deployment options for the Urban Tour bot

This document shows several simple ways to run the bot constantly so you don't need to keep your PC on.

1) VPS with systemd
- copy the repository to the VPS (e.g. /opt/urban_tour_bot)
- install Python 3.11 and create a virtualenv

Commands (on VPS):
```bash
sudo apt update && sudo apt install -y python3.11 python3-venv git
sudo useradd --system --create-home --shell /bin/false urbanbot
sudo mkdir -p /opt/urban_tour_bot
sudo chown $USER:$USER /opt/urban_tour_bot
git clone <repo_url> /opt/urban_tour_bot
cd /opt/urban_tour_bot/urban_tour_bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
systemctl --user enable --now <service-file>
```

Use the provided `systemd-example.service` as a template — copy it to `/etc/systemd/system/urban_tour_bot.service` and set the `WorkingDirectory` and `ExecStart` appropriately, and set environment variables via an `/etc/urban_tour_bot.env` file or `EnvironmentFile=`.

2) Docker / Docker Compose (recommended)
- Build locally or on server, run with restart policy.

Commands (build & run):
```bash
cd urban_tour_bot
docker compose build
docker compose up -d
```

3) PaaS (Render / Railway / Heroku)
- Use the included `Dockerfile` or `Procfile` (Heroku). Configure environment variables in the platform dashboard. Push the repository or connect GitHub — the platform will keep the service alive.

4) Fly.io (recommended free tier)
- Fly.io supports running Dockerized apps and has a free tier suitable for bots. The repository includes `urban_tour_bot/fly.toml` and a GitHub Actions workflow to deploy automatically.

Quick steps to deploy to Fly.io:

1. Create a Fly account and install `flyctl` locally: https://fly.io/docs/hands-on/install/
2. Create an app (or let workflow create it). Example:

```bash
flyctl auth login
flyctl apps create your-app-name --org personal --region ams
```

3. Add required secrets to your GitHub repository (Settings → Secrets): `FLY_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

4. Push to `main` — GitHub Actions will build and deploy the image to Fly.

Notes:
- The workflow uses `--remote-only` which builds the image on Fly builders. If you prefer building locally and pushing, remove `--remote-only`.
- Monitor app logs with `flyctl logs -a your-app-name`.


4) CI for container images
- A GitHub Actions workflow in `.github/workflows/docker-image.yml` will build and push images to GitHub Container Registry. Provide appropriate repository secrets if you want to push to Docker Hub instead.

Notes
- Do NOT commit `.env` with secrets. Use `.env.example` as the template.
- For production, use a supervisor (systemd/docker) and add monitoring (Prometheus/Healthchecks.io) or simple cron to verify bot is running.
# Деплой бота — варианты, чтобы он работал когда ПК выключен

В этом файле кратко описаны простые варианты запуска бота постоянно (24/7).

1) Быстрый и простой — Deploy на Render / Railway / Replit
- Создайте аккаунт на выбранном сервисе (Render.com, Railway.app, Replit.com).
- Подключите репозиторий или загрузите файлы проекта (папка `urban_tour_bot`).
- В настройках сервиса укажите команду запуска: `python bot.py` или используйте `Procfile` (есть `worker: python bot.py`).
- В переменных окружения (ENV) задайте `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`.

Плюсы: быстро, не нужен сервер. Минусы: может быть платным при постоянной нагрузке.

2) Docker на VPS / облачный сервер (рекомендуется для стабильности)
- На VPS (например, DigitalOcean, Hetzner, AWS EC2) установите Docker.
- Сборка и запуск (в директории `urban_tour_bot`):

```bash
docker build -t urban-tour-bot:latest .
docker run -d --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN="<ваш_токен>" \
  -e TELEGRAM_CHAT_ID="<@или_-100id>" \
  --name urban-tour-bot urban-tour-bot:latest
```

Плюсы: вы контролируете окружение. Минусы: нужен VPS и базовые навыки.

3) systemd сервис (если вы запускаете напрямую на Linux сервере без Docker)
- Скопируйте проект в `/opt/urban_tour_bot`.
- Создайте и активируйте виртуenv, установите зависимости.
- Создайте unit-файл `/etc/systemd/system/urban_tour_bot.service` (пример ниже) и включите service.

Пример `urban_tour_bot.service`:

```
[Unit]
Description=Urban Tour Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/urban_tour_bot
Environment="TELEGRAM_BOT_TOKEN=..."
Environment="TELEGRAM_CHAT_ID=..."
ExecStart=/usr/bin/python3 /opt/urban_tour_bot/bot.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Команды включения:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now urban_tour_bot.service
sudo journalctl -u urban_tour_bot -f
```

4) Windows Server / Always-on ПК
- На Windows Server можно настроить службу (nssm) или планировщик задач с перезапуском при падении.

Полезные примечания:
- Никогда не храните секреты в репозитории. Для Docker/VPS используйте переменные окружения.
- Убедитесь, что `TELEGRAM_CHAT_ID` корректен и бот добавлен в группу/чат с правами писать.
- Для рекламы лучше выбрать облачный хостинг (Render / Railway / VPS).

Если хотите, могу подготовить SSH-скрипт для автоматического деплоя на VPS или показать точные шаги для Render/Railway.
