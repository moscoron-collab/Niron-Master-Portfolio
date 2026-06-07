#!/usr/bin/env python3
"""
ONE-CLICK FIXUP — relabel the old Suncoast / Mid South manual rows.

An earlier version of enter_suncoast_manual.py wrote these 3 out-of-state
properties in a broken format that hid them from the dashboard's per-property
monitor (and from the Divando roll-up):

    col C (LLC)    = the property name (e.g. "8222 Hare Ave")   <-- wrong
    col K (Source) = a bare "Manual Entry"                       <-- wrong

This script rewrites any such row to the correct format:

    col C (LLC)    = "Divando LLC"
    col K (Source) = "Manual Entry: <property>"

It is SAFE to run more than once — it only touches rows still in the broken
format and skips everything else. Triggered from GitHub Actions (one button).
"""

import os, json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

PROPS = {"8222 Hare Ave", "3899 Joest Rd", "6580 Stockport Dr"}


def main():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    svc = build("sheets", "v4", credentials=creds).spreadsheets()

    # Read the whole History tab (A..L). Row 1 is the header.
    rows = svc.values().get(spreadsheetId=SHEET_ID, range="History!A:L").execute().get("values", [])
    if len(rows) < 2:
        print("History is empty — nothing to do.")
        return

    updates = []
    for i, row in enumerate(rows[1:], start=2):  # sheet row number (1-based, +1 for header)
        llc = (row[2].strip() if len(row) > 2 and row[2] else "")  # col C
        if llc not in PROPS:
            continue  # only touch the broken rows
        prop = llc
        updates.append({"range": f"History!C{i}", "values": [["Divando LLC"]]})
        updates.append({"range": f"History!K{i}", "values": [[f"Manual Entry: {prop}"]]})
        print(f"Row {i}: '{prop}' -> Divando LLC + 'Manual Entry: {prop}'")

    if not updates:
        print("No broken rows found — already correct. Nothing changed.")
        return

    svc.values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    print(f"\nDone. Relabeled {len(updates) // 2} row(s).")


if __name__ == "__main__":
    main()
