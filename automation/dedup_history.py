"""
One-time cleanup: removes duplicate rows from the History tab.
Keeps the FIRST occurrence of each (period_start, llc) pair; deletes the rest.
Run once to fix the duplicates caused by the Pending Review approval bug.

Usage (set env vars first):
  export GOOGLE_SHEET_ID=...
  export GOOGLE_CREDENTIALS_JSON='...'
  python automation/dedup_history.py
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID   = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    creds   = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds).spreadsheets()

    result = service.values().get(
        spreadsheetId=SHEET_ID, range="History!A:Z"
    ).execute()
    rows = result.get("values", [])

    if not rows:
        print("History tab is empty.")
        return

    header = rows[0]
    data_rows = rows[1:]
    print(f"Total rows (excluding header): {len(data_rows)}")

    # Columns: A=date_range, B=period_start, C=llc, ...
    seen = set()
    to_delete = []  # 1-based row indices (row 1 = header, row 2 = first data row)
    for i, row in enumerate(data_rows):
        period = row[1] if len(row) > 1 else ""
        llc    = row[2] if len(row) > 2 else ""
        key    = (period, llc)
        if key in seen:
            to_delete.append(i + 2)  # +2: 1-based + skip header
        else:
            seen.add(key)

    print(f"Duplicate rows to delete: {len(to_delete)}")
    if not to_delete:
        print("Nothing to do — History tab is already clean.")
        return

    # Delete from bottom to top so row indices stay valid
    to_delete.sort(reverse=True)
    for row_idx in to_delete:
        service.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                "requests": [{
                    "deleteDimension": {
                        "range": {
                            "sheetId": _get_sheet_id(service, "History"),
                            "dimension": "ROWS",
                            "startIndex": row_idx - 1,  # 0-based
                            "endIndex": row_idx,
                        }
                    }
                }]
            }
        ).execute()
        print(f"  Deleted row {row_idx}")

    print(f"\nDone. Removed {len(to_delete)} duplicate rows from History.")


def _get_sheet_id(service, sheet_name):
    meta = service.get(spreadsheetId=SHEET_ID).execute()
    for s in meta["sheets"]:
        if s["properties"]["title"] == sheet_name:
            return s["properties"]["sheetId"]
    raise ValueError(f"Sheet '{sheet_name}' not found")


if __name__ == "__main__":
    main()
