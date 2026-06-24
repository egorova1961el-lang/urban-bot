from __future__ import annotations

import json
import os
import time
from calendar import monthrange
from datetime import date, timedelta
from typing import List, Tuple

import requests

API_URL = "https://key-indicators.data-etagi.ru/reports/data"
PERMISSION_CODE = "site_summary"
REPORT_TYPE = "visits"


def normalize_city(city: str) -> str:
    return str(city or "").strip().lower().replace("ё", "е")


def _token() -> str:
    token = os.getenv("KEY_INDICATORS_TOKEN")
    if not token:
        raise RuntimeError("KEY_INDICATORS_TOKEN is missing in .env")
    return token


def _request_with_retry(url: str, headers: dict, params: dict, timeout: int = 60) -> requests.Response:
    last_err = None
    for attempt in range(6):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(2 ** attempt, 30)
                time.sleep(wait)
                last_err = RuntimeError(f"HTTP {r.status_code}: {r.text}")
                continue
            return r
        except Exception as e:
            last_err = e
            wait = min(2 ** attempt, 30)
            time.sleep(wait)
    raise RuntimeError(f"Facts API request failed after retries: {last_err}")


def _query_visits_series(city: str, date1: date, date2: date, group: str = "day") -> Tuple[List[str], List[float]]:
    headers = {"Authorization": f"Bearer {_token()}"}
    params = {
        "date1": date1.isoformat(),
        "date2": date2.isoformat(),
        "group": group,
        "cities": json.dumps([city], ensure_ascii=False),
        "permission_code": PERMISSION_CODE,
        "type": REPORT_TYPE,
    }
    r = _request_with_retry(API_URL, headers=headers, params=params, timeout=90)
    if r.status_code >= 400:
        raise RuntimeError(f"Facts API error {r.status_code}: {r.text}")

    js = r.json()
    labels = js.get("labels") or []
    datasets = js.get("datasets") or []
    data = (datasets[0].get("data") if datasets else []) or []

    if len(labels) != len(data):
        n = min(len(labels), len(data))
        labels = labels[:n]
        data = data[:n]

    return labels, [float(x or 0) for x in data]


def _sum_day_series_in_range(city: str, start: date, end: date) -> float:
    if end < start:
        return 0.0
    _, data = _query_visits_series(city, start, end, group="day")
    return float(sum(data))


def get_city_visits_mtd_full_days(city: str, d: date | None = None) -> float:
    d = d or date.today()
    if d.day == 1:
        return 0.0

    start = d.replace(day=1)
    end = d - timedelta(days=1)
    return _sum_day_series_in_range(city, start, end)


def get_city_visits_month_total(city: str, year: int, month: int) -> float:
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    return _sum_day_series_in_range(city, start, end)
