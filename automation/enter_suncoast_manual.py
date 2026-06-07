#!/usr/bin/env python3
"""
Manual entry for the 3 Propertyware properties (Suncoast + MidSouth) until the
managers start emailing the PDF and full automation takes over.

Triggered from GitHub Actions (workflow_dispatch). The user supplies the month
and the Net Operating Income for each property; this writes one row per property
to the Niron sheet History tab, in the exact same column layout as run.py.

No mortgage, no insurance on these properties → net_cashflow == NOI.
Leave a property's value blank/0 to skip it (e.g. if you didn't get its statement).
"""

import os, json, datetime, calendar
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID  = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Month like "2026-04" (year-month). Property NOIs as plain numbers.
MONTH_INPUT = os.environ["MONTH"].strip()
PROPERTIES = {
    "8222 Hare Ave":     os.environ.get("HARE_NOI", "").strip(),
    "3899 Joest Rd":     os.environ.get("JOEST_NOI", "").strip(),
    "6580 Stockport Dr": os.environ.get("STOCKPORT_NOI", "").strip(),
}


def sheets_client():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def read_range(svc, rng):
    return svc.values().get(spreadsheetId=SHEET_ID, range=rng).execute().get("values", [])


def already_recorded(svc, source, month_label):
    """Match on period_start (col B) + the Source string (col K) so the 3 properties are
    told apart even though they all share LLC = 'Divando LLC' (col C)."""
    for tab in ("History", "Pending Review"):
        for row in read_range(svc, f"'{tab}'!A:K")[1:]:
            if len(row) >= 11 and row[1] == month_label and row[10] == source:
                return True
    return False


def parse_money(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def main():
    # Parse month input → period_start label + a human date range
    try:
        year, month = (int(x) for x in MONTH_INPUT.replace("/", "-").split("-")[:2])
    except ValueError:
        raise SystemExit(f"MONTH must look like 2026-04 (got '{MONTH_INPUT}')")
    period_start = f"{year:04d}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    date_range = f"{month:02d}/01/{year} - {month:02d}/{last_day:02d}/{year}"

    svc = sheets_client()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    wrote = 0
    for prop, raw in PROPERTIES.items():
        noi = parse_money(raw)
        if noi is None or noi == 0:
            print(f"Skipping {prop} (no value entered)")
            continue
        source = f"Manual Entry: {prop}"
        if already_recorded(svc, source, period_start):
            print(f"Already recorded {prop} for {period_start} — skipping")
            continue
        # The 3 out-of-state properties roll up under Divando LLC, so the LLC column (C) is
        # "Divando LLC" and the property name lives in the Source column (K) as
        # "Manual Entry: <property>" — that is exactly how the dashboard's
        # buildPropertyRecords() and Divando roll-up locate them. (Older runs wrongly put
        # the property in col C with a bare "Manual Entry" source, which made these rows
        # invisible to the per-property monitor.)
        row = [
            date_range, period_start, "Divando LLC",
            noi, 0,         # disbursement (= NOI), mgmt_fee (already netted out)
            0, 0, 0,        # mortgage, tax_mo, ins_mo
            0, noi,         # maintenance, net_cashflow
            source, now_str,
        ]
        svc.values().append(
            spreadsheetId=SHEET_ID,
            range="History!A:Z",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        ).execute()
        print(f"Saved {prop} {period_start} → ${noi:,.2f}")
        wrote += 1

    print(f"\nDone. {wrote} row(s) written to History.")


if __name__ == "__main__":
    main()
