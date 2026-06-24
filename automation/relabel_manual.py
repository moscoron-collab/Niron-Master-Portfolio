#!/usr/bin/env python3
"""
ONE-CLICK FIXUP — relabel the old Suncoast / Mid South manual rows.

The 3 out-of-state properties (Hare / Joest / Stockport) roll up under
Divando LLC, and the dashboard tells them apart by the Source column (K)
reading "Manual Entry: <property>". Two older broken shapes exist; this
script repairs BOTH and is safe to run repeatedly (idempotent):

  Shape A (oldest enter_suncoast_manual.py bug):
      col C (LLC)    = the property name (e.g. "8222 Hare Ave")   <-- wrong
      col K (Source) = a bare "Manual Entry"                       <-- wrong
    Fix -> col C = "Divando LLC", col K = "Manual Entry: <property>"

  Shape B (the April 2026 rows — col C already correct, only the label is
  generic, so Shape A's name-based match can't see them):
      col B (Month)  = 2026-04-01
      col C (LLC)    = "Divando LLC"            <-- already correct
      col K (Source) = a bare "Manual Entry"   <-- wrong (no property)
    The property is recovered from the Owner Disbursement amount (col D),
    using the mapping the user confirmed:
      $478.25 -> 3899 Joest Rd
      $920.00 -> 6580 Stockport Dr
      $1,209.00 -> 8222 Hare Ave
    Fix -> col K = "Manual Entry: <property>" (the amount is NOT changed).

Triggered from GitHub Actions (one button): "Relabel Manual Entries".
"""

import os, json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Shape A — rows whose LLC column wrongly holds the property name.
PROPS = {"8222 Hare Ave", "3899 Joest Rd", "6580 Stockport Dr"}

# Shape B — April 2026 "Divando LLC" + bare "Manual Entry" rows, matched by
# Owner Disbursement amount (col D). User-confirmed mapping.
APRIL_2026 = "04/01/2026"  # the start of the Date Range string in col A
APRIL_AMOUNT_MAP = [
    (478.25, "3899 Joest Rd"),
    (920.00, "6580 Stockport Dr"),
    (1209.00, "8222 Hare Ave"),
]


def to_amount(v):
    """Parse a cell value (number or '$1,209.00' style text) to a float, or None."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def match_april_property(amount):
    if amount is None:
        return None
    for amt, prop in APRIL_AMOUNT_MAP:
        if abs(amount - amt) < 0.005:
            return prop
    return None


def main():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    svc = build("sheets", "v4", credentials=creds).spreadsheets()

    # Read the whole History tab (A..L). Row 1 is the header. UNFORMATTED_VALUE so
    # the Disbursement column comes back as a number we can match reliably.
    rows = (
        svc.values()
        .get(spreadsheetId=SHEET_ID, range="History!A:L", valueRenderOption="UNFORMATTED_VALUE")
        .execute()
        .get("values", [])
    )
    if len(rows) < 2:
        print("History is empty — nothing to do.")
        return

    def cell(row, idx):
        return row[idx] if len(row) > idx and row[idx] is not None else ""

    updates = []
    for i, row in enumerate(rows[1:], start=2):  # sheet row number (1-based, +1 for header)
        date_range = str(cell(row, 0)).strip()  # col A
        llc = str(cell(row, 2)).strip()         # col C
        source = str(cell(row, 10)).strip()     # col K

        # Shape A: LLC column wrongly holds the property name.
        if llc in PROPS:
            prop = llc
            updates.append({"range": f"History!C{i}", "values": [["Divando LLC"]]})
            updates.append({"range": f"History!K{i}", "values": [[f"Manual Entry: {prop}"]]})
            print(f"Row {i}: [shape A] '{prop}' -> Divando LLC + 'Manual Entry: {prop}'")
            continue

        # Shape B: April 2026 Divando rows with a bare "Manual Entry" source.
        if llc == "Divando LLC" and source == "Manual Entry" and date_range.startswith(APRIL_2026):
            amount = to_amount(cell(row, 3))  # col D — Owner Disbursement
            prop = match_april_property(amount)
            if prop:
                updates.append({"range": f"History!K{i}", "values": [[f"Manual Entry: {prop}"]]})
                amt_str = f"${amount:,.2f}" if amount is not None else "?"
                print(f"Row {i}: [shape B] {amt_str} -> 'Manual Entry: {prop}'")
            else:
                print(f"Row {i}: [shape B] bare 'Manual Entry' but amount {amount} not in the "
                      f"April map — left alone (check it manually).")

    if not updates:
        print("No broken rows found — already correct. Nothing changed.")
        return

    svc.values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    print(f"\nDone. Relabeled {len(updates)} cell update(s).")


if __name__ == "__main__":
    main()
