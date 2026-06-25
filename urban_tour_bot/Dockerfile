FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Do not copy local .env into the image in production. Set env vars in the host/orchestrator.
CMD ["python", "urban_tour_bot/bot.py"]
