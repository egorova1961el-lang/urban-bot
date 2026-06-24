# AGENTS.md
# Plan vs Fact Deviation Agent
# Phase 1: Лидогенерация + Посещаемость сайта (Yandex Metrika)

---

## 1. Purpose

Build and run an automated agent that:

- Twice per week (Tuesday & Thursday)
- Compares Plan vs Fact
- Calculates deviations
- Sends a Telegram summary
- Generates a detailed shareable Google Sheet report

Timezone: Europe/Amsterdam  
Scope: Current month-to-date (MTD)

Phase 1 blocks:
- Лидогенерация
- Посещаемость сайта

Future blocks:
- Агрегаторы
- Офлайн реклама
- Монетизация

---

## 2. Scheduling

Codex does NOT schedule runs.

Use:
- Windows Task Scheduler
OR
- WSL cron

Run days:
- Tuesday
- Thursday

---

# ===============================
# SECTION A — LEAD GENERATION
# ===============================

## 3. Data Sources

### 3.1 Media Plan Registry

URL:
https://docs.google.com/spreadsheets/d/1G4JnbJ1_XJPcwaw__LGDG3PLmMqBE35RNaVQrRoqRUs/edit?gid=2002470426#gid=2002470426

Structure:
- Column A → City
- Column B → Link to city media plan spreadsheet

---

### 3.2 City Media Plans

Each city link contains:
- Separate sheet per month
- Sheet name contains Russian month name (e.g., "февраль")

Inside month sheet:
- Blocks:
  - Контекст
  - Таргет
- Column A → Direction (новостройки, вторичная покупатель, etc.)
- Metrics per block:
  - "Заявки"
  - "Ст-сть заявки"
  - "Бюджет"

---

### 3.3 Facts File

URL:
https://docs.google.com/spreadsheets/d/1nGv8BecKIpKHmH8xbhtzpln9bte34T-lJ9ZHGvHoUsE/edit?gid=878494629#gid=878494629

Structure:

Column A contains hierarchy:
- Year (e.g., 2026)
- Month (e.g., февраль)
- City (e.g., Тюмень)
- Directions below city

Facts are cumulative month-to-date (updated weekly).

Metrics:

Контекст:
- Заявки яндекс
- Ст-сть заявки контекст
- Яндекс расход

Таргет:
- Заявки таргет
- Стоимость заявки таргет
- Расход таргет

Итого:
- Заявки вместе
- Стоимость заявки вместе
- Бюджет вместе

---

## 4. Matching Logic

Keys:
- Month (current)
- City
- Direction
- Block (Контекст / Таргет / Итого)

Normalize:
- lower case
- trim spaces
- "ё" → "е"

If fact exists but no plan:
- Status = YELLOW
- Label = "NO PLAN"

---

## 5. Plan-to-Date Calculation

Let:
- D = current day of month
- N = number of days in month

For Budget and Applications:
PlanToDate = PlanMonth × (D / N)

CPL:
Compare fact CPL vs monthly plan CPL directly.

---

## 6. KPI Rules — Leadgen

### 6.1 Budget

Delta_pct = (Fact - PlanToDate) / PlanToDate × 100

- RED     → ≤ -3%
- NEUTRAL → -3% < Δ < +3%
- YELLOW  → ≥ +3%

---

### 6.2 Applications

Delta_pct = (Fact - PlanToDate) / PlanToDate × 100

- RED     → < -5%
- NEUTRAL → -5% to +5%
- GREEN   → > +5%

---

### 6.3 CPL

Delta_pct = (FactCPL - PlanCPL) / PlanCPL × 100

- GREEN   → FactCPL < PlanCPL
- NEUTRAL → ≤ +10%
- RED     → > +10%

---

## 7. Aggregation Rules

City totals:
- Spend → sum
- Apps → sum
- CPL → Spend_total / Apps_total

Never average CPL.

---

# ===============================
# SECTION B — SITE VISITS
# ===============================

## 8. Yandex Metrika

Authentication:
Environment variable:

YANDEX_METRIKA_TOKEN

One counter = one city.

Counter matching:
- Title contains city name
- Ignore word "область"
- Case insensitive
- "ё" → "е"

If not found:
- Status = YELLOW
- Label = "NO COUNTER"

---

## 9. Visits Fact

Metric:
visits

Date range:
1st of month → today

No dimensions (total per counter).

---

## 10. Visits Plan Model

Source:
Google Sheet:
https://docs.google.com/spreadsheets/d/1JdTNWlRApsGQPK2w15jDdmNoPvuUWBP71qM712rVlGY/edit

- Column B → City
- Column AG → Annual target
- Column AJ → Monthly growth from March

Baseline:
- February actual visits from Metrika

Plan logic:
- March = February actual + AJ
- Next months incrementally + AJ
- If December ≠ Annual target:
  - scale proportionally

PlanToDate = PlanMonth × (D / N)

---

## 11. KPI Rules — Visits

Delta_pct = (Fact - PlanToDate) / PlanToDate × 100

- RED     → < -5%
- NEUTRAL → -5% to +5%
- GREEN   → > +5%

---

# ===============================
# SECTION C — OUTPUT
# ===============================

## 12. Telegram Summary Format

ЛИДОГЕНЕРАЦИЯ — YYYY-MM (MTD до DD)

City:
- Бюджет (ИТОГО): status Δ%
- Заявки (ИТОГО): status Δ%
- CPL (ИТОГО): status Δ%

ПОСЕЩАЕМОСТЬ:
- Визиты: status Δ%

ТОП отклонения:
1)
2)
3)

Полный отчет: <link>

---

## 13. Full Report Structure

Google Sheet:
"Leadgen Report — YYYY-MM — YYYY-MM-DD"

Tabs:
- Summary_by_city
- Detail_by_city_direction_block
- Visits
- Mismatches

Include:
- run timestamp
- source URLs

---

## 14. Secrets

Do NOT hardcode.

Use environment variables:
- GOOGLE credentials
- YANDEX_METRIKA_TOKEN
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

.env must NOT be committed.