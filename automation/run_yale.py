"""
AppFolio Per-Property Automation — YALE TOWNHOMES, LLC (Niron portfolio).

SEPARATE from run.py on purpose. run.py keeps writing the single consolidated
"Yale Townhomes, LLC" row to History (the partner-facing card data — untouched).
This script reads the SAME Yale Owner Packet but breaks the numbers down PER UNIT
and writes one row per townhome unit to the dedicated "Property Detail" tab on the
Niron sheet (same tab Divando uses). Nothing here can affect the existing cards or
History.

⚠️ Yale's packet is STRUCTURALLY DIFFERENT from Divando's:
  - Divando = one PDF page per property (clean per-property summary blocks).
  - Yale    = ONE consolidated property ("YALE, 2991-2999") with a single Property
              Cash Summary. The 5 townhome units (2991/2993/2995/2997/2999) appear
              ONLY as a prefix inside the Transactions table line descriptions
              (e.g. "2991 - Rent Income"). There is NO per-unit Owner Disbursement
              or per-unit Management Fee line — those exist only at the whole-Yale
              level (one pooled $10,076.61 disbursement, four unlabeled mgmt-fee
              checks).

So per-unit RENT + occupancy are recovered by summing the transaction lines by unit
number (using the running Balance column to tell cash-in from cash-out, which also
handles NSF/reversal lines correctly). The pooled Management Fees and Owner
Disbursement from the summary are then ALLOCATED to each unit in proportion to that
unit's cash-in, so the per-unit disbursements sum back to the statement total. Fixed
costs are split evenly: one Lument mortgage and one Acuity policy cover all 5 units.

Verified against 3 months of bank statements (acct "2 Yale LLC 2321", Mar/Apr/May
2026 — all identical):
  - Lument mortgage  = $7,279.08/mo  -> ÷5 = $1,455.82 per unit
  - Acuity insurance = $1,037.55/mo  -> ÷5 =   $207.51 per unit
  - SBA loan         =   $225.00/mo  -> LLC-level business debt, NOT per-unit
                                        (mirrors Divando's SBA handling; excluded here)

Yale tax is escrowed in the mortgage (isTaxEscrowed in index.html) so tax is NOT
deducted in per-property net. Per-unit repairs are applied live by the dashboard
from the Maintenance Log, same as Divando — so we do NOT write tax/maintenance/net
here; the frontend computes net from these inputs.
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
APPFOLIO_OWNER_NAME = "Yale Townhomes, LLC"
LLC_NAME            = "Yale Townhomes, LLC"

# Where per-property rows go. SAME isolated tab Divando uses. Never touches History.
DETAIL_TAB = "Property Detail"
DETAIL_HEADER = [
    "Date Range", "Month", "LLC", "Property",
    "Cash In", "Rent Collected", "Mgmt Fee", "Disbursement",
    "Mortgage", "Insurance/12", "Status", "Source", "Updated",
]

# The 5 townhome units. The unit number is how each is identified inside the
# Transactions table; the canonical name is what the dashboard shows.
YALE_UNIT_NUMBERS = ["2991", "2993", "2995", "2997", "2999"]
YALE_PROPERTY = {n: f"{n} W Yale Ave" for n in YALE_UNIT_NUMBERS}

# Fixed costs are shared across all 5 units (one mortgage, one policy) and split
# evenly. Bank-verified Mar/Apr/May 2026.
YALE_MORTGAGE_TOTAL = 7279.08
YALE_INS_TOTAL      = 1037.55
YALE_MORTGAGE_EACH  = round(YALE_MORTGAGE_TOTAL / 5, 2)   # 1455.82
YALE_INS_EACH       = round(YALE_INS_TOTAL / 5, 2)        # 207.51

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


# The 5 Yale units this pull writes every month — used to decide "is the month
# already pulled?" so the daily run can stop logging into AppFolio.
EXPECTED_PROPERTIES = sorted(YALE_PROPERTY.values())


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
    """True when every Yale unit already has a FILLED row for this month — so the
    daily run can skip AppFolio entirely (no re-login until next month)."""
    return all(find_existing(sheets, p, month_label)[1] for p in EXPECTED_PROPERTIES)


# ── PDF parsing ──────────────────────────────────────────────────────
_AMOUNT_RE = re.compile(r"-?\(?\$?([\d,]+\.\d{2})\)?")
_DATE_RE   = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_UNIT_RE   = re.compile(r"\b(" + "|".join(YALE_UNIT_NUMBERS) + r")\b")

# Revenue keywords — a cash-IN line in these categories is income; the matching
# cash-OUT line (an NSF / reversal) cancels it back out. Anything else going out is
# an operating expense (repairs / supplies / utilities).
_RENT_RE     = re.compile(r"Rent Income", re.I)
_REVENUE_RE  = re.compile(r"Rent Income|Pet Rent|NSF Fees|Late Fee|Garbage|Recycling|Application", re.I)
_MGMT_RE     = re.compile(r"Management Fee", re.I)
_DISB_RE     = re.compile(r"Owner (Distribution|payment|Disbursement)", re.I)
_SD_RE       = re.compile(r"Security Deposit", re.I)


def _parse_amount(text):
    m = _AMOUNT_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _summary_value(lines, label):
    """Find a Property Cash Summary line that STARTS with `label` and return its
    amount (absolute value)."""
    for ln in lines:
        s = ln.strip()
        if s.startswith(label):
            v = _parse_amount(s)
            return abs(v) if v is not None else None
    return None


def extract_per_unit_from_pdf(pdf_path):
    """Parse the Yale Owner Packet into per-unit numbers.

    Returns (units_dict, totals_dict) where units_dict maps unit-number ->
    {cash_in, rent_collected, expenses, occupied} and totals_dict carries the
    statement-level Cash In / Management Fees / Owner Disbursements used to
    allocate the pooled disbursement back to each unit.
    """
    units = {n: {"cash_in": 0.0, "rent_collected": 0.0, "expenses": 0.0, "occupied": False}
             for n in YALE_UNIT_NUMBERS}

    all_lines = []
    summary = {}
    begin_balance = 0.0
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend([ln for ln in text.split("\n") if ln.strip()])

    # Statement-level totals from the Property Cash Summary block (page 1).
    summary["cash_in"]      = _summary_value(all_lines, "Cash In") or 0.0
    summary["mgmt_fee"]     = _summary_value(all_lines, "Management Fees") or 0.0
    summary["disbursement"] = _summary_value(all_lines, "Owner Disbursements") or 0.0
    bb = _summary_value(all_lines, "Beginning Balance")
    begin_balance = bb if bb is not None else 0.0

    # Walk the Transactions table using the running Balance column to classify each
    # line as cash-in or cash-out (delta sign). This correctly nets NSF/reversal
    # lines and avoids guessing which number is the amount vs. the balance.
    #
    # AppFolio WRAPS long descriptions, so a transaction's unit number + category
    # ("2995 - Rent Income - NSF reversal") often lands on the line(s) ABOVE the
    # line that carries the date + amount + balance. So for each date line we match
    # unit/keywords against a CONTEXT window = every non-date line since the previous
    # date line, plus the date line itself. That re-stitches the wrapped fragments.
    date_idxs = [i for i, ln in enumerate(all_lines) if _DATE_RE.search(ln)]
    prev_balance = begin_balance
    started = False
    prev_date_idx = -1
    for idx in date_idxs:
        ln = all_lines[idx]
        amounts = _AMOUNT_RE.findall(ln)
        if not amounts:
            prev_date_idx = idx
            continue
        new_balance = float(amounts[-1].replace(",", ""))

        # The "Beginning Cash Balance as of MM/DD/YYYY 500.00" line seeds the balance.
        if not started and ("Beginning Cash Balance" in ln or len(amounts) == 1):
            prev_balance = new_balance
            started = True
            prev_date_idx = idx
            continue
        started = True

        delta = round(new_balance - prev_balance, 2)
        prev_balance = new_balance
        if delta == 0:
            prev_date_idx = idx
            continue

        context = " ".join(all_lines[prev_date_idx + 1: idx + 1])
        prev_date_idx = idx

        um = _UNIT_RE.search(context)
        unit = um.group(1) if um else None
        ln = context  # match keywords against the stitched context below

        if delta > 0:                      # cash IN
            if unit:
                units[unit]["cash_in"] += delta
                if _RENT_RE.search(ln):
                    units[unit]["rent_collected"] += delta
                    units[unit]["occupied"] = True
        else:                              # cash OUT
            amt = -delta
            if _MGMT_RE.search(ln) or _DISB_RE.search(ln):
                continue                   # pooled — handled via summary totals
            if unit and (_REVENUE_RE.search(ln) or _SD_RE.search(ln)):
                # NSF / reversal of a prior receipt (rent, fee, or deposit) —
                # cancel it back out of cash-in rather than booking an expense.
                units[unit]["cash_in"] -= amt
                if _RENT_RE.search(ln):
                    units[unit]["rent_collected"] -= amt
            elif unit:
                units[unit]["expenses"] += amt   # repairs / supplies / utilities

    # Round and finalize occupancy (rent collected > 0 => occupied).
    for n, u in units.items():
        u["cash_in"]        = round(max(u["cash_in"], 0.0), 2)
        u["rent_collected"] = round(max(u["rent_collected"], 0.0), 2)
        u["expenses"]       = round(u["expenses"], 2)
        u["occupied"]       = u["rent_collected"] > 0
    return units, summary


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
    """Find the Yale card and download the most recent packet.
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
        file_path = os.path.join(tmp_dir, f"yale{ext}")
        download.save_as(file_path)
        return file_path, month_label, date_range

    print(f"WARNING: No card found for '{APPFOLIO_OWNER_NAME}'")
    return None, None, None


def get_pdf_path(file_path, tmp_dir):
    if file_path.endswith(".pdf"):
        return file_path
    extract_dir = os.path.join(tmp_dir, "yale_extract")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            print(f"  ZIP contains: {f}")
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    return None


def build_rows(units, summary, date_range, month_label, now_str,
               source="System — Yale per-property"):
    """Allocate the pooled Management Fees + Owner Disbursement to each unit in
    proportion to its cash-in, and build the Property Detail rows."""
    total_cash_in = sum(u["cash_in"] for u in units.values()) or 1.0
    total_mgmt    = summary.get("mgmt_fee", 0.0)
    total_disb    = summary.get("disbursement", 0.0)

    rows = []
    for n in YALE_UNIT_NUMBERS:
        u = units[n]
        share = u["cash_in"] / total_cash_in
        mgmt_fee     = round(total_mgmt * share, 2)
        disbursement = round(total_disb * share, 2)
        rows.append([
            date_range, month_label, LLC_NAME, YALE_PROPERTY[n],
            u["cash_in"], u["rent_collected"], mgmt_fee, disbursement,
            YALE_MORTGAGE_EACH, YALE_INS_EACH,
            "Occupied" if u["occupied"] else "Vacant",
            source, now_str,
        ])
    return rows


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("Starting Yale per-property automation...")
    sheets = get_sheets_service()
    units = summary = None
    month_label = date_range = None
    errors = []

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
                    errors.append("Could not download Yale Owner Packet")
                else:
                    pdf_path = get_pdf_path(file_path, tmp_dir)
                    if not pdf_path:
                        errors.append("Owner Packet.pdf not found in download")
                    else:
                        units, summary = extract_per_unit_from_pdf(pdf_path)
            except Exception as e:
                errors.append(str(e))
                print(traceback.format_exc())
        browser.close()

    if errors:
        print(f"Errors: {errors}")
    if not units or not month_label:
        print("Nothing to write.")
        return

    ensure_detail_tab(sheets)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = build_rows(units, summary, date_range, month_label, now_str)

    written = 0
    for row in rows:
        property_name = row[3]
        idx, filled = find_existing(sheets, property_name, month_label)
        if filled:
            print(f"Already recorded {property_name} for {month_label}, skipping.")
            continue
        if idx:                                    # blank placeholder row → fill it
            update_row(sheets, DETAIL_TAB, idx, row)
        else:
            append_row(sheets, DETAIL_TAB, row)
        written += 1
        print(f"Written: {property_name} -> CashIn ${row[4]:,.2f}, "
              f"Rent ${row[5]:,.2f}, Disb ${row[7]:,.2f}, {row[10]}")

    print(f"\nDone. Wrote {written} rows to '{DETAIL_TAB}'.")


if __name__ == "__main__":
    main()
