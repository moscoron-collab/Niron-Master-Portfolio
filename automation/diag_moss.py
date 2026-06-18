"""One-off diagnostic: dump Moss History rows for 1959 S Kearney Way / June 2026
so we can see why the dashboard shows $0 'edited'. Reads only — writes nothing.
Run via the diag_moss.yml workflow (workflow_dispatch)."""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID   = os.environ["MOSS_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = ["A Date", "B Month", "C Property", "D Disb", "E Mgmt", "F Mort",
           "G Tax", "H Ins", "I Maint", "J Net", "K EnteredBy", "L LoggedAt"]


def main():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    rows = sheets.values().get(spreadsheetId=SHEET_ID, range="History!A:L").execute().get("values", [])
    print(f"History has {len(rows)} rows (incl header).\n")

    print("=== Rows mentioning 'Kearney' (any month) ===")
    for i, row in enumerate(rows):
        prop = (row[2] if len(row) > 2 else "")
        if "kearney" in prop.lower():
            cells = " | ".join(f"{HEADERS[j]}={row[j] if j < len(row) else ''!r}" for j in range(12))
            print(f"sheetRow {i + 1}: {cells}")

    print("\n=== All rows for June 2026 (month col B contains '2026-06' or '6/1/2026') ===")
    for i, row in enumerate(rows):
        mon = (row[1] if len(row) > 1 else "")
        if "2026-06" in str(mon) or "6/1/2026" in str(mon):
            prop = row[2] if len(row) > 2 else ""
            disb = row[3] if len(row) > 3 else ""
            src  = row[10] if len(row) > 10 else ""
            print(f"sheetRow {i + 1}: month={mon!r} prop={prop!r} disb={disb!r} enteredBy={src!r}")


if __name__ == "__main__":
    main()
