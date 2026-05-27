"""
De-duplicate the Moss History tab — removes repeated (property, month) rows.

The monthly automation runs daily (15th–25th). A date-format mismatch in the
old already_recorded() dedup meant each daily run appended another identical
row instead of skipping it, so some months accumulated several copies. This
keeps the first row of each (property, month) and deletes the later EXACT
duplicates (same disbursement and net).

Safety:
  * DRY RUN by default — prints what it would delete and changes nothing.
    Set APPLY=yes (workflow input) to actually delete.
  * Only deletes rows whose disbursement AND net match the kept row exactly.
    A (property, month) with DIFFERING values is reported for manual review
    and left untouched.
  * Ignores legacy 'Moss Investments, LLC' total rows and any row whose month
    can't be parsed — those are handled separately.

Google Sheets only; no AppFolio login.

Run via the "Deduplicate Moss History" workflow (workflow_dispatch).
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
    """Delete the given 0-based row indices in one batchUpdate (bottom-up)."""
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
    return (row[i] if i < len(row) else "").strip()


def main():
    mode = "APPLY (will delete)" if APPLY else "DRY RUN (no changes)"
    print(f"Deduplicating Moss History — mode: {mode}\n")
    sheets = get_sheets_service()
    rows = read_sheet(sheets, "History!A:L")
    print(f"Total rows incl. header: {len(rows)}")

    groups = defaultdict(list)   # (property, 'YYYY-MM') -> [(idx0, disb, net, ts), ...]
    for idx, row in enumerate(rows):
        if idx == 0:
            continue
        prop = _cell(row, 2)
        ym = _period_to_ym(_cell(row, 1))
        if not prop or prop == LEGACY_TOTAL_NAME or ym is None:
            continue  # legacy totals / unparseable months handled separately
        groups[(prop, ym)].append((idx, _cell(row, 3), _cell(row, 9), _cell(row, 11)))

    to_delete = []   # (idx0, property, ym, disb)
    differing = []   # (property, ym) groups with mismatched values — left alone
    for key in sorted(groups.keys()):
        entries = groups[key]
        if len(entries) < 2:
            continue
        keep_idx, keep_disb, keep_net, _ = entries[0]
        prop, ym = key
        for idx, disb, net, ts in entries[1:]:
            if disb == keep_disb and net == keep_net:
                to_delete.append((idx, prop, ym, disb))
            else:
                differing.append((prop, ym))

    if differing:
        print("\n=== NEEDS MANUAL REVIEW (same property+month, different values — NOT touched) ===")
        for prop, ym in sorted(set(differing)):
            print(f"  {prop} | {ym}")

    print(f"\n{'Would delete' if not APPLY else 'Deleting'} {len(to_delete)} duplicate row(s):")
    for idx, prop, ym, disb in sorted(to_delete):
        print(f"  row {idx + 1}: {prop} | {ym}  disb={disb}")

    if not to_delete:
        print("\nNothing to delete.")
        return

    if not APPLY:
        print("\nDRY RUN — nothing was changed. Re-run with APPLY=yes to delete these rows.")
        return

    gid = get_sheet_gid(sheets, "History")
    removed = batch_delete_rows(sheets, gid, [idx for idx, _, _, _ in to_delete])
    print(f"\nDone. Deleted {removed} duplicate row(s).")


if __name__ == "__main__":
    main()
