#!/usr/bin/env python3
"""
Set the Notes (col E) and optionally the Simon amount (col F) of ONE row in the Niron
Distributions tab. Used to mark a sale payout as ONE-TIME so the dashboard keeps it out of
the operating "Your Distribution" totals (Nov 3 2026: the Enid row had no note).

Env: MATCH_DATE (YYYY-MM-DD), MATCH_LLC (substring, case-insensitive), MATCH_AMOUNT (Ron's
amount, col C), SET_NOTES, SET_SIMON (blank = leave col F alone), CONFIRM=YES to write.
Refuses unless exactly one row matches. Prints old -> new.
"""
import os, json, datetime, re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
creds = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]),
                                              scopes=["https://www.googleapis.com/auth/spreadsheets"])
s = build("sheets", "v4", credentials=creds).spreadsheets()
DATE = os.environ.get("MATCH_DATE", "").strip()
LLC = os.environ.get("MATCH_LLC", "").strip().lower()
AMT = round(float(os.environ.get("MATCH_AMOUNT") or 0), 2)
NOTES = os.environ.get("SET_NOTES", "")
SIMON = os.environ.get("SET_SIMON", "").strip()
CONFIRM = os.environ.get("CONFIRM", "").strip().upper() == "YES"


def iso(v):
    s_ = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s_)
    if m:
        return m.group(0)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s_)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    try:
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(s_)))).isoformat()
    except ValueError:
        return ""


def money(v):
    try:
        return round(float(str(v).replace("$", "").replace(",", "")), 2)
    except ValueError:
        return None


rows = s.values().get(spreadsheetId=SHEET_ID, range="Distributions!A:F",
                      valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])

# BATCH mode (env BATCH = JSON list of {"date","llc","amount", "ron"?, "nir"?, "simon"?, "notes"?}):
# sets Ron (C) / Nir (D) / Simon (F) / Notes (E) on each matched row. Every row must match exactly once.
BATCH = os.environ.get("BATCH", "").strip()
if BATCH:
    print("MODE:", "WRITE" if CONFIRM else "DRY RUN (set confirm=YES to write)")
    data, bad = [], []
    for t in json.loads(BATCH):
        hits = [i + 1 for i, r in enumerate(rows) if i >= 4 and len(r) > 2 and iso(r[0]) == t["date"]
                and t["llc"].lower() in str(r[1]).lower() and money(r[2]) == round(float(t["amount"]), 2)]
        if len(hits) != 1:
            bad.append(f'{t["date"]} {t["llc"]} {t["amount"]}: {len(hits)} rows'); continue
        rn = hits[0]; r = rows[rn - 1] + [""] * 6
        for key, col, idx in (("ron", "C", 2), ("nir", "D", 3), ("notes", "E", 4), ("simon", "F", 5)):
            if key in t:
                print(f"Row {rn} {t['date']} {r[1]}: {key} {r[idx]!r} -> {t[key]!r}")
                data.append({"range": f"Distributions!{col}{rn}", "values": [[t[key]]]})
    if bad:
        raise SystemExit("::error::No single match for: " + "; ".join(bad))
    if CONFIRM:
        s.values().batchUpdate(spreadsheetId=SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": data}).execute()
        print("Written.")
    raise SystemExit(0)
hits = [i + 1 for i, r in enumerate(rows) if i >= 4 and len(r) > 2 and iso(r[0]) == DATE
        and LLC in str(r[1]).lower() and money(r[2]) == AMT]
print("MODE:", "WRITE" if CONFIRM else "DRY RUN (set confirm=YES to write)")
if len(hits) != 1:
    raise SystemExit(f"::error::Expected exactly 1 matching row, found {len(hits)}: {hits}")
rn = hits[0]
r = rows[rn - 1] + [""] * 6
print(f"Row {rn}: {r[:6]}")
print(f"  Notes (E): {r[4]!r} -> {NOTES!r}")
data = [{"range": f"Distributions!E{rn}", "values": [[NOTES]]}]
if SIMON:
    print(f"  Simon (F): {r[5]!r} -> {float(SIMON)}")
    data.append({"range": f"Distributions!F{rn}", "values": [[float(SIMON)]]})
if CONFIRM:
    s.values().batchUpdate(spreadsheetId=SHEET_ID, body={"valueInputOption": "USER_ENTERED", "data": data}).execute()
    print("Written.")
