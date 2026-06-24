#!/usr/bin/env bash
# Simple deployment helper for VPS (requires git and docker)
set -euo pipefail

# Edit these when using
REPO_URL="<REPO_GIT_URL>"
APP_DIR="/opt/urban_tour_bot"

if [ "$REPO_URL" = "<REPO_GIT_URL>" ]; then
  echo "Please edit deploy_prod.sh and set REPO_URL to your repository URL"
  exit 1
fi

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  git fetch --all && git reset --hard origin/HEAD
fi

cd "$APP_DIR/urban_tour_bot"
if [ ! -f .env ]; then
  cp .env.prod.example .env
  echo "Copied .env.prod.example to .env — edit .env and fill secrets, then re-run this script."
  exit 0
fi

# Ensure docker compose plugin is available
docker compose -f docker-compose.prod.yml pull || true
docker compose -f docker-compose.prod.yml build --pull
docker compose -f docker-compose.prod.yml up -d

echo "Deployment finished. Check logs: docker compose -f docker-compose.prod.yml logs -f urban_tour_bot"
