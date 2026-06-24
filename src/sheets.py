import os
import re
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build

# WRITE access (needed to write reports)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# =========================
# OAuth / Google Sheets API
# =========================

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _secrets_dir() -> Path:
    return _project_root() / ".secrets"


def _credentials_path() -> Path:
    return _secrets_dir() / "credentials.json"


def _token_path() -> Path:
    return _secrets_dir() / "token.json"


def get_sheets_service():
    creds: Optional[Credentials] = None
    token_path = _token_path()
    creds_path = _credentials_path()

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Refresh token is expired/revoked; force new interactive OAuth flow.
                creds = None
        else:
            creds = None

        if not creds or not creds.valid:
            if token_path.exists():
                token_path.unlink()
            if not creds_path.exists():
                raise FileNotFoundError(f"Missing {creds_path}. Put OAuth credentials.json into .secrets/")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("sheets", "v4", credentials=creds)


# =========================
# Helpers
# =========================

RU_MONTHS = {
    1: "СЏРЅРІР°СЂ",
    2: "С„РµРІСЂР°Р»",
    3: "РјР°СЂС‚",
    4: "Р°РїСЂРµР»",
    5: "РјР°Р№",
    6: "РёСЋРЅ",
    7: "РёСЋР»",
    8: "Р°РІРіСѓСЃС‚",
    9: "СЃРµРЅС‚СЏР±СЂ",
    10: "РѕРєС‚СЏР±СЂ",
    11: "РЅРѕСЏР±СЂ",
    12: "РґРµРєР°Р±СЂ",
}


def _norm(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().lower().replace("С‘", "Рµ")


def _to_float(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except:
        try:
            return float(str(x).replace(" ", "").replace(",", "."))
        except:
            return None


def extract_spreadsheet_id(url_or_id: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_or_id)
    return m.group(1) if m else url_or_id.strip()


def get_sheet_title_by_gid(service, spreadsheet_id: str, gid: int) -> str:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in meta.get("sheets", []):
        props = sh.get("properties", {})
        if int(props.get("sheetId", -1)) == int(gid):
            return props.get("title")
    raise ValueError(f"Sheet with gid={gid} not found in spreadsheet {spreadsheet_id}")


import time

def read_range(service, spreadsheet_id: str, sheet_title: str, a1_range: str) -> List[List[Any]]:
    rng = f"{sheet_title}!{a1_range}"
    last_err = None
    for attempt in range(5):
        try:
            resp = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=rng,
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
            return resp.get("values", [])
        except Exception as e:
            last_err = e
            # backoff: 1s, 2s, 4s, 8s, 16s
            time.sleep(2 ** attempt)
    raise last_err


def compute_plan_to_date(plan_month: Optional[float], run_date: Optional[date] = None) -> Optional[float]:
    if plan_month is None or plan_month == 0:
        return None
    d = run_date or date.today()
    days_in_month = monthrange(d.year, d.month)[1]
    return plan_month * (d.day / days_in_month)


def _is_month_label(a: str) -> bool:
    a = _norm(a)
    return any(m in a for m in ["СЏРЅРІР°СЂ", "С„РµРІСЂР°Р»", "РјР°СЂС‚", "Р°РїСЂРµР»", "РјР°Р№", "РёСЋРЅ", "РёСЋР»", "Р°РІРіСѓСЃС‚", "СЃРµРЅС‚СЏР±СЂ", "РѕРєС‚СЏР±СЂ", "РЅРѕСЏР±СЂ", "РґРµРєР°Р±СЂ"])


# =========================
# Leadgen: single sheet plan+fact
# =========================

FACT_PLAN_URL = "https://docs.google.com/spreadsheets/d/1nGv8BecKIpKHmH8xbhtzpln9bte34T-lJ9ZHGvHoUsE/edit#gid=878494629"
FACT_PLAN_GID = 878494629


def extract_leadgen_plan_fact_single_sheet(month_token: Optional[str] = None) -> List[Dict[str, Any]]:
    service = get_sheets_service()
    ssid = extract_spreadsheet_id(FACT_PLAN_URL)
    sheet_title = get_sheet_title_by_gid(service, ssid, FACT_PLAN_GID)

    grid = read_range(service, ssid, sheet_title, "A1:AD4000")

    today = date.today()
    yyyy_mm = f"{today.year:04d}-{today.month:02d}"
    token = month_token or RU_MONTHS[today.month]

    def cell(r, c):
        return grid[r][c] if r < len(grid) and c < len(grid[r]) else None

    COL = {
        "ctx_spend": 4,   # E
        "ctx_apps": 8,    # I
        "ctx_cpl": 11,    # L
        "trg_apps": 14,   # O
        "trg_spend": 15,  # P
        "trg_cpl": 17,    # R
        "tot_apps": 20,   # U
        "tot_cpl": 23,    # X
        "tot_spend": 24,  # Y
        "plan_apps": 27,  # AB
        "plan_spend": 28, # AC
        "plan_cpl": 29,   # AD
    }

    month_row = None
    for r in range(len(grid)):
        a = _norm(cell(r, 0))
        if a and token in a and _is_month_label(a):
            month_row = r
            break
    if month_row is None:
        raise ValueError(f"Month '{token}' not found in column A (gid={FACT_PLAN_GID}).")

    out: List[Dict[str, Any]] = []
    current_city: Optional[str] = None
    current_city_plan = {"apps": None, "spend": None, "cpl": None}

    r = month_row + 1
    while r < len(grid):
        a_raw = cell(r, 0)
        a = _norm(a_raw)

        if a and _is_month_label(a) and token not in a:
            break

        if not a:
            r += 1
            continue

        fact_any = any(
            _to_float(cell(r, COL[k])) is not None
            for k in ["ctx_spend", "ctx_apps", "trg_spend", "trg_apps", "tot_spend", "tot_apps"]
        )

        row_plan_apps = _to_float(cell(r, COL["plan_apps"]))
        row_plan_spend = _to_float(cell(r, COL["plan_spend"]))
        row_plan_cpl = _to_float(cell(r, COL["plan_cpl"]))
        row_has_plan = any(v is not None for v in [row_plan_apps, row_plan_spend, row_plan_cpl])

        if not fact_any:
            current_city = str(a_raw).strip()
            if row_has_plan:
                current_city_plan = {"apps": row_plan_apps, "spend": row_plan_spend, "cpl": row_plan_cpl}
            r += 1
            continue

        if not current_city:
            r += 1
            continue

        direction = str(a_raw).strip()

        if row_has_plan:
            plan = {"apps_month": row_plan_apps, "spend_month": row_plan_spend, "cpl_month": row_plan_cpl}
            plan_level = "direction"
        elif any(v is not None for v in current_city_plan.values()):
            plan = {"apps_month": current_city_plan["apps"], "spend_month": current_city_plan["spend"], "cpl_month": current_city_plan["cpl"]}
            plan_level = "city"
        else:
            plan = {"apps_month": None, "spend_month": None, "cpl_month": None}
            plan_level = "missing"

        out.append({
            "month": yyyy_mm,
            "city": current_city,
            "direction": direction,
            "plan_level": plan_level,
            "plan": plan,
            "fact": {
                "tot_spend": _to_float(cell(r, COL["tot_spend"])),
                "tot_apps": _to_float(cell(r, COL["tot_apps"])),
                "tot_cpl": _to_float(cell(r, COL["tot_cpl"])),

                "ctx_spend": _to_float(cell(r, COL["ctx_spend"])),
                "ctx_apps": _to_float(cell(r, COL["ctx_apps"])),
                "ctx_cpl": _to_float(cell(r, COL["ctx_cpl"])),

                "trg_spend": _to_float(cell(r, COL["trg_spend"])),
                "trg_apps": _to_float(cell(r, COL["trg_apps"])),
                "trg_cpl": _to_float(cell(r, COL["trg_cpl"])),
            }
        })

        r += 1

    return out


# =========================
# Reporting: write Leadgen to separate report spreadsheet
# =========================

def _rgb(r: float, g: float, b: float) -> dict:
    return {"red": r, "green": g, "blue": b}


def ensure_sheet(service, spreadsheet_id: str, title: str) -> int:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in meta.get("sheets", []):
        props = sh.get("properties", {})
        if props.get("title") == title:
            return int(props["sheetId"])

    resp = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()
    return int(resp["replies"][0]["addSheet"]["properties"]["sheetId"])


def clear_sheet(service, spreadsheet_id: str, sheet_title: str):
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"{sheet_title}!A:ZZ", body={}
    ).execute()


def write_values(service, spreadsheet_id: str, sheet_title: str, values: List[List[Any]]):
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_title}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def apply_header_format(service, spreadsheet_id: str, sheet_id: int, n_cols: int):
    reqs = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": n_cols},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "backgroundColor": _rgb(0.95, 0.95, 0.95)}},
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
    ]
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": reqs}).execute()


def clear_conditional_rules(service, spreadsheet_id: str, sheet_id: int):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_meta = None
    for sh in meta.get("sheets", []):
        if int(sh["properties"]["sheetId"]) == int(sheet_id):
            sheet_meta = sh
            break
    if not sheet_meta or not sheet_meta.get("conditionalFormats"):
        return

    count = len(sheet_meta["conditionalFormats"])
    reqs = [{"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}} for _ in range(count)]
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": reqs}).execute()


def export_leadgen_to_report_sheet(service, rows: List[Dict[str, Any]]) -> str:
    """
    Writes Leadgen report into separate spreadsheet specified by REPORT_SHEETS_URL env var.
    DeltaPct stored as percent number (e.g. -3.2 means -3.2%).
    """
    report_url = os.getenv("REPORT_SHEETS_URL")
    if not report_url:
        raise RuntimeError("REPORT_SHEETS_URL is missing in .env (link to your KPI REPORT spreadsheet)")

    report_spreadsheet_id = extract_spreadsheet_id(report_url)
    sheet_title = "Leadgen"

    sheet_id = ensure_sheet(service, report_spreadsheet_id, sheet_title)
    clear_sheet(service, report_spreadsheet_id, sheet_title)

    def r1(x):
        return None if x is None else round(float(x), 1)

    header = [
        "month", "city", "direction", "plan_level",
        "Budget_PlanToDate", "Budget_Fact", "Budget_Delta", "Budget_DeltaPct(%)",
        "Leads_PlanToDate", "Leads_Fact", "Leads_Delta", "Leads_DeltaPct(%)",
        "CPL_Plan", "CPL_Fact", "CPL_Delta", "CPL_DeltaPct(%)",
        "NO_PLAN_FLAG",
    ]

    values: List[List[Any]] = [header]

    for r in rows:
        no_plan = (
            r.get("plan_level") == "missing"
            or (r.get("plan_spend_month") in (None, 0) and r.get("plan_apps_month") in (None, 0) and r.get("plan_cpl_month") in (None, 0))
        )

        values.append([
            r.get("month"),
            r.get("city"),
            r.get("direction"),
            r.get("plan_level"),

            r1(r.get("plan_spend_to_date")),
            r1(r.get("fact_spend_mtd")),
            r1(r.get("delta_spend")),
            r1(r.get("delta_spend_pct")),  # % number

            r1(r.get("plan_apps_to_date")),
            r1(r.get("fact_apps_mtd")),
            r1(r.get("delta_apps")),
            r1(r.get("delta_apps_pct")),   # % number

            r1(r.get("plan_cpl_month")),
            r1(r.get("fact_cpl_mtd")),
            r1(r.get("delta_cpl")),
            r1(r.get("delta_cpl_pct")),    # % number

            "NO_PLAN" if no_plan else "",
        ])

    write_values(service, report_spreadsheet_id, sheet_title, values)
    apply_header_format(service, report_spreadsheet_id, sheet_id, len(header))

    n_rows = len(values)
    start_row = 1
    end_row = n_rows

    clear_conditional_rules(service, report_spreadsheet_id, sheet_id)

    # Batch: number formats + conditional formatting
    def repeat_format(col_start, col_end, fmt_type, pattern):
        return {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": n_rows,
                    "startColumnIndex": col_start,
                    "endColumnIndex": col_end,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": fmt_type, "pattern": pattern}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }

    def rng(col):
        return {
            "sheetId": sheet_id,
            "startRowIndex": start_row,
            "endRowIndex": end_row,
            "startColumnIndex": col,
            "endColumnIndex": col + 1,
        }

def rule_number(col, cond_type, val, color):
    # normalize to Google Sheets enum names
    mapping = {
        "NUMBER_LESS_THAN": "NUMBER_LESS",
        "NUMBER_GREATER_THAN": "NUMBER_GREATER",
    }
    cond_type = mapping.get(cond_type, cond_type)

    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [rng(col)],
                "booleanRule": {
                    "condition": {"type": cond_type, "values": [{"userEnteredValue": str(val)}]},
                    "format": {"backgroundColor": color},
                },
            },
            "index": 0,
        }
    }

    def rule_text(col, text, color):
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [rng(col)],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": text}]},
                        "format": {"backgroundColor": color},
                    },
                },
                "index": 0,
            }
        }

    red = _rgb(0.95, 0.60, 0.60)
    yellow = _rgb(0.98, 0.88, 0.55)
    green = _rgb(0.70, 0.90, 0.70)

    requests = [
        # number formats: 1 decimal; delta% as 0.0"%"
        repeat_format(4, 7, "NUMBER", "0.0"),
        repeat_format(8, 11, "NUMBER", "0.0"),
        repeat_format(12, 15, "NUMBER", "0.0"),
        repeat_format(7, 8, "NUMBER", '0.0"%"'),
        repeat_format(11, 12, "NUMBER", '0.0"%"'),
        repeat_format(15, 16, "NUMBER", '0.0"%"'),

        # Budget_DeltaPct col=7: red <= -3, yellow >= +3
        rule_number(7, "NUMBER_LESS_THAN_EQ", -3, red),
        rule_number(7, "NUMBER_GREATER", 3, yellow),

        rule_number(11, "NUMBER_LESS", -5, red),
rule_number(11, "NUMBER_GREATER", 5, green),

rule_number(15, "NUMBER_GREATER", 10, red),
rule_number(15, "NUMBER_LESS", 0, green),

        # NO_PLAN_FLAG col=16 -> yellow
        rule_text(16, "NO_PLAN", yellow),
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=report_spreadsheet_id,
        body={"requests": requests},
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{report_spreadsheet_id}/edit"
def export_traffic_to_report_sheet(service, traffic_rows: List[Dict[str, Any]]) -> str:
    report_url = os.getenv("REPORT_SHEETS_URL")
    if not report_url:
        raise RuntimeError("REPORT_SHEETS_URL is missing in .env (link to your KPI REPORT spreadsheet)")

    report_spreadsheet_id = extract_spreadsheet_id(report_url)
    sheet_title = "Traffic"

    sheet_id = ensure_sheet(service, report_spreadsheet_id, sheet_title)
    clear_sheet(service, report_spreadsheet_id, sheet_title)

    def r1(x):
        return None if x is None else round(float(x), 1)

    month_keys = sorted(
        {mk for r in traffic_rows for mk in (r.get("facts") or {}).keys()}
    )

    current_month_key = ""
    if traffic_rows:
        current_month_key = str(traffic_rows[0].get("month") or "")

    header = ["Месяц", "Город", "Зона", "Годовой_план"]
    header += [f"Факт_{mk}" for mk in month_keys]
    header += [
        f"Факт_{current_month_key}_MTD" if current_month_key else "Факт_текущий_MTD",
        f"План_{current_month_key}_месяц" if current_month_key else "План_текущий_месяц",
        f"План_{current_month_key}_к_дате" if current_month_key else "План_текущий_к_дате",
        "Дельта", "Дельта_процент(%)",
        "Остаток_до_года", "Осталось_месяцев", "Базовый_прирост_AJ",
        "НЕТ_ПЛАНА", "НЕТ_ДАННЫХ",
        "Выполнение_годовой_цели_прогноз(%)",
    ]

    values = [header]

    for r in traffic_rows:
        facts = r.get("facts") or {}
        row = [
            r.get("month"),
            r.get("city"),
            r.get("zone"),
            r1(r.get("annual_target")),
        ]
        row += [r1(facts.get(mk)) for mk in month_keys]
        row += [
            r1(r.get("fact_current_mtd")),
            r1(r.get("plan_current_month")),
            r1(r.get("plan_to_date")),
            r1(r.get("delta")),
            r1(r.get("delta_pct")),
            r1(r.get("remaining_target")),
            r1(r.get("months_left")),
            r1(r.get("base_growth_aj")),
            "НЕТ_ПЛАНА" if r.get("no_plan") else "",
            "НЕТ_ДАННЫХ" if r.get("no_counter") else "",
            r1(r.get("annual_goal_pct")),
        ]
        values.append(row)

    write_values(service, report_spreadsheet_id, sheet_title, values)
    apply_header_format(service, report_spreadsheet_id, sheet_id, len(header))

    n_rows = len(values)
    clear_conditional_rules(service, report_spreadsheet_id, sheet_id)

    red = _rgb(0.95, 0.60, 0.60)
    green = _rgb(0.70, 0.90, 0.70)
    yellow = _rgb(0.98, 0.88, 0.55)

    def repeat_format(col_start, col_end, fmt_type, pattern):
        return {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": n_rows,
                    "startColumnIndex": col_start,
                    "endColumnIndex": col_end,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": fmt_type, "pattern": pattern}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }

    def rng(col):
        return {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "endRowIndex": n_rows,
            "startColumnIndex": col,
            "endColumnIndex": col + 1,
        }

    def rule_number(col, cond_type, val, color):
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [rng(col)],
                    "booleanRule": {
                        "condition": {"type": cond_type, "values": [{"userEnteredValue": str(val)}]},
                        "format": {"backgroundColor": color},
                    },
                },
                "index": 0,
            }
        }

    def rule_text(col, text, color):
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [rng(col)],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": text}]},
                        "format": {"backgroundColor": color},
                    },
                },
                "index": 0,
            }
        }

    # Locate dynamic indices in header
    idx_delta_pct = header.index("Дельта_процент(%)")
    idx_no_plan = header.index("НЕТ_ПЛАНА")
    idx_no_data = header.index("НЕТ_ДАННЫХ")
    idx_annual_goal_pct = header.index("Выполнение_годовой_цели_прогноз(%)")

    requests = [
        repeat_format(3, len(header), "NUMBER", "0.0"),
        repeat_format(idx_delta_pct, idx_delta_pct + 1, "NUMBER", '0.0"%"'),
        repeat_format(idx_annual_goal_pct, idx_annual_goal_pct + 1, "NUMBER", '0.0"%"'),
        rule_number(idx_delta_pct, "NUMBER_LESS_THAN_EQ", -3, red),
        rule_number(idx_delta_pct, "NUMBER_GREATER_THAN_EQ", 3, green),
        # Same zone logic around annual goal 100%: <=97 red, >=103 green.
        rule_number(idx_annual_goal_pct, "NUMBER_LESS_THAN_EQ", 97, red),
        rule_number(idx_annual_goal_pct, "NUMBER_GREATER_THAN_EQ", 103, green),
        rule_text(idx_no_plan, "НЕТ_ПЛАНА", yellow),
        rule_text(idx_no_data, "НЕТ_ДАННЫХ", yellow),
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=report_spreadsheet_id,
        body={"requests": requests},
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{report_spreadsheet_id}/edit"
