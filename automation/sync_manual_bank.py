#!/usr/bin/env python3
"""
Set the out-of-state manual rows (Hare / Joest / Stockport) in the Niron History tab to
the amounts that actually hit the Divando bank account (Nov 3 2026, Ron: "you can only
see it through the bank account, update the whole year").

Rule: one row per property per month, where the month = the month the deposit landed in
the bank, and the amount = the deposit. A month with a target of 0 gets a $0 row.

TARGETS (env) is JSON: {"8222 Hare Ave": {"2026-01": 1183.91, ...}, ...}
Only the properties and months listed are touched. For each one:
  - no row      -> append
  - one row     -> update Disbursement (D) + Net (J) if the amount differs
  - 2+ rows     -> update the first, report the rest (never deletes)
DRY RUN unless CONFIRM == "YES". Every change is printed old -> new.
"""

import os, json, datetime, calendar, re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
TARGETS = json.loads(os.environ["TARGETS"])
CONFIRM = os.environ.get("CONFIRM", "").strip().upper() == "YES"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def svc():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def month_key(v):
    """'2026-06-01' / '6/1/2026' / '06/01/2026' / serial number -> '2026-06'."""
    s = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}"
    try:
        d = datetime.date(1899, 12, 30) + datetime.timedelta(days=float(s))
        return f"{d.year:04d}-{d.month:02d}"
    except ValueError:
        return ""


def money(v):
    try:
        return round(float(str(v).replace("$", "").replace(",", "").strip()), 2)
    except ValueError:
        return None


def main():
    s = svc()
    rows = s.values().get(spreadsheetId=SHEET_ID, range="History!A:L",
                          valueRenderOption="UNFORMATTED_VALUE",
                          dateTimeRenderOption="FORMATTED_STRING").execute().get("values", [])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("MODE:", "WRITE" if CONFIRM else "DRY RUN (set confirm=YES to write)")

    index = {}
    for i, r in enumerate(rows):
        if len(r) > 10 and str(r[10]).startswith("Manual Entry: "):
            prop = str(r[10])[len("Manual Entry: "):].strip()
            index.setdefault((prop, month_key(r[1])), []).append(i + 1)  # 1-based sheet row

    updates, appends, same = [], [], 0
    for prop, months in TARGETS.items():
        for mk, amt in sorted(months.items()):
            amt = round(float(amt), 2)
            hits = index.get((prop, mk), [])
            if not hits:
                y, m = (int(x) for x in mk.split("-"))
                last = calendar.monthrange(y, m)[1]
                appends.append([f"{m:02d}/01/{y} - {m:02d}/{last:02d}/{y}", f"{y:04d}-{m:02d}-01",
                                "Divando LLC", amt, 0, 0, 0, 0, 0, amt, f"Manual Entry: {prop}", now])
                print(f"ADD     {mk} {prop}: ${amt:,.2f}")
                continue
            if len(hits) > 1:
                print(f"WARN    {mk} {prop}: {len(hits)} rows (sheet rows {hits}) - only the first is set")
            rn = hits[0]
            old = money(rows[rn - 1][3]) if len(rows[rn - 1]) > 3 else None
            if old == amt:
                same += 1
                print(f"OK      {mk} {prop}: ${amt:,.2f}")
                continue
            print(f"CHANGE  {mk} {prop}: {'blank' if old is None else f'${old:,.2f}'} -> ${amt:,.2f} (row {rn})")
            updates.append({"range": f"History!D{rn}", "values": [[amt]]})
            updates.append({"range": f"History!J{rn}", "values": [[amt]]})
            updates.append({"range": f"History!L{rn}", "values": [[now]]})

    print(f"\nSummary: {same} already correct, {len(updates) // 3} to change, {len(appends)} to add.")
    if not CONFIRM:
        return
    if updates:
        s.values().batchUpdate(spreadsheetId=SHEET_ID, body={
            "valueInputOption": "USER_ENTERED", "data": updates}).execute()
    if appends:
        s.values().append(spreadsheetId=SHEET_ID, range="History!A:L",
                          valueInputOption="USER_ENTERED", body={"values": appends}).execute()
    print("Written.")


if __name__ == "__main__":
    main()
