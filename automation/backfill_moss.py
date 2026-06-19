"""
AppFolio Historical Backfill — MOSS INVESTMENTS, LLC v2 (per-property).
Paginates through AppFolio Owner Statements for Moss and, for every historical
Owner Packet, writes one row PER PROPERTY to the Moss sheet's History tab
(4 rows from Laureate + 1 Cabo plug when in window) — mirroring run_moss.py.

Old versions of this script wrote a single consolidated "Moss Investments, LLC"
total row per month. For any month it re-imports, this version removes that
legacy total row so the per-property rows replace it without duplicates.

Trigger manually via GitHub Actions (backfill_moss.yml) with the months input.

PDF layout (Moss Owner Packet):
  Page 1: Consolidated Summary (skipped — we parse the per-property pages)
  Page 2: 1959 S Kearney Way Apt
  Page 3: KEARNEY, 1959  (main house)
  Page 4: KENTON, 1443
  Page 5: KENTON, 1453
"""

import os
import re
import json
import time
import base64
import zipfile
import tempfile
import datetime
import traceback

import pdfplumber
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

APPFOLIO_URL    = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL  = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS   = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID        = os.environ["MOSS_SHEET_ID"]
CREDS_JSON      = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64     = os.environ.get("APPFOLIO_COOKIES", "")
MAX_MONTHS      = int(os.environ.get("BACKFILL_MONTHS", "12"))

# Single AppFolio card to find — the owner packet contains all 4 properties.
APPFOLIO_OWNER_NAME = "Moss Investments, LLC"

# Legacy single total rows written by the v1 backfill use this exact LLC string.
# We delete these for any re-imported month so per-property rows replace them.
LEGACY_TOTAL_NAME = "Moss Investments, LLC"

# Map PDF page headers → canonical property names that match the dashboard's
# property-ID resolver. Patterns are matched in order; first hit wins.
# (Kept in sync with run_moss.py.)
PROPERTY_NAME_MAP = [
    (re.compile(r"1959\s+S\s+Kearney\s+Way\s+Apt", re.I), "1959 S Kearney Way Apt"),
    (re.compile(r"KEARNEY,\s*1959",                re.I), "1959 S Kearney Way"),
    (re.compile(r"1959\s+S\.?\s*Kearney\s+Way",    re.I), "1959 S Kearney Way"),
    (re.compile(r"KENTON,\s*1443",                 re.I), "1443 S Kenton St"),
    (re.compile(r"1443\s+S\.?\s*Kenton\s+St",      re.I), "1443 S Kenton St"),
    (re.compile(r"KENTON,\s*1453",                 re.I), "1453 S Kenton St"),
    (re.compile(r"1453\s+S\.?\s*Kenton\s+St",      re.I), "1453 S Kenton St"),
]

# Hardcoded mortgage + insurance/12 per property (kept in sync with run_moss.py).
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


def _execute(request, what="API call"):
    """Run a Sheets API request, retrying with backoff on rate-limit (429) and
    transient (500/503) errors so a momentary quota hit doesn't abort the run."""
    delay = 2
    for attempt in range(6):
        try:
            return request.execute()
        except HttpError as e:
            status = e.resp.status if getattr(e, "resp", None) is not None else None
            if status in (429, 500, 503) and attempt < 5:
                print(f"  {what}: HTTP {status} — backing off {delay}s (retry {attempt + 1}/5)")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def read_sheet(sheets, range_name):
    return _execute(sheets.values().get(spreadsheetId=SHEET_ID, range=range_name),
                    f"read {range_name}").get("values", [])


def append_rows(sheets, tab, rows):
    """Append many rows in a single write request (one API call, not one per row)."""
    if not rows:
        return
    _execute(
        sheets.values().append(
            spreadsheetId=SHEET_ID,
            range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ),
        f"append {len(rows)} row(s)",
    )


def batch_delete_rows(sheets, gid, row_indices):
    """Delete the given 0-based sheet row indices in one batchUpdate."""
    if gid is None or not row_indices:
        return 0
    # Delete bottom-up so earlier deletions don't shift later indices.
    requests = [{
        "deleteDimension": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": i, "endIndex": i + 1},
        }
    } for i in sorted(set(row_indices), reverse=True)]
    _execute(sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}),
             f"delete {len(requests)} row(s)")
    return len(requests)


def get_sheet_gid(sheets, tab_name):
    """Numeric sheetId for a tab — required by batchUpdate row deletions."""
    meta = _execute(sheets.get(spreadsheetId=SHEET_ID, fields="sheets(properties(sheetId,title))"),
                    "get metadata")
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            return s["properties"]["sheetId"]
    return None


def _period_to_ym(period_val):
    """Best-effort YYYY-MM for a History column-B value across known formats."""
    period = str(period_val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(period, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", period)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def scan_history(sheets):
    """Read History once. Returns (existing, legacy_rows):
      existing    — set of (name, 'YYYY-MM') already present (for dedup);
      legacy_rows — list of (0-based row index, 'YYYY-MM') for the old single
                    'Moss Investments, LLC' total rows."""
    rows = read_sheet(sheets, "History!A:C")
    existing = set()
    legacy_rows = []
    for idx, row in enumerate(rows):
        if idx == 0 or len(row) < 3:  # skip header / short rows
            continue
        name = row[2].strip()
        ym = _period_to_ym(row[1])
        if ym is None:
            continue
        existing.add((name, ym))
        if name == LEGACY_TOTAL_NAME:
            legacy_rows.append((idx, ym))
    return existing, legacy_rows


# ── PDF parsing (per-property — mirrors run_moss.py) ─────────────────
def normalize_property_name(header_text):
    for pattern, canonical in PROPERTY_NAME_MAP:
        if pattern.search(header_text or ""):
            return canonical
    return None


def extract_per_property_from_pdf(pdf_path):
    """Returns a list of {property, disbursement, mgmt_fee, maintenance} —
    one dict per property page (skips the page-1 consolidated summary)."""
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln for ln in text.split("\n") if ln.strip()]
            if not lines:
                continue
            header = lines[0].strip()
            canonical = normalize_property_name(header)
            if not canonical:
                if "Consolidated Summary" in text:
                    print(f"    Page {page_idx + 1}: Consolidated Summary (skipped)")
                else:
                    print(f"    Page {page_idx + 1}: '{header[:60]}' — no property match, skipped")
                continue

            disbursement = None
            mgmt_fee = None
            for i, line in enumerate(lines):
                low = line.lower()
                if disbursement is None and "owner disbursement" in low:
                    disbursement = _find_amount(line, lines, i)
                if mgmt_fee is None and "management fee" in low:
                    mgmt_fee = _find_amount(line, lines, i)

            # Maintenance left at 0 — supplies are already netted out of the
            # disbursement on the Owner Packet (matches run_moss.py).
            maintenance = 0

            # CRITICAL: if the Owner Disbursement could NOT be parsed, SKIP this
            # property — do NOT write a $0 row. This is exactly what produced the
            # bogus 2023 "$0.00 / System — Backfill" Kearney rows: `disbursement or 0`
            # turned a parse failure into a real-looking $0 row that then distorted
            # history (and, mirrored as a browser override, masked live data).
            # `disbursement is None` = parse failure (skip); a genuinely-parsed 0.0
            # is kept (real vacant/reserve month).
            if disbursement is None:
                print(f"    Page {page_idx + 1}: {canonical} — no Owner Disbursement parsed, "
                      "SKIPPING (will not write a $0 row).")
                continue

            results.append({
                "property":     canonical,
                "disbursement": disbursement,
                "mgmt_fee":     mgmt_fee or 0,
                "maintenance":  maintenance,
            })
            print(f"    Page {page_idx + 1}: {canonical} → Disb=${disbursement:,.2f}, Mgmt=${mgmt_fee or 0:,.2f}")
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


# ── Cabo helper ──────────────────────────────────────────────────────
def cabo_should_plug(month_label):
    """Cabo gets a flat $2,300/mo plug May–Dec 2026."""
    if not month_label:
        return False
    return CABO_PLUG_FROM <= month_label <= CABO_PLUG_THROUGH


# ── Playwright / cookies ─────────────────────────────────────────────
def _normalize_cookies(cookies):
    out = []
    for c in cookies:
        cookie = {"name": c.get("name"), "value": c.get("value"),
                  "domain": c.get("domain"), "path": c.get("path", "/")}
        if "expirationDate" in c:
            cookie["expires"] = int(c["expirationDate"])
        elif "expires" in c and c["expires"]:
            try: cookie["expires"] = int(c["expires"])
            except: pass
        if "httpOnly" in c: cookie["httpOnly"] = c["httpOnly"]
        if "secure" in c: cookie["secure"] = c["secure"]
        if "sameSite" in c:
            ss = c["sameSite"]
            if ss in ("no_restriction","unspecified",None,""): cookie["sameSite"] = "None"
            elif ss in ("lax","Lax"): cookie["sameSite"] = "Lax"
            elif ss in ("strict","Strict"): cookie["sameSite"] = "Strict"
            elif ss in ("None","none"): cookie["sameSite"] = "None"
        out.append(cookie)
    return out


def load_cookies():
    if not COOKIES_B64: return []
    raw = COOKIES_B64.strip()
    try: return _normalize_cookies(json.loads(raw))
    except Exception: pass
    try: return _normalize_cookies(json.loads(base64.b64decode(raw).decode()))
    except Exception: return []


def login(page):
    print("Navigating to login page...")
    page.goto(APPFOLIO_URL)
    page.wait_for_load_state("networkidle")
    print(f"URL: {page.url}")
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    print("Logging in with credentials...")
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")


def parse_packet_li(li):
    """Extract metadata from a list item. Returns dict or None."""
    date_text = li.query_selector("b")
    if not date_text:
        return None
    date_range = date_text.inner_text().strip()
    if not re.search(r"\w+ \d+, \d+ to \w+ \d+, \d+", date_range):
        return None

    m_to = re.search(r"to\s+(\w+ \d+, \d+)", date_range)
    m_from = re.search(r"^(\w+ \d+, \d+)", date_range)
    if not m_to or not m_from:
        return None
    try:
        to_date   = datetime.datetime.strptime(m_to.group(1), "%b %d, %Y")
        from_date = datetime.datetime.strptime(m_from.group(1), "%b %d, %Y")
        # Skip year-end / annual summaries
        if (to_date - from_date).days > 60:
            return {"skip": True, "date_range": date_range}
        month_label = to_date.strftime("%Y-%m-01")
    except Exception:
        return None

    dl_link = li.query_selector(".analytics-statement-download-link a")
    if not dl_link:
        return None
    href = dl_link.get_attribute("href") or ""
    return {
        "date_range": date_range,
        "month_label": month_label,
        "href": href,
        "ext": ".zip" if ".zip" in href else ".pdf",
    }


def find_card_index(page, appfolio_name):
    cards = page.query_selector_all(".card")
    for idx, card in enumerate(cards):
        h2 = card.query_selector("h2.card-title")
        if h2 and h2.inner_text().strip() == appfolio_name:
            return idx
    return -1


def click_next_page(page, card_idx):
    """Click the 'next page' button within the specified LLC's card. Returns True if clicked."""
    cards = page.query_selector_all(".card")
    if card_idx >= len(cards):
        return False
    card = cards[card_idx]
    pagination_btns = card.query_selector_all(".pagination li.page-item button")
    for btn in pagination_btns:
        html = btn.inner_html()
        if "fa-angle-right" in html and "fa-angle-double-right" not in html:
            parent_li = btn.evaluate_handle("el => el.closest('li')")
            classes = parent_li.evaluate("el => el.className") if parent_li else ""
            if "disabled" in classes:
                return False
            try:
                btn.click()
                return True
            except Exception:
                return False
    return False


def collect_packets(page, appfolio_name, max_count):
    """Navigate, paginate, and return up to max_count monthly packets."""
    print(f"  Navigating to statements page...")
    page.goto("https://laureatetld.appfolio.com/oportal/statements")
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector("#statements-root .card", timeout=20000)
    except Exception:
        print("  WARNING: Timed out waiting for cards")

    card_idx = find_card_index(page, appfolio_name)
    if card_idx == -1:
        print(f"  No card found for '{appfolio_name}'")
        return []
    print(f"  Card index: {card_idx}")

    all_packets = []
    seen_month_labels = set()
    page_num = 1
    max_pages = (max_count // 4) + 3  # safety margin

    while len(all_packets) < max_count and page_num <= max_pages:
        cards = page.query_selector_all(".card")
        if card_idx >= len(cards):
            break
        card = cards[card_idx]
        items = card.query_selector_all("ul.list-group li")
        print(f"  Page {page_num}: {len(items)} items")

        new_added = 0
        for li in items:
            data = parse_packet_li(li)
            if not data:
                continue
            if data.get("skip"):
                print(f"    Skipping non-monthly: {data['date_range']}")
                continue
            if data["month_label"] in seen_month_labels:
                continue
            seen_month_labels.add(data["month_label"])
            all_packets.append(data)
            new_added += 1
            if len(all_packets) >= max_count:
                break

        if len(all_packets) >= max_count or new_added == 0:
            break

        if not click_next_page(page, card_idx):
            print("  No next page available")
            break
        page.wait_for_timeout(2000)
        page_num += 1

    return all_packets


def download_via_url(page, url, file_path):
    """Download a file directly via HTTP using the page's session cookies."""
    if url.startswith("/"):
        url = "https://laureatetld.appfolio.com" + url
    response = page.context.request.get(url)
    if response.status >= 400:
        raise Exception(f"Download failed with HTTP {response.status}")
    with open(file_path, "wb") as f:
        f.write(response.body())


def get_pdf_path(file_path, tmp_dir, name):
    if file_path.endswith(".pdf"): return file_path
    extract_dir = os.path.join(tmp_dir, name.replace(" ", "_"))
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    return None


def build_row(pkt, prop, r, now_str):
    fixed = PROPERTY_FIXED_COSTS.get(prop, {"mortgage": 0, "ins_mo": 0})
    mortgage     = fixed["mortgage"]
    ins_mo       = fixed["ins_mo"]
    tax_mo       = 0  # Tax paid by escrow — not on Owner Packet
    maintenance  = r["maintenance"]
    disbursement = r["disbursement"]
    mgmt_fee     = r["mgmt_fee"]
    net = disbursement - mortgage - tax_mo - ins_mo - maintenance
    row = [
        pkt["date_range"], pkt["month_label"], prop,
        disbursement, mgmt_fee,
        mortgage, tax_mo, ins_mo,
        maintenance, net,
        "System — Backfill", now_str,
    ]
    return row, disbursement, net


def main():
    print(f"Starting Moss per-property backfill — up to {MAX_MONTHS} months...")
    sheets      = get_sheets_service()
    history_gid = get_sheet_gid(sheets, "History")
    if history_gid is None:
        print("WARNING: Could not resolve History sheetId — legacy total rows "
              "will NOT be auto-removed.")

    # Read History once up front; dedup + legacy lookup happen in memory so the
    # whole run makes only a couple of API writes (avoids the per-row write
    # quota of 60/min that throttled the v2.0 implementation).
    existing, legacy_rows = scan_history(sheets)
    print(f"History has {len(existing)} (property, month) entries; "
          f"{len(legacy_rows)} legacy 'Moss Investments, LLC' total row(s).")

    pending     = []      # rows to append, accumulated then written in one call
    cleanup_yms = set()   # months that now have per-property data
    written = 0
    skipped = 0
    errors  = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        print(f"Loaded {len(cookies)} cookies from secret")
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        login(page)

        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"\n=== {APPFOLIO_OWNER_NAME} (per-property) ===")
            try:
                packets = collect_packets(page, APPFOLIO_OWNER_NAME, MAX_MONTHS)
                print(f"  Collected {len(packets)} monthly packets")

                for pkt in packets:
                    month_label = pkt["month_label"]
                    ym = month_label[:7]

                    print(f"  [{month_label}] downloading...")
                    try:
                        file_path = os.path.join(tmp_dir, f"moss_{month_label}{pkt['ext']}")
                        download_via_url(page, pkt["href"], file_path)
                        pdf_path = get_pdf_path(file_path, tmp_dir, f"moss_{month_label}")
                        if not pdf_path:
                            errors.append(f"{month_label}: Owner Packet.pdf not found")
                            continue
                        per_property = extract_per_property_from_pdf(pdf_path)
                    except Exception as e:
                        errors.append(f"{month_label}: {e}")
                        continue

                    if not per_property:
                        errors.append(f"{month_label}: no property pages parsed")
                        continue

                    cleanup_yms.add(ym)  # this month now has per-property data
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    for r in per_property:
                        prop = r["property"]
                        if (prop, ym) in existing:
                            print(f"  [{month_label}] {prop} already recorded — skip")
                            skipped += 1
                            continue
                        row, disbursement, net = build_row(pkt, prop, r, now_str)
                        pending.append(row)
                        existing.add((prop, ym))
                        written += 1
                        print(f"  [{month_label}] {prop} -> Disb ${disbursement:,.2f}, Net ${net:,.2f}")

                    # Cabo plug — only fires for months in the plug window.
                    if cabo_should_plug(month_label) and (CABO_PROPERTY, ym) not in existing:
                        pending.append([
                            pkt["date_range"], month_label, CABO_PROPERTY,
                            CABO_DISBURSEMENT_PLUG, 0,
                            0, 0, 0, 0, CABO_DISBURSEMENT_PLUG,
                            "Manual plug (Cabo $2,300/mo through Dec 2026)", now_str,
                        ])
                        existing.add((CABO_PROPERTY, ym))
                        written += 1
                        print(f"  [{month_label}] {CABO_PROPERTY} (Cabo plug) -> ${CABO_DISBURSEMENT_PLUG:,.2f}")

            except Exception as e:
                errors.append(str(e))
                print(f"ERROR: {e}")
                print(traceback.format_exc())

        browser.close()

    # One batched write for all new rows.
    print(f"\nWriting {len(pending)} new row(s)...")
    try:
        append_rows(sheets, "History", pending)
    except Exception as e:
        errors.append(f"append batch: {e}")
        written = 0
        print(f"ERROR appending rows: {e}")
        print(traceback.format_exc())

    # Remove legacy single total rows for every month we imported, in one call.
    removed = 0
    legacy_to_delete = [idx for (idx, ym) in legacy_rows if ym in cleanup_yms]
    try:
        removed = batch_delete_rows(sheets, history_gid, legacy_to_delete)
    except Exception as e:
        errors.append(f"delete legacy totals: {e}")
        print(f"ERROR deleting legacy totals: {e}")
        print(traceback.format_exc())

    print(f"\n=== DONE ===")
    print(f"Rows written:          {written}")
    print(f"Rows skipped (dupe):   {skipped}")
    print(f"Legacy totals removed: {removed}")
    print(f"Errors: {len(errors)}")
    for e in errors:
        print(f"  - {e}")


if __name__ == "__main__":
    main()
