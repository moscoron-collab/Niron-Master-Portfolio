"""
AppFolio Monthly Cashflow Automation — MOSS INVESTMENTS, LLC v2 (per-property).
Pulls the most recent Owner Packet from AppFolio (Laureate),
extracts numbers PER PROPERTY from each page, and writes one row per property
to the Moss Google Sheet (4 rows from Laureate + 1 row for Cabo plug).

Forked + extended from run_moss.py v1 which only wrote a single consolidated row.

PDF layout (Moss Owner Packet):
  Page 1: Consolidated Summary (skipped — we already have per-property pages)
  Page 2: 1959 S Kearney Way Apt
  Page 3: KEARNEY, 1959  (main house)
  Page 4: KENTON, 1443
  Page 5: KENTON, 1453

Cabo (524 Galeras) is NOT on AppFolio — added as a $2,300/mo plug
through Dec 2026 (per user spec).
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

APPFOLIO_URL    = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL  = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS   = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID        = os.environ["MOSS_SHEET_ID"]
CREDS_JSON      = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64     = os.environ.get("APPFOLIO_COOKIES", "")

# Single AppFolio card to find — the owner packet contains all 4 properties.
APPFOLIO_OWNER_NAME = "Moss Investments, LLC"

# Map PDF page headers → canonical property names that match the dashboard's
# property-ID resolver. Patterns are matched in order; first hit wins.
PROPERTY_NAME_MAP = [
    (re.compile(r"1959\s+S\s+Kearney\s+Way\s+Apt", re.I), "1959 S Kearney Way Apt"),
    (re.compile(r"KEARNEY,\s*1959",                re.I), "1959 S Kearney Way"),
    (re.compile(r"1959\s+S\.?\s*Kearney\s+Way",    re.I), "1959 S Kearney Way"),
    (re.compile(r"KENTON,\s*1443",                 re.I), "1443 S Kenton St"),
    (re.compile(r"1443\s+S\.?\s*Kenton\s+St",      re.I), "1443 S Kenton St"),
    (re.compile(r"KENTON,\s*1453",                 re.I), "1453 S Kenton St"),
    (re.compile(r"1453\s+S\.?\s*Kenton\s+St",      re.I), "1453 S Kenton St"),
]

# Hardcoded mortgage + insurance/12 per property.
# (Cleaner long-term: read from a per-property Settings table — for now this
# matches what's in the dashboard frontend's defaults.)
PROPERTY_FIXED_COSTS = {
    "1959 S Kearney Way":     {"mortgage": 2328.99, "ins_mo": 321.58},
    "1959 S Kearney Way Apt": {"mortgage": 0.00,    "ins_mo": 0.00},
    "1443 S Kenton St":       {"mortgage": 1763.39, "ins_mo": 229.00},
    "1453 S Kenton St":       {"mortgage": 2054.04, "ins_mo": 228.67},
    "524 Galeras":            {"mortgage": 0.00,    "ins_mo": 0.00},
}

# Cabo (524 Galeras): not on AppFolio. Flat $2,300/mo plug through end of 2026.
CABO_PROPERTY          = "524 Galeras"
CABO_DISBURSEMENT_PLUG = 2300.00
CABO_PLUG_FROM         = "2026-05-01"
CABO_PLUG_THROUGH      = "2026-12-01"

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
    """Overwrite an existing row in place (cols A:L) — used to fill a blank
    placeholder row instead of appending a duplicate beside it."""
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A{row_index}:L{row_index}",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()


def require_approval(sheets):
    rows = read_sheet(sheets, "Settings!B3")
    val = rows[0][0] if rows and rows[0] else "YES"
    return val.strip().upper() != "NO"


def _month_key(value):
    """Normalize a History period cell or a 'YYYY-MM-01' label to 'YYYY-MM'.
    Sheets stores the month as a date and may return it formatted (e.g.
    '5/1/2026'), so a raw string compare against 'YYYY-MM-01' misses — which
    made the daily automation append a duplicate every run."""
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}" if m else s


# Core AppFolio properties expected every current month (Galeras/Cabo is a plug,
# not an AppFolio statement, so it's excluded from the "is the month pulled?" test).
MOSS_CORE_PROPERTIES = [p for p in PROPERTY_FIXED_COSTS if p != CABO_PROPERTY]


def _current_month_label():
    """First day of the current calendar month, e.g. '2026-06-01' — the month the
    15th-25th run is pulling (the statement's 'to' date lands in it)."""
    return datetime.date.today().replace(day=1).strftime("%Y-%m-01")


def find_existing(sheets, property_name, month_label):
    """Find an existing History row for this property + month.
    Returns (sheet_row_index, filled): `filled` means the Disbursement cell (col D)
    is non-empty. A BLANK placeholder row reads filled=False, so the real pull fills
    it in (update-in-place) instead of being blocked by it — this is what stopped a
    blank Kearney row from hiding the real $3,926.51. (None, False) = no row at all."""
    target = _month_key(month_label)
    result = (None, False)
    rows = read_sheet(sheets, "History!A:D")
    for i, row in enumerate(rows):
        if i == 0 or len(row) < 3:
            continue
        if row[2].strip() == property_name and _month_key(row[1]) == target:
            filled = len(row) >= 4 and str(row[3]).strip() != ""
            if filled:
                return (i + 1, True)   # a real, filled row wins
            result = (i + 1, False)    # remember the blank row, keep looking
    return result


def already_recorded(sheets, property_name, month_label):
    """Back-compat: True only when a FILLED row exists (a blank row does NOT count)."""
    return find_existing(sheets, property_name, month_label)[1]


def month_already_pulled(sheets, month_label):
    """True when every core AppFolio property already has a FILLED row for this month
    — so the daily run can skip AppFolio entirely (no re-login until next month)."""
    return all(find_existing(sheets, p, month_label)[1] for p in MOSS_CORE_PROPERTIES)


# ── PDF parsing ──────────────────────────────────────────────────────
def normalize_property_name(header_text):
    for pattern, canonical in PROPERTY_NAME_MAP:
        if pattern.search(header_text or ""):
            return canonical
    return None


def extract_per_property_from_pdf(pdf_path):
    """
    Returns a list of {property, disbursement, mgmt_fee, maintenance} —
    one dict per property page (skips the page-1 consolidated summary).
    """
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln for ln in text.split("\n") if ln.strip()]
            if not lines:
                continue
            # First line of each property page is the property header.
            header = lines[0].strip()
            canonical = normalize_property_name(header)
            if not canonical:
                if "Consolidated Summary" in text:
                    print(f"  Page {page_idx + 1}: Consolidated Summary (skipped)")
                else:
                    print(f"  Page {page_idx + 1}: '{header[:60]}' — no property match, skipped")
                continue

            disbursement = None
            mgmt_fee = None
            for i, line in enumerate(lines):
                low = line.lower()
                if disbursement is None and "owner disbursement" in low:
                    disbursement = _find_amount(line, lines, i)
                if mgmt_fee is None and "management fee" in low:
                    mgmt_fee = _find_amount(line, lines, i)

            # Maintenance — for v2 we leave at 0 by default. The user can layer
            # adjustments via the dashboard's Edit modal until we add a proper
            # "Supplies / Maintenance" parser for the transactions table.
            maintenance = 0

            results.append({
                "property":     canonical,
                "disbursement": disbursement or 0,
                "mgmt_fee":     mgmt_fee or 0,
                "maintenance":  maintenance,
            })
            print(f"  Page {page_idx + 1}: {canonical} → Disb=${disbursement or 0:,.2f}, Mgmt=${mgmt_fee or 0:,.2f}")
    return results


def _find_amount(line, lines, idx):
    v = _parse_amount(line)
    if v is not None:
        return abs(v)
    if idx + 1 < len(lines):
        v = _parse_amount(lines[idx + 1])
        if v is not None:
            return abs(v)
    return None


def _parse_amount(text):
    for m in re.findall(r"\(?\$?([\d,]+\.?\d*)\)?", text):
        try:
            return float(m.replace(",", ""))
        except ValueError:
            continue
    return None


# ── Playwright / cookies (unchanged from v1) ─────────────────────────
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


def login(page):
    page.goto(APPFOLIO_URL)
    page.wait_for_load_state("networkidle")
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    print("Logging in with credentials...")
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Login complete.")


def _dump_page_diagnostics(page, tag="DIAG"):
    """Print the live Statements page structure so we can re-target selectors
    after an AppFolio layout change. Read this in the Actions log."""
    try:
        print(f"===== {tag}: PAGE DIAGNOSTICS =====")
        print(f"{tag} url: {page.url}")
        try:
            print(f"{tag} title: {page.title()}")
        except Exception:
            pass
        # All headings (LLC names usually live here)
        try:
            heads = page.query_selector_all("h1, h2, h3, h4")
            print(f"{tag} headings ({len(heads)}):")
            for h in heads[:40]:
                t = (h.inner_text() or "").strip().replace("\n", " ")
                if t:
                    print(f"{tag}   <{h.evaluate('e=>e.tagName')}.{h.evaluate('e=>e.className')}> {t[:120]}")
        except Exception as e:
            print(f"{tag} heading dump failed: {e}")
        # Anything that looks like a card / statement container
        try:
            for sel in ["[class*='card']", "[class*='statement']", "[data-testid]"]:
                els = page.query_selector_all(sel)
                classes = sorted({(e.get_attribute("class") or "")[:80] for e in els})
                print(f"{tag} selector '{sel}': {len(els)} els; classes={classes[:15]}")
        except Exception as e:
            print(f"{tag} card-scan failed: {e}")
        # Download links
        try:
            links = page.query_selector_all("a")
            dl = [(a.get_attribute("href") or "")[:90] for a in links
                  if "statement" in ((a.get_attribute("href") or "").lower())
                  or "download" in ((a.get_attribute("class") or "").lower())]
            print(f"{tag} statement/download links ({len(dl)}): {dl[:15]}")
        except Exception as e:
            print(f"{tag} link dump failed: {e}")
        # Truncated body text so we can see the LLC names + layout
        try:
            body = page.inner_text("body")
            print(f"{tag} body text (first 1500 chars):\n{body[:1500]}")
        except Exception as e:
            print(f"{tag} body dump failed: {e}")
        print(f"===== {tag}: END DIAGNOSTICS =====")
    except Exception as e:
        print(f"{tag}: diagnostics crashed: {e}")


def download_packet(page, tmp_dir):
    """Find the Moss Investments card on the Owner Statements page and download
    the most recent packet. Returns (file_path, month_label, date_range)."""
    page.goto("https://laureatetld.appfolio.com/oportal/statements")
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector("#statements-root .card", timeout=20000)
    except Exception:
        print("WARNING: Timed out waiting for cards")
    cards = page.query_selector_all(".card")
    print(f"Cards found: {len(cards)}")
    if len(cards) < 2:
        # Expected one card per LLC/owner; <2 means the layout likely changed.
        _dump_page_diagnostics(page, tag="MOSS_DIAG")

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
        file_path = os.path.join(tmp_dir, f"moss{ext}")
        download.save_as(file_path)
        return file_path, month_label, date_range

    print(f"WARNING: No card found for '{APPFOLIO_OWNER_NAME}'")
    return None, None, None


def get_pdf_path(file_path, tmp_dir):
    if file_path.endswith(".pdf"):
        return file_path
    extract_dir = os.path.join(tmp_dir, "moss_extract")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            print(f"  ZIP contains: {f}")
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    return None


# ── Cabo helper ──────────────────────────────────────────────────────
def cabo_should_plug(month_label):
    """Cabo gets a flat $2,300/mo plug May–Dec 2026."""
    if not month_label:
        return False
    return CABO_PLUG_FROM <= month_label <= CABO_PLUG_THROUGH


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("Starting Moss AppFolio automation (per-property v2)...")
    sheets = get_sheets_service()
    per_property_results = []
    errors = []
    month_label = None
    date_range = None

    # Once this month's data is already in, don't log into AppFolio again — the
    # daily 15th-25th runs just confirm "already pulled" and stop here.
    exp_month = _current_month_label()
    if month_already_pulled(sheets, exp_month):
        print(f"{exp_month}: all core properties already pulled — skipping AppFolio login.")
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
                    errors.append("Could not download Moss Owner Packet")
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

    approval = require_approval(sheets)
    tab = "Pending Review" if approval else "History"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written = 0

    for r in per_property_results:
        property_name = r["property"]
        idx, filled = find_existing(sheets, property_name, month_label)
        if filled:
            print(f"Already recorded {property_name} for {month_label}, skipping.")
            continue
        fixed = PROPERTY_FIXED_COSTS.get(property_name, {"mortgage": 0, "ins_mo": 0})
        mortgage    = fixed["mortgage"]
        ins_mo      = fixed["ins_mo"]
        tax_mo      = 0  # Tax paid by escrow — not on Owner Packet
        maintenance = r["maintenance"]
        disbursement = r["disbursement"]
        mgmt_fee    = r["mgmt_fee"]
        net = disbursement - mortgage - tax_mo - ins_mo - maintenance
        row = [
            date_range, month_label, property_name,
            disbursement, mgmt_fee,
            mortgage, tax_mo, ins_mo,
            maintenance, net,
            "System — Automation", now_str,
        ]
        if idx:                                    # blank placeholder row → fill it
            update_row(sheets, "History", idx, row)
            print(f"Filled blank row: {property_name} -> Disb ${disbursement:,.2f}, Net ${net:,.2f}")
        else:
            append_row(sheets, tab, row)
            print(f"Written ({tab}): {property_name} -> Disb ${disbursement:,.2f}, Net ${net:,.2f}")
        written += 1

    # Cabo plug — manual fixed $2,300/mo through Dec 2026
    if cabo_should_plug(month_label):
        idx, filled = find_existing(sheets, CABO_PROPERTY, month_label)
        if not filled:
            row = [
                date_range or "", month_label, CABO_PROPERTY,
                CABO_DISBURSEMENT_PLUG, 0,
                0, 0, 0, 0, CABO_DISBURSEMENT_PLUG,
                "Manual plug (Cabo $2,300/mo through Dec 2026)", now_str,
            ]
            if idx:
                update_row(sheets, "History", idx, row)
            else:
                append_row(sheets, tab, row)
            written += 1
            print(f"Written ({tab}): {CABO_PROPERTY} (Cabo plug) -> ${CABO_DISBURSEMENT_PLUG:,.2f}")

    print(f"\nDone. Wrote {written} rows to {tab}.")


if __name__ == "__main__":
    main()
