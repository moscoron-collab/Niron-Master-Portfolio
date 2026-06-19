"""
One-off cleanup — remove bogus $0 / "System — Backfill" rows from the Moss sheet.

WHY: an older `backfill_moss.py` used `disbursement or 0`, so when a PDF page
failed to parse it wrote a real-looking **$0 row** (e.g. the 2023 "$0.00 /
System — Backfill" Kearney rows for 02–10/2023). Those distort history and — if
a matching browser override exists — can mask correct live data. The writer is
now fixed (it skips un-parseable pages), but the already-written bad rows must be
removed. This script does that SAFELY:

  1. Finds History rows where Owner Disbursement (col D) is blank/0
     AND "Entered By" (col K) contains "Backfill"   (the exact bad-writer signature).
  2. Optional extra filters PROPERTY_FILTER / YEAR_FILTER to narrow further.
  3. DRY RUN by default — prints what it WOULD delete and changes nothing.
  4. Only when CONFIRM_DELETE=YES: copies every matched row to a brand-new
     backup tab (History_Backup_<timestamp>) FIRST, then deletes them from
     History (bottom-up so indices don't shift).

Run via GitHub Actions (cleanup_moss_zero_rows.yml). Set CONFIRM_DELETE=YES on
the workflow_dispatch input ONLY after reviewing the dry-run output.

Env:
  MOSS_SHEET_ID, GOOGLE_CREDENTIALS_JSON   (same secrets as run_moss.py)
  CONFIRM_DELETE=YES        — actually back up + delete (else dry run)
  PROPERTY_FILTER           — optional substring of col C (e.g. "Kearney")
  YEAR_FILTER               — optional 4-digit year of col B (e.g. "2023")
"""

import os
import json
import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID   = os.environ["MOSS_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

CONFIRM         = os.environ.get("CONFIRM_DELETE", "").strip().upper() == "YES"
PROPERTY_FILTER = os.environ.get("PROPERTY_FILTER", "").strip()
YEAR_FILTER     = os.environ.get("YEAR_FILTER", "").strip()

# Only ever touch rows whose "Entered By" contains this (the bad-writer signature).
ENTEREDBY_MATCH = "backfill"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# History column layout (0-based): D=disbursement(3), C=property(2), B=month(1), K=enteredby(10)
COL_MONTH, COL_PROP, COL_DISB, COL_ENTEREDBY = 1, 2, 3, 10


def get_sheets():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def get_gid(sheets, tab_name):
    meta = sheets.get(spreadsheetId=SHEET_ID,
                      fields="sheets(properties(sheetId,title))").execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            return s["properties"]["sheetId"]
    return None


def _is_zero_or_blank(value):
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        return True
    try:
        return float(s) == 0.0
    except ValueError:
        return False


def _year_of(value):
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y")
        except ValueError:
            continue
    return s[:4] if len(s) >= 4 and s[:4].isdigit() else ""


def main():
    sheets = get_sheets()
    rows = sheets.values().get(spreadsheetId=SHEET_ID, range="History!A:L").execute().get("values", [])
    print(f"Read {len(rows)} History rows (incl. header).")

    matched = []  # (0-based sheet row index, the row values)
    for idx, row in enumerate(rows):
        if idx == 0 or len(row) <= COL_ENTEREDBY:
            continue
        entered_by = str(row[COL_ENTEREDBY]).strip().lower()
        if ENTEREDBY_MATCH not in entered_by:
            continue
        if not _is_zero_or_blank(row[COL_DISB] if len(row) > COL_DISB else ""):
            continue
        if PROPERTY_FILTER and PROPERTY_FILTER.lower() not in str(row[COL_PROP]).lower():
            continue
        if YEAR_FILTER and _year_of(row[COL_MONTH]) != YEAR_FILTER:
            continue
        matched.append((idx, row))

    print(f"\nMatched {len(matched)} bogus $0 / backfill row(s):")
    for idx, row in matched:
        prop = row[COL_PROP] if len(row) > COL_PROP else ""
        month = row[COL_MONTH] if len(row) > COL_MONTH else ""
        disb = row[COL_DISB] if len(row) > COL_DISB else ""
        print(f"  sheet row {idx + 1}: {month} | {prop} | Disb='{disb}' | {row[COL_ENTEREDBY]}")

    if not matched:
        print("\nNothing to clean. Done.")
        return

    if not CONFIRM:
        print("\nDRY RUN — set CONFIRM_DELETE=YES to back up + delete these rows. "
              "Nothing was changed.")
        return

    # 1) Back up matched rows to a new tab FIRST.
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_tab = f"History_Backup_{stamp}"
    sheets.batchUpdate(spreadsheetId=SHEET_ID, body={
        "requests": [{"addSheet": {"properties": {"title": backup_tab}}}]
    }).execute()
    header = rows[0] if rows else []
    backup_values = [header] + [row for _, row in matched]
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{backup_tab}'!A1",
        valueInputOption="RAW",
        body={"values": backup_values},
    ).execute()
    print(f"\nBacked up {len(matched)} row(s) (+ header) to new tab '{backup_tab}'.")

    # 2) Delete them from History, bottom-up so indices don't shift.
    gid = get_gid(sheets, "History")
    if gid is None:
        print("ERROR: could not resolve History sheetId — aborting before delete. "
              "Your backup tab is safe; no rows were deleted.")
        return
    requests = [{
        "deleteDimension": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": i, "endIndex": i + 1}
        }
    } for i, _ in sorted(matched, key=lambda t: t[0], reverse=True)]
    sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}).execute()
    print(f"Deleted {len(requests)} row(s) from History. "
          f"(Backup kept in '{backup_tab}'.) Done.")


if __name__ == "__main__":
    main()
