from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional

from sheets import extract_leadgen_plan_fact_single_sheet, compute_plan_to_date


def _pct_percent(delta: float, base: float) -> Optional[float]:
    if base == 0:
        return None
    return (delta / base) * 100.0


def build_leadgen_rows() -> List[Dict[str, Any]]:
    """
    Простая модель:
    - Plan (месяц): AB/AC/AD
    - PlanToDate (по календарю): для бюджета и заявок
    - Fact MTD: Y/U/X
    - Delta и Delta% (в ПРОЦЕНТАХ, т.е. -3.2 означает -3.2%)
    """
    raw = extract_leadgen_plan_fact_single_sheet()
    today = date.today()

    out: List[Dict[str, Any]] = []

    for r in raw:
        city = r["city"]
        direction = r["direction"]
        plan_level = r["plan_level"]

        fact_spend = r["fact"]["tot_spend"]
        fact_apps = r["fact"]["tot_apps"]
        fact_cpl = r["fact"]["tot_cpl"]

        plan_spend_m = r["plan"]["spend_month"]
        plan_apps_m = r["plan"]["apps_month"]
        plan_cpl_m = r["plan"]["cpl_month"]

        plan_spend_td = compute_plan_to_date(plan_spend_m, today)
        plan_apps_td = compute_plan_to_date(plan_apps_m, today)

        delta_spend = None if (plan_spend_td is None or fact_spend is None) else fact_spend - plan_spend_td
        delta_apps = None if (plan_apps_td is None or fact_apps is None) else fact_apps - plan_apps_td
        delta_cpl = None if (plan_cpl_m is None or fact_cpl is None) else fact_cpl - plan_cpl_m

        delta_spend_pct = None
        if delta_spend is not None and plan_spend_td not in (None, 0):
            delta_spend_pct = _pct_percent(delta_spend, plan_spend_td)

        delta_apps_pct = None
        if delta_apps is not None and plan_apps_td not in (None, 0):
            delta_apps_pct = _pct_percent(delta_apps, plan_apps_td)

        delta_cpl_pct = None
        if delta_cpl is not None and plan_cpl_m not in (None, 0):
            delta_cpl_pct = _pct_percent(delta_cpl, plan_cpl_m)

        out.append({
            "month": r["month"],
            "city": city,
            "direction": direction,
            "plan_level": plan_level,

            "plan_spend_month": plan_spend_m,
            "plan_apps_month": plan_apps_m,
            "plan_cpl_month": plan_cpl_m,

            "plan_spend_to_date": plan_spend_td,
            "plan_apps_to_date": plan_apps_td,

            "fact_spend_mtd": fact_spend,
            "fact_apps_mtd": fact_apps,
            "fact_cpl_mtd": fact_cpl,

            "delta_spend": delta_spend,
            "delta_spend_pct": delta_spend_pct,  # percent number

            "delta_apps": delta_apps,
            "delta_apps_pct": delta_apps_pct,    # percent number

            "delta_cpl": delta_cpl,
            "delta_cpl_pct": delta_cpl_pct,      # percent number
        })

    return out