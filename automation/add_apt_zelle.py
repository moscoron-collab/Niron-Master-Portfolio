"""
One-off manual entry — MOSS: 1959 S Kearney Way Apt (Zelle months Jan–Jun 2025).

The apartment was rented Jan–Jun 2025 with rent paid to the owner directly by
Zelle, so it never appeared on the AppFolio Owner Packets for those months
(their Consolidated Summary lists only 3 properties). Starting with the Jul 2025
statement a new tenant moved in and the apartment joined AppFolio (summary then
shows 4 properties), so from 2025-07 on it is parsed normally by run_moss.py /
backfill_moss.py.

This writes the 6 missing Zelle months to History as $1,850 net manual rows.
Idempotent: any apt month already present is skipped, so re-running is safe.
Touches Google Sheets only — no AppFolio login.

Run via the "Add Apt Zelle Months — Moss" workflow (workflow_dispatch).
"""

import os
import re
import json
import time
import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SHEET_ID   = os.environ["MOSS_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Canonical name must match PROPERTY_NAME_MAP in run_moss.py and the dashboard's
# propertyIdFromLlc() resolver — do not change without updating both.
APT_PROPERTY = "1959 S Kearney Way Apt"
APT_NET      = 1850.00
APT_MONTHS   = ["2025-01-01", "2025-02-01", "2025-03-01",
                "2025-04-01", "2025-05-01", "2025-06-01"]


def get_sheets_service():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def _execute(request, what="API call"):
    delay = 2
    for attempt in range(6):
        try:
            return request.execute()
        except HttpError as e:
            status = e.resp.status if getattr(e, "resp", None) is not None else None
            if status in (429, 500, 503) and attempt < 5:
                print(f"  {what}: HTTP {status} — backing off {delay}s (retry {attempt + 1}/5)")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def read_sheet(sheets, range_name):
    return _execute(sheets.values().get(spreadsheetId=SHEET_ID, range=range_name),
                    f"read {range_name}").get("values", [])


def append_rows(sheets, tab, rows):
    if not rows:
        return
    _execute(
        sheets.values().append(
            spreadsheetId=SHEET_ID,
            range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ),
        f"append {len(rows)} row(s)",
    )


def _period_to_ym(period_val):
    period = str(period_val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(period, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", period)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def existing_apt_months(sheets):
    rows = read_sheet(sheets, "History!A:C")
    found = set()
    for idx, row in enumerate(rows):
        if idx == 0 or len(row) < 3:
            continue
        if row[2].strip() == APT_PROPERTY:
            ym = _period_to_ym(row[1])
            if ym:
                found.add(ym)
    return found


def main():
    print("Adding 1959 S Kearney Way Apt — Zelle months (Jan–Jun 2025) @ $1,850 net...")
    sheets = get_sheets_service()

    already = existing_apt_months(sheets)
    print(f"Apt months already in History: {sorted(already) or 'none'}")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending = []
    for month_label in APT_MONTHS:
        ym = month_label[:7]
        if ym in already:
            print(f"  {month_label}: already present — skip")
            continue
        label = datetime.datetime.strptime(month_label, "%Y-%m-%d").strftime("%b %Y")
        pending.append([
            f"Zelle (manual) — {label}", month_label, APT_PROPERTY,
            APT_NET, 0,
            0, 0, 0, 0, APT_NET,
            "Manual — Zelle (apt rent, not on AppFolio)", now_str,
        ])
        print(f"  {month_label}: queued ${APT_NET:,.2f}")

    if not pending:
        print("Nothing to add — all 6 months already present.")
        return

    append_rows(sheets, "History", pending)
    print(f"\nDone. Added {len(pending)} apt row(s) to History.")


if __name__ == "__main__":
    main()
