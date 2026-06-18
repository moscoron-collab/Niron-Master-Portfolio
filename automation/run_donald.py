"""
AppFolio Per-Property Automation — 5070 DONALD, LLC (Niron portfolio).

SEPARATE from run.py on purpose. run.py keeps writing the single consolidated
"5070 Donald, LLC" row to History (the partner-facing card data — untouched). This
script reads the SAME Donald Owner Packet but extracts numbers PER UNIT from each
page (pages 2..9; page 1 is the consolidated summary) and writes one row per unit to
the dedicated "Property Detail" tab on the Niron sheet (same tab Divando/Yale use).
Nothing here can affect the existing dashboard cards or History.

Donald's packet is the SAME clean structure as Divando — one PDF page per unit, each
with its own "Property Cash Summary" block (Cash In / Management Fees / Owner
Disbursements). So unlike Yale, the per-unit disbursement is read directly from each
page; no allocation is needed.

Donald Owner Packet layout (9 pages for the 8-unit statement):
  Page 1   : Consolidated Summary (skipped)
  Pages 2+ : one page per unit, header "DONALD, NNNN - NNNN E Donald Ave, Denver, CO"

The 8 units are 4 duplexes (5060 & 5062, 5064 & 5066, 5070 & 5072, 5080 & 5082).

Fixed costs (bank-verified: acct "1 Donald LLC 9364", Mar/Apr/May 2026, all identical):
  - Mortgage  (CBRE blanket loan)   = $13,708.00/mo -> ÷8 = $1,713.50 per unit
  - Insurance (Westfield, 1 policy) =  $1,210.84/mo -> ÷8 =   $151.36 per unit
  - SBA loan                        =    $444.00/mo -> LLC-level business debt,
                                                       NOT per-unit (mirrors Divando/Yale)

Donald tax is escrowed in the mortgage (isTaxEscrowed in index.html) so tax is NOT
deducted in per-unit net. Per-unit maintenance is applied live by the dashboard from
the Maintenance Log — so we do NOT write tax/maintenance/net here; the frontend
computes net from these inputs.
"""

import os
import re
import json
import base64
import zipfile
import tempfile
import datetime
import traceback

import pdfplumber
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

APPFOLIO_URL   = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS  = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID       = os.environ["GOOGLE_SHEET_ID"]          # Niron sheet (same as run.py)
CREDS_JSON     = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64    = os.environ.get("APPFOLIO_COOKIES", "")

# AppFolio card title on the Owner Statements page (matches LLC_MAP in run.py).
APPFOLIO_OWNER_NAME = "5070 Donald, LLC"
LLC_NAME            = "5070 Donald, LLC"

# Where per-property rows go. SAME isolated tab Divando/Yale use. Never touches History.
DETAIL_TAB = "Property Detail"
DETAIL_HEADER = [
    "Date Range", "Month", "LLC", "Property",
    "Cash In", "Rent Collected", "Mgmt Fee", "Disbursement",
    "Mortgage", "Insurance/12", "Status", "Source", "Updated",
]

# Map each property page header (matched on the code before " - ") to a canonical
# address used everywhere on the dashboard.
PROPERTY_CODE_MAP = {
    "DONALD, 5060": "5060 E Donald Ave",
    "DONALD, 5062": "5062 E Donald Ave",
    "DONALD, 5064": "5064 E Donald Ave",
    "DONALD, 5066": "5066 E Donald Ave",
    "DONALD, 5070": "5070 E Donald Ave",
    "DONALD, 5072": "5072 E Donald Ave",
    "DONALD, 5080": "5080 E Donald Ave",
    "DONALD, 5082": "5082 E Donald Ave",
}

# Blanket CBRE mortgage + Westfield insurance split evenly across all 8 units.
# SBA loan ($444/mo) is general business debt and stays at the LLC level — excluded.
DONALD_MORTGAGE_EACH = round(13708.00 / 8, 2)   # 1713.50
DONALD_INS_EACH      = round(1210.84 / 8, 2)    # 151.36
DONALD_FIXED_COSTS = {
    canonical: {"mortgage": DONALD_MORTGAGE_EACH, "ins_mo": DONALD_INS_EACH}
    for canonical in PROPERTY_CODE_MAP.values()
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ── Google Sheets ────────────────────────────────────────────────────
def get_sheets_service():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def read_sheet(sheets, range_name):
    return sheets.values().get(spreadsheetId=SHEET_ID, range=range_name).execute().get("values", [])


def append_row(sheets, tab, row):
    sheets.values().append(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def update_row(sheets, tab, row_index, row):
    """Overwrite a row in place (cols A:M) — fills a blank placeholder row instead
    of appending a duplicate beside it."""
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A{row_index}:M{row_index}",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()


def ensure_detail_tab(sheets):
    """Create the Property Detail tab (with header) if it doesn't exist yet."""
    meta = sheets.get(spreadsheetId=SHEET_ID).execute()
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if DETAIL_TAB in titles:
        return
    print(f"Creating '{DETAIL_TAB}' tab...")
    sheets.batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": [{"addSheet": {"properties": {"title": DETAIL_TAB}}}]},
    ).execute()
    append_row(sheets, DETAIL_TAB, DETAIL_HEADER)


def _month_key(value):
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}" if m else s


# Every unit this pull is expected to write each month — used to decide "is the
# month already pulled?" so the daily run can stop logging into AppFolio.
EXPECTED_PROPERTIES = sorted(set(PROPERTY_CODE_MAP.values()))


def _current_month_label():
    """First day of the current calendar month, e.g. '2026-06-01'."""
    return datetime.datetime.now().replace(day=1).strftime("%Y-%m-01")


def find_existing(sheets, property_name, month_label):
    """Find this unit + month in Property Detail (col D=Property, col B=Month).
    Returns (sheet_row_index, filled): `filled` = the Disbursement cell (col H) is
    non-empty, so a BLANK placeholder row reads filled=False and gets filled in
    instead of blocking the real data. (None, False) if there is no row at all."""
    target = _month_key(month_label)
    result = (None, False)
    rows = read_sheet(sheets, f"'{DETAIL_TAB}'!A:H")
    for i, row in enumerate(rows):
        if i == 0 or len(row) < 4:
            continue
        if row[3].strip() == property_name and _month_key(row[1]) == target:
            filled = len(row) >= 8 and str(row[7]).strip() != ""
            if filled:
                return (i + 1, True)
            result = (i + 1, False)
    return result


def already_recorded(sheets, property_name, month_label):
    """Back-compat: True only when a FILLED row exists (a blank row does NOT count)."""
    return find_existing(sheets, property_name, month_label)[1]


def month_already_pulled(sheets, month_label):
    """True when every expected unit already has a FILLED row for this month — so the
    daily run can skip AppFolio entirely (no re-login until next month)."""
    return all(find_existing(sheets, p, month_label)[1] for p in EXPECTED_PROPERTIES)


# ── PDF parsing (identical logic to run_divando.py) ──────────────────
def _parse_amount(text):
    """First dollar-looking number on a line (summary lines are 'Label 1,234.56')."""
    m = re.search(r"-?\(?\$?([\d,]+\.\d{2})\)?", text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _summary_value(lines, label):
    """Find a Property Cash Summary line that STARTS with `label` and return its
    amount. Starts-with avoids matching the transactions table / column headers."""
    for ln in lines:
        s = ln.strip()
        if s.startswith(label):
            return _parse_amount(s)
    return None


def _match_code(header):
    """Header looks like 'CODE - Full Address'. Return canonical address or None."""
    code_part = header.split(" - ")[0].strip().upper()
    for code, canonical in PROPERTY_CODE_MAP.items():
        if code_part == code.upper():
            return canonical
    return None


def extract_per_property_from_pdf(pdf_path):
    """Return a list of dicts (one per unit page):
    {property, cash_in, rent_collected, mgmt_fee, disbursement, occupied}."""
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln for ln in text.split("\n") if ln.strip()]
            if not lines:
                continue
            header = lines[0].strip()
            canonical = _match_code(header)
            if not canonical:
                if "Consolidated Summary" in text:
                    print(f"  Page {page_idx + 1}: Consolidated Summary (skipped)")
                else:
                    print(f"  Page {page_idx + 1}: '{header[:50]}' — no match, skipped")
                continue

            cash_in      = _summary_value(lines, "Cash In") or 0.0
            mgmt_fee     = abs(_summary_value(lines, "Management Fees") or 0.0)
            disbursement = abs(_summary_value(lines, "Owner Disbursements") or 0.0)
            occupied     = "Rent Income" in text
            rent_collected = cash_in if occupied else 0.0

            results.append({
                "property":       canonical,
                "cash_in":        cash_in,
                "rent_collected": rent_collected,
                "mgmt_fee":       mgmt_fee,
                "disbursement":   disbursement,
                "occupied":       occupied,
            })
            status = "Occupied" if occupied else "VACANT"
            print(f"  Page {page_idx + 1}: {canonical} → CashIn=${cash_in:,.2f}, "
                  f"Disb=${disbursement:,.2f}, {status}")
    return results


# ── Playwright / cookies (mirrors run_divando.py) ────────────────────
def _normalize_cookies(cookies):
    out = []
    for c in cookies:
        cookie = {
            "name": c.get("name"), "value": c.get("value"),
            "domain": c.get("domain"), "path": c.get("path", "/"),
        }
        if "expirationDate" in c: cookie["expires"] = int(c["expirationDate"])
        if "httpOnly" in c: cookie["httpOnly"] = c["httpOnly"]
        if "secure" in c: cookie["secure"] = c["secure"]
        if "sameSite" in c:
            ss = c["sameSite"]
            if ss in ("no_restriction", "unspecified", None): cookie["sameSite"] = "None"
            elif ss == "lax": cookie["sameSite"] = "Lax"
            elif ss == "strict": cookie["sameSite"] = "Strict"
        out.append(cookie)
    return out


def load_cookies():
    if not COOKIES_B64:
        return []
    raw = COOKIES_B64.strip()
    try:
        return _normalize_cookies(json.loads(raw))
    except Exception:
        pass
    try:
        return _normalize_cookies(json.loads(base64.b64decode(raw).decode()))
    except Exception:
        return []


def save_cookies(context):
    encoded = base64.b64encode(json.dumps(context.cookies()).encode()).decode()
    print(f"::set-output name=new_cookies::{encoded}")


STATEMENTS_URL = "https://laureatetld.appfolio.com/oportal/statements"

def login(page):
    page.goto(STATEMENTS_URL)
    page.wait_for_load_state("networkidle")
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    print("Logging in with credentials...")
    page.goto(APPFOLIO_URL)
    page.wait_for_load_state("networkidle")
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Login complete.")


def download_packet(page, tmp_dir):
    """Find the Donald card and download the most recent packet.
    Returns (file_path, month_label, date_range)."""
    page.goto("https://laureatetld.appfolio.com/oportal/statements")
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector("#statements-root .card", timeout=20000)
    except Exception:
        print("WARNING: Timed out waiting for cards")
    cards = page.query_selector_all(".card")
    print(f"Cards found: {len(cards)}")

    for card in cards:
        h2 = card.query_selector("h2.card-title")
        if not h2 or h2.inner_text().strip() != APPFOLIO_OWNER_NAME:
            continue
        print(f"Found card for: {APPFOLIO_OWNER_NAME}")
        first_li = card.query_selector("ul.list-group li")
        if not first_li:
            return None, None, None
        date_text = first_li.query_selector("b")
        date_range = date_text.inner_text().strip() if date_text else ""
        print(f"Most recent packet: {date_range}")

        month_label = None
        m = re.search(r"to\s+(\w+ \d+, \d+)", date_range)
        if m:
            try:
                to_date = datetime.datetime.strptime(m.group(1), "%b %d, %Y")
                month_label = to_date.strftime("%Y-%m-01")
            except Exception:
                pass

        dl_link = first_li.query_selector(".analytics-statement-download-link a")
        if not dl_link:
            return None, None, None
        href = dl_link.get_attribute("href") or ""
        ext = ".zip" if ".zip" in href else ".pdf"
        with page.expect_download() as dl_info:
            dl_link.click()
        download = dl_info.value
        file_path = os.path.join(tmp_dir, f"donald{ext}")
        download.save_as(file_path)
        return file_path, month_label, date_range

    print(f"WARNING: No card found for '{APPFOLIO_OWNER_NAME}'")
    return None, None, None


def get_pdf_path(file_path, tmp_dir):
    if file_path.endswith(".pdf"):
        return file_path
    extract_dir = os.path.join(tmp_dir, "donald_extract")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            print(f"  ZIP contains: {f}")
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    return None


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("Starting Donald per-property automation...")
    sheets = get_sheets_service()
    per_property_results = []
    errors = []
    month_label = None
    date_range = None

    # Once every unit is already in for this month, don't log into AppFolio again.
    ensure_detail_tab(sheets)
    exp_month = _current_month_label()
    if month_already_pulled(sheets, exp_month):
        print(f"{exp_month}: all {len(EXPECTED_PROPERTIES)} units already pulled — skipping AppFolio login.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        print(f"Loaded {len(cookies)} cookies")
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        login(page)
        save_cookies(context)

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                file_path, month_label, date_range = download_packet(page, tmp_dir)
                if not file_path or not month_label:
                    errors.append("Could not download Donald Owner Packet")
                else:
                    pdf_path = get_pdf_path(file_path, tmp_dir)
                    if not pdf_path:
                        errors.append("Owner Packet.pdf not found in download")
                    else:
                        per_property_results = extract_per_property_from_pdf(pdf_path)
            except Exception as e:
                errors.append(str(e))
                print(traceback.format_exc())
        browser.close()

    print(f"\nParsed {len(per_property_results)} property pages")
    if errors:
        print(f"Errors: {errors}")

    if not per_property_results or not month_label:
        print("Nothing to write.")
        return

    ensure_detail_tab(sheets)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written = 0

    for r in per_property_results:
        property_name = r["property"]
        idx, filled = find_existing(sheets, property_name, month_label)
        if filled:
            print(f"Already recorded {property_name} for {month_label}, skipping.")
            continue
        fixed = DONALD_FIXED_COSTS.get(property_name, {"mortgage": 0, "ins_mo": 0})
        row = [
            date_range, month_label, LLC_NAME, property_name,
            r["cash_in"], r["rent_collected"], r["mgmt_fee"], r["disbursement"],
            fixed["mortgage"], fixed["ins_mo"],
            "Occupied" if r["occupied"] else "Vacant",
            "System — Donald per-property", now_str,
        ]
        if idx:                                    # blank placeholder row → fill it
            update_row(sheets, DETAIL_TAB, idx, row)
        else:
            append_row(sheets, DETAIL_TAB, row)
        written += 1
        print(f"Written: {property_name} -> CashIn ${r['cash_in']:,.2f}, "
              f"Disb ${r['disbursement']:,.2f}, {row[10]}")

    print(f"\nDone. Wrote {written} rows to '{DETAIL_TAB}'.")


if __name__ == "__main__":
    main()
