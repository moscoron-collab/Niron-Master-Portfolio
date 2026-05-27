"""
Remove leftover legacy 'Moss Investments, LLC' monthly total rows from History.

The v1 backfill wrote one combined total row per month (property column =
'Moss Investments, LLC'). v2 replaced that with one row per property, but the
legacy removal in backfill_moss.py couldn't parse those rows' month cells
(stored as Google Sheets date serials such as 45839), so ~30 were left behind
and now shadow the per-property data.

A legacy total is deleted ONLY when the per-property rows for that same month
already cover it — specifically when per-property disbursements for the month
sum to AT LEAST the legacy total. That tolerance lets the apartment's added
Zelle income (which the old total never included) through, while a month that
is actually missing a property sums to LESS and is kept + flagged for review.

Safety:
  * DRY RUN by default — prints a full per-month analysis and changes nothing.
    Set APPLY=yes (workflow input) to actually delete.
  * Never deletes a legacy row for a month with no per-property coverage, or
    where per-property sums to LESS than the legacy total.

Google Sheets only; no AppFolio login.

Run via the "Remove Legacy Moss Totals" workflow (workflow_dispatch).
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
APPLY      = os.environ.get("APPLY", "no").strip().lower() == "yes"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
LEGACY_TOTAL_NAME = "Moss Investments, LLC"
TOL = 0.01


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


def get_sheet_gid(sheets, tab_name):
    meta = _execute(sheets.get(spreadsheetId=SHEET_ID, fields="sheets(properties(sheetId,title))"),
                    "get metadata")
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            return s["properties"]["sheetId"]
    return None


def batch_delete_rows(sheets, gid, row_indices):
    if gid is None or not row_indices:
        return 0
    requests = [{
        "deleteDimension": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": i, "endIndex": i + 1},
        }
    } for i in sorted(set(row_indices), reverse=True)]
    _execute(sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}),
             f"delete {len(requests)} row(s)")
    return len(requests)


def _month_key(value):
    """Normalize a period cell to 'YYYY-MM', including Google Sheets date serials."""
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    try:
        serial = float(s)
        if 30000 <= serial <= 60000:   # sane date-serial range (~1982–2064)
            d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(serial))
            return d.strftime("%Y-%m")
    except ValueError:
        pass
    return None


def _to_float(value):
    s = str(value).strip().replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
    try:
        return float(s)
    except ValueError:
        return None


def _cell(row, i):
    return (row[i] if i < len(row) else "").strip()


def main():
    mode = "APPLY (will delete)" if APPLY else "DRY RUN (no changes)"
    print(f"Removing legacy 'Moss Investments, LLC' totals — mode: {mode}\n")
    sheets = get_sheets_service()
    rows = read_sheet(sheets, "History!A:L")
    print(f"Total rows incl. header: {len(rows)}\n")

    coverage = defaultdict(float)        # ym -> summed per-property disbursement
    coverage_props = defaultdict(set)    # ym -> set of properties present
    legacy = []                          # (idx0, ym, legacy_total, raw_month)
    for idx, row in enumerate(rows):
        if idx == 0:
            continue
        prop = _cell(row, 2)
        if not prop:
            continue
        ym = _month_key(_cell(row, 1))
        if prop == LEGACY_TOTAL_NAME:
            legacy.append((idx, ym, _to_float(_cell(row, 3)), _cell(row, 1)))
        elif ym is not None:
            disb = _to_float(_cell(row, 3))
            if disb is not None:
                coverage[ym] += disb
                coverage_props[ym].add(prop)

    to_delete = []
    keep_flagged = []
    print("=== LEGACY TOTALS ANALYSIS (month | old total | per-property sum | properties) ===")
    for idx, ym, total, raw in sorted(legacy, key=lambda x: (x[1] or "")):
        if ym is None:
            keep_flagged.append((idx, raw, "month unparseable"))
            print(f"  row {idx + 1}: month='{raw}'  UNPARSEABLE  -> KEEP (review)")
            continue
        props = sorted(coverage_props.get(ym, []))
        pp_sum = coverage.get(ym, 0.0)
        covered = bool(props)
        enough = total is not None and pp_sum + TOL >= total
        if covered and enough:
            to_delete.append(idx)
            decision = "DELETE"
        else:
            reason = "no per-property rows" if not covered else f"per-property sum {pp_sum:.2f} < total {total}"
            keep_flagged.append((idx, ym, reason))
            decision = "KEEP"
        total_str = f"{total:.2f}" if total is not None else "?"
        print(f"  row {idx + 1}: {ym}  old={total_str}  per-prop={pp_sum:.2f}  {props}  -> {decision}")

    print(f"\n{'Would delete' if not APPLY else 'Deleting'} {len(to_delete)} legacy total row(s).")
    if keep_flagged:
        print(f"\nKeeping {len(keep_flagged)} legacy row(s) for review:")
        for idx, key, reason in keep_flagged:
            print(f"  row {idx + 1}: {key} — {reason}")

    if not to_delete:
        print("\nNothing to delete.")
        return
    if not APPLY:
        print("\nDRY RUN — nothing changed. Re-run with APPLY=yes to delete the rows marked DELETE.")
        return

    gid = get_sheet_gid(sheets, "History")
    removed = batch_delete_rows(sheets, gid, to_delete)
    print(f"\nDone. Deleted {removed} legacy total row(s).")


if __name__ == "__main__":
    main()
