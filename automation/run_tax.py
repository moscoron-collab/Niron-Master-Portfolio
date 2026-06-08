"""
Property Tax balance scraper — Niron portfolio (Divando + Dorado).

Goal: auto-fill the "Amount Due" column of the `Property Tax` Google Sheet tab
from each county treasurer website, so the dashboard always shows the live
balance without the user looking each parcel up by hand.

WHY THIS IS TWO-PHASE (read before editing):
The county portals (Denver, Adams, Duval, ...) block naive HTTP requests with a
403 and render their numbers with JavaScript, so the page HTML can't be read from
a plain fetch — only from a REAL browser. Playwright (the same headless Chromium
the AppFolio jobs use) gets past that, but we can't see the rendered markup from
the dev machine. So this script runs in two modes:

  1. CALIBRATE (default)  — loads each parcel's Tax Link in a real browser, prints
     the candidate dollar amounts it found, and dumps the page text + a screenshot
     to ./tax_dumps/ (uploaded as a workflow artifact). It does NOT write anything.
     The first run is a calibration run: we read the real pages from the artifacts
     and lock in the exact per-county extractor below.
  2. WRITE (TAX_WRITE=1) — once an extractor is trusted, writes the scraped amount
     into Amount Due (col G) + a timestamp into col S ("Auto-Updated"). It only
     writes when it is CONFIDENT about the number, and NEVER zeroes a cell on a
     failed lookup (a missed scrape leaves the manual value untouched).

Only the direct-deep-link counties are handled (the Tax Link points straight at the
parcel): Denver (denvergov.org), Adams (adcotax.com), Duval FL (county-taxes.com).
Arapahoe (arapahoegov.com search form) and Memphis (payit901.com) store only a
generic search page in Tax Link, so they need form automation — left for phase 2.

Reuses the existing Sheets service-account auth (GOOGLE_SHEET_ID +
GOOGLE_CREDENTIALS_JSON secrets). No AppFolio login needed — these are public
lookups, so no cookies / 2FA.
"""

import os
import re
import json
import datetime
import traceback
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID   = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
TAX_WRITE  = os.environ.get("TAX_WRITE", "") in ("1", "true", "TRUE", "yes")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TAB = "Property Tax"
DATA_START_ROW = 5           # data begins at row 5 (title row 1, headers row 4)
COL_AMOUNT_DUE = "G"         # what we auto-fill
COL_CHECKED    = "S"         # timestamp of last successful auto-update (extra col)
DUMP_DIR = "tax_dumps"

# Column indexes within a Property Tax row (A=0 ... R=17)
C_LLC, C_STATE, C_PROPERTY, C_COUNTY, C_PARCEL = 0, 1, 2, 3, 4
C_TAX_YEAR, C_AMOUNT_DUE, C_AMOUNT_PAID = 5, 6, 7
C_PAID_BY, C_TAX_LINK = 9, 11

REALISTIC_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


# ── Google Sheets ────────────────────────────────────────────────────
def get_sheets():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def read_rows(sheets):
    return sheets.values().get(
        spreadsheetId=SHEET_ID, range=f"'{TAB}'!A{DATA_START_ROW}:S"
    ).execute().get("values", [])


def write_cell(sheets, col, sheet_row, value):
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{TAB}'!{col}{sheet_row}",
        valueInputOption="USER_ENTERED",
        body={"values": [[value]]},
    ).execute()


# ── Amount extraction ────────────────────────────────────────────────
MONEY = r"\$?\s*([0-9][0-9,]*\.[0-9]{2})"

# Labels that typically precede the payable balance, best first. The generic
# finder returns every (label, amount) it sees so calibration shows what's on the
# page; the per-county extractors below pick the right one once we've seen it.
DUE_LABELS = [
    "total amount due", "total due", "amount due", "balance due",
    "current balance", "total tax due", "tax due", "amount to pay",
    "pay this amount", "total amount to pay",
]


def to_float(s):
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def find_amount_candidates(text):
    """Return [(label, amount_float)] for every due-like figure on the page."""
    low = text.lower()
    out = []
    for label in DUE_LABELS:
        for m in re.finditer(re.escape(label) + r"[:\s]*" + MONEY, low):
            amt = to_float(m.group(1))
            if amt is not None:
                out.append((label, amt))
    return out


def extract_denver(text):
    # Denver "Real Property" page: locked after calibration. Falls back to the
    # first labelled due amount until then.
    cands = find_amount_candidates(text)
    return cands[0][1] if cands else None


def extract_adams(text):
    # Adams treasurerweb account.jsp: locked after calibration.
    cands = find_amount_candidates(text)
    return cands[0][1] if cands else None


def extract_duval(text):
    # Duval county-taxes.com bills page: locked after calibration.
    cands = find_amount_candidates(text)
    return cands[0][1] if cands else None


HANDLERS = {
    "denvergov.org": ("Denver", extract_denver),
    "adcotax.com": ("Adams", extract_adams),
    "county-taxes.com": ("Duval", extract_duval),
}


def handler_for(url):
    host = (urlparse(url).hostname or "").lower()
    for key, val in HANDLERS.items():
        if host.endswith(key) or key in host:
            return val
    return (None, None)


# ── Main ─────────────────────────────────────────────────────────────
def main():
    os.makedirs(DUMP_DIR, exist_ok=True)
    sheets = get_sheets()
    rows = read_rows(sheets)
    print(f"Mode: {'WRITE (will update Amount Due)' if TAX_WRITE else 'CALIBRATE (no writes)'}")
    print(f"Read {len(rows)} property-tax rows from '{TAB}'.\n")

    updated = 0
    skipped = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=REALISTIC_UA, viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        for i, row in enumerate(rows):
            def cell(idx):
                return row[idx].strip() if idx < len(row) and row[idx] else ""

            sheet_row = DATA_START_ROW + i
            prop = cell(C_PROPERTY)
            link = cell(C_TAX_LINK)
            if not prop:
                continue
            if "escrow" in cell(C_PAID_BY).lower():
                print(f"· {prop}: escrow (lender pays) — skipped")
                skipped += 1
                continue
            if not link:
                print(f"· {prop}: no Tax Link — skipped")
                skipped += 1
                continue

            county, extractor = handler_for(link)
            if not extractor:
                print(f"· {prop}: {urlparse(link).hostname} not a direct-link county (search form) — skipped (phase 2)")
                skipped += 1
                continue

            try:
                # county-taxes.com (Duval) never reaches networkidle, so use
                # domcontentloaded + a settle delay rather than waiting for idle.
                page.goto(link, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4500)
                text = page.inner_text("body")
            except Exception as e:
                print(f"✗ {prop} [{county}]: page load failed — {str(e).splitlines()[0]}")
                skipped += 1
                continue

            # Always dump for calibration / debugging.
            safe = re.sub(r"[^a-zA-Z0-9]+", "_", prop)[:40]
            try:
                with open(os.path.join(DUMP_DIR, f"{i:02d}_{county}_{safe}.txt"), "w") as fh:
                    fh.write(f"URL: {link}\n\n{text}")
                page.screenshot(path=os.path.join(DUMP_DIR, f"{i:02d}_{county}_{safe}.png"), full_page=True)
            except Exception:
                pass

            cands = find_amount_candidates(text)
            amount = extractor(text)
            sheet_amt = to_float(str(cell(C_AMOUNT_DUE)).replace("$", "")) or 0.0
            cand_str = ", ".join(f"{lbl}=${amt:,.2f}" for lbl, amt in cands[:6]) or "none found"
            print(f"· {prop} [{county}] sheet=${sheet_amt:,.2f}  →  scraped={('$%.2f' % amount) if amount else 'NONE'}  | candidates: {cand_str}")

            # Calibration aid: show every line that contains a dollar figure, with the
            # line above it for context, so the real label wording is visible in the log.
            if not TAX_WRITE:
                lines = [ln.strip() for ln in text.splitlines()]
                shown = 0
                for j, ln in enumerate(lines):
                    if re.search(MONEY, ln) and shown < 18:
                        prev = lines[j - 1] if j > 0 and lines[j - 1] else ""
                        print(f"      $ | {prev[:45]} » {ln[:70]}")
                        shown += 1
                if shown == 0:
                    print(f"      (no $ figures in page text — length {len(text)} chars; likely canvas/iframe, see screenshot)")

            if TAX_WRITE and amount and amount > 0:
                write_cell(sheets, COL_AMOUNT_DUE, sheet_row, round(amount, 2))
                write_cell(sheets, COL_CHECKED, sheet_row,
                           datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + f" ({county})")
                print(f"    ✏️  wrote Amount Due = ${amount:,.2f} to {COL_AMOUNT_DUE}{sheet_row}")
                updated += 1

        browser.close()

    print(f"\nDone. {'Updated ' + str(updated) + ' rows.' if TAX_WRITE else 'Calibration only — no writes.'} Skipped {skipped}.")
    print(f"Page dumps + screenshots saved to ./{DUMP_DIR}/ (workflow artifact).")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
