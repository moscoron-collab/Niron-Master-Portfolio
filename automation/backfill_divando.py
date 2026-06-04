"""
AppFolio Historical Backfill — DIVANDO LLC (per-property).
Paginates through AppFolio Owner Statements for the Divando card and, for every
historical Owner Packet, writes one row PER PROPERTY to the Niron sheet's
"Property Detail" tab — mirroring run_divando.py.

This NEVER touches the History tab or the consolidated Divando rows the dashboard
cards use; it only fills the isolated Property Detail tab. Safe to re-run — it
dedups on (property, month).

Trigger manually via GitHub Actions (backfill_divando.yml) with the months input.
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

APPFOLIO_URL   = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS  = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID       = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON     = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64    = os.environ.get("APPFOLIO_COOKIES", "")
MAX_MONTHS     = int(os.environ.get("BACKFILL_MONTHS", "18"))

APPFOLIO_OWNER_NAME = "Divando, LLC"
LLC_NAME = "Divando, LLC"

DETAIL_TAB = "Property Detail"
DETAIL_HEADER = [
    "Date Range", "Month", "LLC", "Property",
    "Cash In", "Rent Collected", "Mgmt Fee", "Disbursement",
    "Mortgage", "Insurance/12", "Status", "Source", "Updated",
]

# Kept in sync with run_divando.py.
PROPERTY_CODE_MAP = {
    "13TH,15655":        "15655 E 13th Pl",
    "13TH,15675":        "15675 E 13th Pl",
    "43RD,14790":        "14790 E 43rd Ave",
    "BATES,15559 LOWER": "15559 E Bates Ave Lower",
    "BATES,15559 UPPER": "15559 E Bates Ave Upper",
    # AppFolio abbreviated the upper unit as "BAT, 15559 Upper" in older months
    # (Dec 2024–May 2025). Alias both abbreviations to the same canonical addresses.
    "BAT,15559 LOWER":   "15559 E Bates Ave Lower",
    "BAT,15559 UPPER":   "15559 E Bates Ave Upper",
    "BLACK,4776":        "4776 Blackhawk Way",
    "BOSTO,1724":        "1724 Boston St",
    "CROWN,5101A":       "5101 Crown Blvd Unit A",
    "CROWN,5101B":       "5101 Crown Blvd Unit B",
    "DEAR,5538":         "5538 Dearborn St",
    "HOLLY,3630":        "3630 Holly St",
    "IDALI,1310":        "1310 Idalia Ct",
    "OAK,2332":          "2332 Oakland St",
    "TUCSO,3225":        "3225 Tucson St",
    "VIRG,11795":        "11795 E Virginia Dr",
}

DIVANDO_FIXED_COSTS = {
    "15655 E 13th Pl":          {"mortgage": 784.30,   "ins_mo": 98.03},
    "15675 E 13th Pl":          {"mortgage": 784.30,   "ins_mo": 98.03},
    "1310 Idalia Ct":           {"mortgage": 784.30,   "ins_mo": 98.03},
    "14790 E 43rd Ave":         {"mortgage": 859.18,   "ins_mo": 220.17},
    "15559 E Bates Ave Lower":  {"mortgage": 429.59,   "ins_mo": 104.46},
    "15559 E Bates Ave Upper":  {"mortgage": 429.59,   "ins_mo": 104.46},
    "4776 Blackhawk Way":       {"mortgage": 1007.39,  "ins_mo": 276.67},
    "1724 Boston St":           {"mortgage": 845.28,   "ins_mo": 197.00},
    "5101 Crown Blvd Unit A":   {"mortgage": 503.70,   "ins_mo": 112.58},
    "5101 Crown Blvd Unit B":   {"mortgage": 503.69,   "ins_mo": 112.58},
    "5538 Dearborn St":         {"mortgage": 1157.92,  "ins_mo": 217.50},
    "3630 Holly St":            {"mortgage": 1053.71,  "ins_mo": 224.42},
    "2332 Oakland St":          {"mortgage": 1053.71,  "ins_mo": 217.67},
    "3225 Tucson St":           {"mortgage": 845.28,   "ins_mo": 187.92},
    "11795 E Virginia Dr":      {"mortgage": 1157.92,  "ins_mo": 203.58},
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ── Google Sheets (with backoff + batched writes, mirrors backfill_moss) ──
def get_sheets_service():
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def _execute(request, what="API call"):
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


def ensure_detail_tab(sheets):
    meta = _execute(sheets.get(spreadsheetId=SHEET_ID, fields="sheets(properties(title))"),
                    "get metadata")
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if DETAIL_TAB in titles:
        return
    print(f"Creating '{DETAIL_TAB}' tab...")
    _execute(sheets.batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": [{"addSheet": {"properties": {"title": DETAIL_TAB}}}]},
    ), "create tab")
    append_rows(sheets, DETAIL_TAB, [DETAIL_HEADER])


def _period_to_ym(period_val):
    period = str(period_val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(period, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.match(r"(\d{4})[-/](\d{2})", period)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def scan_detail(sheets):
    """Existing (property, 'YYYY-MM') pairs already in Property Detail, for dedup."""
    rows = read_sheet(sheets, f"'{DETAIL_TAB}'!A:D")
    existing = set()
    for idx, row in enumerate(rows):
        if idx == 0 or len(row) < 4:
            continue
        ym = _period_to_ym(row[1])
        if ym:
            existing.add((row[3].strip(), ym))
    return existing


# ── PDF parsing (identical logic to run_divando.py) ──────────────────
def _parse_amount(text):
    m = re.search(r"-?\(?\$?([\d,]+\.\d{2})\)?", text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _summary_value(lines, label):
    for ln in lines:
        s = ln.strip()
        if s.startswith(label):
            return _parse_amount(s)
    return None


def _match_code(header):
    # Whitespace/case-insensitive so 'BATES, 15559 LOWER' (AppFolio prints a space
    # after the comma) and 'Upper' still match the 'BATES,15559 LOWER'/'UPPER' keys.
    code_part = re.sub(r"\s+", "", header.split(" - ")[0]).upper()
    for code, canonical in PROPERTY_CODE_MAP.items():
        if code_part == re.sub(r"\s+", "", code).upper():
            return canonical
    return None


def extract_per_property_from_pdf(pdf_path):
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
                # Surface real misses (a property page we failed to match) instead of
                # skipping silently — that silence is why Bates went unnoticed.
                if "Consolidated Summary" not in text:
                    print(f"  Page {page_idx + 1}: '{header[:50]}' — no code match, skipped")
                continue
            cash_in      = _summary_value(lines, "Cash In") or 0.0
            mgmt_fee      = _summary_value(lines, "Management Fees") or 0.0
            disbursement = _summary_value(lines, "Owner Disbursements") or 0.0
            occupied     = "Rent Income" in text
            results.append({
                "property":       canonical,
                "cash_in":        cash_in,
                "rent_collected": cash_in if occupied else 0.0,
                "mgmt_fee":       mgmt_fee,
                "disbursement":   disbursement,
                "occupied":       occupied,
            })
    return results


# ── Playwright / cookies / pagination (mirrors backfill_moss.py) ─────
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
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    print("Logging in with credentials...")
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")


def parse_packet_li(li):
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
    cards = page.query_selector_all(".card")
    if card_idx >= len(cards):
        return False
    card = cards[card_idx]
    for btn in card.query_selector_all(".pagination li.page-item button"):
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
    print("  Navigating to statements page...")
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

    all_packets = []
    seen = set()
    page_num = 1
    max_pages = (max_count // 4) + 3

    while len(all_packets) < max_count and page_num <= max_pages:
        cards = page.query_selector_all(".card")
        if card_idx >= len(cards):
            break
        items = cards[card_idx].query_selector_all("ul.list-group li")
        print(f"  Page {page_num}: {len(items)} items")
        new_added = 0
        for li in items:
            data = parse_packet_li(li)
            if not data or data.get("skip"):
                continue
            if data["month_label"] in seen:
                continue
            seen.add(data["month_label"])
            all_packets.append(data)
            new_added += 1
            if len(all_packets) >= max_count:
                break
        if len(all_packets) >= max_count or new_added == 0:
            break
        if not click_next_page(page, card_idx):
            break
        page.wait_for_timeout(2000)
        page_num += 1

    return all_packets


def download_via_url(page, url, file_path):
    if url.startswith("/"):
        url = "https://laureatetld.appfolio.com" + url
    response = page.context.request.get(url)
    if response.status >= 400:
        raise Exception(f"Download failed with HTTP {response.status}")
    with open(file_path, "wb") as f:
        f.write(response.body())


def get_pdf_path(file_path, tmp_dir, name):
    if file_path.endswith(".pdf"):
        return file_path
    extract_dir = os.path.join(tmp_dir, name.replace(" ", "_"))
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    return None


def build_row(pkt, r, now_str):
    fixed = DIVANDO_FIXED_COSTS.get(r["property"], {"mortgage": 0, "ins_mo": 0})
    return [
        pkt["date_range"], pkt["month_label"], LLC_NAME, r["property"],
        r["cash_in"], r["rent_collected"], r["mgmt_fee"], r["disbursement"],
        fixed["mortgage"], fixed["ins_mo"],
        "Occupied" if r["occupied"] else "Vacant",
        "System — Backfill", now_str,
    ]


def main():
    print(f"Starting Divando per-property backfill — up to {MAX_MONTHS} months...")
    sheets = get_sheets_service()
    ensure_detail_tab(sheets)
    existing = scan_detail(sheets)
    print(f"Property Detail has {len(existing)} (property, month) entries.")

    pending = []
    written = 0
    skipped = 0
    errors = []

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
                        file_path = os.path.join(tmp_dir, f"divando_{month_label}{pkt['ext']}")
                        download_via_url(page, pkt["href"], file_path)
                        pdf_path = get_pdf_path(file_path, tmp_dir, f"divando_{month_label}")
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

                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for r in per_property:
                        if (r["property"], ym) in existing:
                            skipped += 1
                            continue
                        pending.append(build_row(pkt, r, now_str))
                        existing.add((r["property"], ym))
                        written += 1
                        print(f"  [{month_label}] {r['property']} -> "
                              f"CashIn ${r['cash_in']:,.2f}, Disb ${r['disbursement']:,.2f}")
            except Exception as e:
                errors.append(str(e))
                print(traceback.format_exc())

        browser.close()

    print(f"\nWriting {len(pending)} new row(s)...")
    try:
        append_rows(sheets, DETAIL_TAB, pending)
    except Exception as e:
        errors.append(f"append batch: {e}")
        written = 0
        print(traceback.format_exc())

    print("\n=== DONE ===")
    print(f"Rows written:        {written}")
    print(f"Rows skipped (dupe): {skipped}")
    print(f"Errors: {len(errors)}")
    for e in errors:
        print(f"  - {e}")


if __name__ == "__main__":
    main()
