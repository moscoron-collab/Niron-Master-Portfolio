#!/usr/bin/env python3
"""
Correct the fixed costs (Mortgage col F, Insurance col H) of AppFolio History rows, and the
matching Settings defaults that future pulls copy, to bank-verified actuals (Nov 3 2026).

TARGETS (env JSON):
  {"history":  {"5070 Donald, LLC": {"2026-10": {"mortgage": 13938, "ins": 1193.42}}},
   "settings": {"5070 Donald, LLC": {"mortgage": 13938, "annual_ins": 14321.04}}}
History rows are matched by LLC (col C, exact) + month (col B) and skip "Manual Entry" rows.
Net (col J) is recomputed the way the pulls write it: D - F - G - H - I.
Settings rows are matched by col A = LLC; mortgage -> col B, annual_ins -> col D.
DRY RUN unless CONFIRM == "YES". Prints every change old -> new.
"""
import os, json, re, datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]),
                                              scopes=["https://www.googleapis.com/auth/spreadsheets"])
s = build("sheets", "v4", credentials=creds).spreadsheets()
SID = os.environ["GOOGLE_SHEET_ID"]
T = json.loads(os.environ["TARGETS"])
CONFIRM = os.environ.get("CONFIRM", "").strip().upper() == "YES"


def mk(v):
    x = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})", x)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", x)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}"
    try:
        d = datetime.date(1899, 12, 30) + datetime.timedelta(days=float(x))
        return f"{d.year:04d}-{d.month:02d}"
    except ValueError:
        return ""


def num(v):
    try:
        return round(float(str(v).replace("$", "").replace(",", "")), 2)
    except ValueError:
        return 0.0


print("MODE:", "WRITE" if CONFIRM else "DRY RUN (set confirm=YES to write)")
upd, missing = [], []
rows = s.values().get(spreadsheetId=SID, range="History!A:L", valueRenderOption="UNFORMATTED_VALUE",
                      dateTimeRenderOption="FORMATTED_STRING").execute().get("values", [])
for llc, months in T.get("history", {}).items():
    for month, vals in sorted(months.items()):
        hits = [i for i, r in enumerate(rows) if len(r) > 3 and str(r[2]).strip() == llc and mk(r[1]) == month
                and not str(r[10] if len(r) > 10 else "").startswith("Manual Entry")]
        if len(hits) != 1:
            missing.append(f"{month} {llc}: {len(hits)} rows")
            continue
        i = hits[0]; r = rows[i] + [""] * 12; rn = i + 1
        D, F, G, H, I = num(r[3]), num(r[5]), num(r[6]), num(r[7]), num(r[8])
        nF = round(float(vals.get("mortgage", F)), 2); nH = round(float(vals.get("ins", H)), 2)
        nJ = round(D - nF - G - nH - I, 2)
        if (nF, nH) == (F, H):
            print(f"OK      {month} {llc}: mortgage {F:,.2f} ins {H:,.2f}")
            continue
        print(f"CHANGE  {month} {llc} (row {rn}): mortgage {F:,.2f} -> {nF:,.2f} | ins {H:,.2f} -> {nH:,.2f} | net(J) {num(r[9]):,.2f} -> {nJ:,.2f}")
        upd += [{"range": f"History!F{rn}", "values": [[nF]]}, {"range": f"History!H{rn}", "values": [[nH]]},
                {"range": f"History!J{rn}", "values": [[nJ]]}]

srows = s.values().get(spreadsheetId=SID, range="Settings!A:E", valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
for llc, vals in T.get("settings", {}).items():
    hits = [i for i, r in enumerate(srows) if r and str(r[0]).strip() == llc]
    if len(hits) != 1:
        missing.append(f"Settings {llc}: {len(hits)} rows")
        continue
    i = hits[0]; r = srows[i] + [""] * 5; rn = i + 1
    for key, col, idx in (("mortgage", "B", 1), ("annual_ins", "D", 3)):
        if key in vals and num(r[idx]) != round(float(vals[key]), 2):
            print(f"SETTING {llc} (row {rn}) {key}: {num(r[idx]):,.2f} -> {float(vals[key]):,.2f}")
            upd.append({"range": f"Settings!{col}{rn}", "values": [[float(vals[key])]]})

if missing:
    raise SystemExit("::error::Not exactly one row for: " + "; ".join(missing))
print(f"\n{len(upd)} cells to write.")
if CONFIRM and upd:
    s.values().batchUpdate(spreadsheetId=SID, body={"valueInputOption": "USER_ENTERED", "data": upd}).execute()
    print("Written.")
