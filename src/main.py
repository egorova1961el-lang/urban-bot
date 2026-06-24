from pathlib import Path
from dotenv import load_dotenv
import os

# Р“Р РЈР—РРњ .env РЎР РђР—РЈ
root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")

print("ENV LOADED:", root / ".env")
print("FACTS API TOKEN PRESENT:", bool(os.getenv("KEY_INDICATORS_TOKEN")))

from sheets import (
    get_sheets_service,
    # export_leadgen_to_report_sheet,
    export_traffic_to_report_sheet,
)
# from leadgen import build_leadgen_rows
from traffic import build_traffic_rows


def main():
    print("START")

    service = get_sheets_service()
    print("Sheets OK")

    # leadgen_rows = build_leadgen_rows()
    # print("Leadgen OK")

    traffic_rows = build_traffic_rows()
    print("Traffic OK")

    # url = export_leadgen_to_report_sheet(service, leadgen_rows)
    # print("Leadgen exported")

    url = export_traffic_to_report_sheet(service, traffic_rows)
    print("Traffic exported")

    print("DONE:", url)


if __name__ == "__main__":
    main()
