"""
Read-only audit of the Moss History tab — finds duplicate rows.

Groups every History row by (property, month) and reports any group with more
than one row, plus any legacy single-total "Moss Investments, LLC" rows left
over from the v1 backfill, plus any rows whose month can't be parsed. Prints
the disbursement, net, source, timestamp, and the 1-based sheet row number for
each, so a precise cleanup can be planned.

WRITES NOTHING — Google Sheets read only, no AppFolio login. Safe to run anytime.

Run via the "Audit Moss History — Duplicates" workflow (workflow_dispatch).
"""

import os
import re
import json
import time
import datetime
from collections import defaultdict

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SHEET_ID   = os.environ["MOSS_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LEGACY_TOTAL_NAME = "Moss Investments, LLC"


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


def _period_to_ym(period_val):
    period = str(period_val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(period, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", period)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _cell(row, i):
    return row[i] if i < len(row) else ""


def main():
    print("Auditing Moss History for duplicates (READ-ONLY — nothing is changed)...\n")
    sheets = get_sheets_service()
    rows = read_sheet(sheets, "History!A:L")
    print(f"Total rows incl. header: {len(rows)}\n")

    groups = defaultdict(list)   # (property, 'YYYY-MM') -> [(sheet_row_no, row), ...]
    legacy = []                  # legacy 'Moss Investments, LLC' total rows
    undated = []                 # rows whose month couldn't be parsed
    for idx, row in enumerate(rows):
        if idx == 0:
            continue  # header
        sheet_row_no = idx + 1   # 1-based row number as shown in the sheet
        prop = _cell(row, 2).strip()
        ym = _period_to_ym(_cell(row, 1))
        if not prop and ym is None:
            continue  # blank row
        if prop == LEGACY_TOTAL_NAME:
            legacy.append((sheet_row_no, row))
        elif ym is None:
            undated.append((sheet_row_no, row))
        else:
            groups[(prop, ym)].append((sheet_row_no, row))

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    excess = sum(len(v) - 1 for v in dup_groups.values())

    print(f"Distinct (property, month) combinations: {len(groups)}")
    print(f"Duplicated combinations:                 {len(dup_groups)}")
    print(f"Excess rows (duplicates beyond the first): {excess}")
    print(f"Legacy 'Moss Investments, LLC' rows:     {len(legacy)}")
    print(f"Rows with unparseable month:             {len(undated)}\n")

    if dup_groups:
        print("=== DUPLICATES (property | month) ===")
        for key in sorted(dup_groups.keys()):
            prop, ym = key
            entries = dup_groups[key]
            print(f"\n{prop} | {ym}  ({len(entries)} rows):")
            for sheet_row_no, row in entries:
                print(f"  row {sheet_row_no}: disb={_cell(row, 3)}  net={_cell(row, 9)}  "
                      f"src='{_cell(row, 10)}'  ts='{_cell(row, 11)}'")

    if legacy:
        print("\n=== LEGACY TOTAL ROWS (Moss Investments, LLC) ===")
        for sheet_row_no, row in legacy:
            print(f"  row {sheet_row_no}: month={_cell(row, 1)}  disb={_cell(row, 3)}  "
                  f"net={_cell(row, 9)}  src='{_cell(row, 10)}'")

    if undated:
        print("\n=== ROWS WITH UNPARSEABLE MONTH ===")
        for sheet_row_no, row in undated:
            print(f"  row {sheet_row_no}: A='{_cell(row, 0)}'  B='{_cell(row, 1)}'  C='{_cell(row, 2)}'")

    print("\nDone (read-only — nothing changed).")


if __name__ == "__main__":
    main()
