from __future__ import annotations

import json
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from sheets import get_sheets_service, extract_spreadsheet_id, get_sheet_title_by_gid, read_range
from metrika import get_city_visits_mtd_full_days, get_city_visits_month_total, normalize_city

TRAFFIC_PLAN_URL = "https://docs.google.com/spreadsheets/d/1JdTNWlRApsGQPK2w15jDdmNoPvuUWBP71qM712rVlGY/edit?gid=1005222570"
TRAFFIC_PLAN_GID = 1005222570


def _to_float(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(" ", "").replace(",", "."))
        except Exception:
            return None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cache_dir() -> Path:
    p = _project_root() / ".cache"
    p.mkdir(exist_ok=True)
    return p


def _history_path() -> Path:
    return _cache_dir() / "traffic_history.json"


def _load_history() -> Dict[str, Any]:
    p = _history_path()
    if not p.exists():
        return {"cities": {}}
    try:
        js = json.loads(p.read_text(encoding="utf-8"))
        js.setdefault("cities", {})
        return js
    except Exception:
        return {"cities": {}}


def _save_history(history: Dict[str, Any]) -> None:
    _history_path().write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _city_bucket(history: Dict[str, Any], city: str) -> Dict[str, Any]:
    cities = history.setdefault("cities", {})
    key = normalize_city(city)
    b = cities.setdefault(key, {"city": city, "facts": {}})
    if not b.get("city"):
        b["city"] = city
    return b


def _get_fact_month(history: Dict[str, Any], city: str, year: int, month: int) -> float:
    b = _city_bucket(history, city)
    facts = b.setdefault("facts", {})
    mk = _month_key(year, month)
    if mk in facts:
        return float(facts[mk])

    fact = float(get_city_visits_month_total(city, year, month))
    facts[mk] = fact
    return fact


def read_traffic_plan_rows() -> List[Dict[str, Any]]:
    service = get_sheets_service()
    ssid = extract_spreadsheet_id(TRAFFIC_PLAN_URL)
    sheet_title = get_sheet_title_by_gid(service, ssid, TRAFFIC_PLAN_GID)

    # Primary mapping by user instruction: A=city, AG=annual target, AJ=growth note
    # Fallback: if A is 'Россия', use B as city.
    col_a = read_range(service, ssid, sheet_title, "A2:A2000")
    col_b = read_range(service, ssid, sheet_title, "B2:B2000")
    col_ag = read_range(service, ssid, sheet_title, "AG2:AG2000")
    col_aj = read_range(service, ssid, sheet_title, "AJ2:AJ2000")

    n = max(len(col_a), len(col_b), len(col_ag), len(col_aj))
    out: List[Dict[str, Any]] = []

    for i in range(n):
        city_a = ""
        city_b = ""

        if i < len(col_a) and len(col_a[i]) > 0:
            city_a = str(col_a[i][0]).strip()
        if i < len(col_b) and len(col_b[i]) > 0:
            city_b = str(col_b[i][0]).strip()

        city = city_a
        if normalize_city(city_a) == "россия" and city_b:
            city = city_b

        if not city:
            continue

        ag = None
        if i < len(col_ag) and len(col_ag[i]) > 0:
            ag = _to_float(col_ag[i][0])

        aj = None
        if i < len(col_aj) and len(col_aj[i]) > 0:
            aj = _to_float(col_aj[i][0])

        out.append({"city": city, "target_ag": ag, "growth_aj": aj})

    return out


def _zone_by_delta_pct(delta_pct: Optional[float], no_plan: bool, no_data: bool) -> str:
    if no_data:
        return "NO_DATA"
    if no_plan or delta_pct is None:
        return "NO_PLAN"
    if delta_pct >= 3:
        return "GREEN"
    if -3 < delta_pct < 3:
        return "NEUTRAL"
    return "RED"


def _sort_key(row: Dict[str, Any]) -> tuple:
    zone_rank = {
        "GREEN": 0,
        "NEUTRAL": 1,
        "RED": 2,
        "NO_PLAN": 3,
        "NO_DATA": 4,
    }
    dp = row.get("delta_pct")
    dp_val = float(dp) if dp is not None else -999999.0
    return (zone_rank.get(row.get("zone"), 99), -dp_val, normalize_city(row.get("city", "")))


def _zone_from_goal_pct(goal_pct: Optional[float], no_data: bool) -> str:
    if no_data or goal_pct is None:
        return "NO_DATA"
    if goal_pct >= 103:
        return "GREEN"
    if goal_pct <= 97:
        return "RED"
    return "NEUTRAL"


def build_traffic_rows() -> List[Dict[str, Any]]:
    d = date.today()
    year = d.year
    current_month = d.month
    current_key = _month_key(year, current_month)
    days_in_month = monthrange(year, current_month)[1]
    elapsed_full_days = max(d.day - 1, 0)

    plans = read_traffic_plan_rows()
    history = _load_history()

    out: List[Dict[str, Any]] = []

    for p in plans:
        city = p["city"]
        annual_target = p.get("target_ag")
        base_growth = p.get("growth_aj")

        facts_by_month: Dict[str, Optional[float]] = {}
        completed_sum = 0.0
        completed_known = True

        for m in range(1, current_month):
            mk = _month_key(year, m)
            try:
                fact_m = _get_fact_month(history, city, year, m)
                facts_by_month[mk] = fact_m
                completed_sum += fact_m
            except Exception:
                facts_by_month[mk] = None
                completed_known = False

        months_left = 12 - (current_month - 1)
        remaining_target = None
        plan_current_month = None
        plan_to_date = None

        if annual_target is not None and completed_known and months_left > 0:
            remaining_target = annual_target - completed_sum
            plan_current_month = remaining_target / months_left
            if elapsed_full_days == 0:
                plan_to_date = 0.0
            else:
                plan_to_date = plan_current_month * (elapsed_full_days / days_in_month)

        no_data = False
        try:
            fact_current_mtd = float(get_city_visits_mtd_full_days(city, d))
        except Exception:
            fact_current_mtd = None
            no_data = True

        delta = None
        delta_pct = None
        if plan_to_date is not None and fact_current_mtd is not None:
            delta = fact_current_mtd - plan_to_date
            if plan_to_date != 0:
                delta_pct = (delta / plan_to_date) * 100.0

        no_plan = plan_current_month is None
        zone = _zone_by_delta_pct(delta_pct, no_plan, no_data)

        # Annual goal projection from current factual daily pace:
        # forecast_year = (YTD factual for full days / elapsed full days in year) * days_in_year
        year_days = 366 if monthrange(year, 2)[1] == 29 else 365
        elapsed_days_year = (d - date(year, 1, 1)).days  # full days before today
        annual_forecast = None
        annual_goal_pct = None
        annual_goal_delta_pct = None
        annual_goal_zone = "NO_DATA"
        if (
            annual_target not in (None, 0)
            and completed_known
            and fact_current_mtd is not None
            and elapsed_days_year > 0
        ):
            ytd_fact_full_days = completed_sum + fact_current_mtd
            annual_forecast = (ytd_fact_full_days / elapsed_days_year) * year_days
            annual_goal_pct = (annual_forecast / annual_target) * 100.0
            annual_goal_delta_pct = annual_goal_pct - 100.0
            annual_goal_zone = _zone_from_goal_pct(annual_goal_pct, False)
        elif no_data:
            annual_goal_zone = "NO_DATA"

        out.append(
            {
                "month": current_key,
                "city": city,
                "annual_target": annual_target,
                "facts": facts_by_month,
                "fact_current_mtd": fact_current_mtd,
                "plan_current_month": plan_current_month,
                "plan_to_date": plan_to_date,
                "delta": delta,
                "delta_pct": delta_pct,
                "remaining_target": remaining_target,
                "months_left": months_left,
                "base_growth_aj": base_growth,
                "zone": zone,
                "annual_forecast": annual_forecast,
                "annual_goal_pct": annual_goal_pct,
                "annual_goal_delta_pct": annual_goal_delta_pct,
                "annual_goal_zone": annual_goal_zone,
                "no_plan": no_plan,
                "no_counter": no_data,
            }
        )

    _save_history(history)
    out.sort(key=_sort_key)
    return out
