"""
AppFolio Historical Backfill — YALE TOWNHOMES, LLC (per-property).
Paginates through AppFolio Owner Statements for the Yale card and, for every
historical Owner Packet, writes one row PER UNIT (2991/2993/2995/2997/2999) to the
Niron sheet's "Property Detail" tab — mirroring run_yale.py (which it imports for
the parsing + row-building logic, so the two never drift apart).

This NEVER touches the History tab or the consolidated Yale row the dashboard cards
use; it only fills the isolated Property Detail tab. Safe to re-run — it dedups on
(property, month).

Trigger manually via GitHub Actions (backfill_yale.yml) with the months input.
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

from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Reuse the exact parser + row builder + constants from the monthly script so the
# backfill can never diverge from production.
import run_yale as Y

APPFOLIO_URL   = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS  = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID       = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON     = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64    = os.environ.get("APPFOLIO_COOKIES", "")
MAX_MONTHS     = int(os.environ.get("BACKFILL_MONTHS", "18"))

APPFOLIO_OWNER_NAME = Y.APPFOLIO_OWNER_NAME    # "Yale Townhomes, LLC"
DETAIL_TAB    = Y.DETAIL_TAB
DETAIL_HEADER = Y.DETAIL_HEADER

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ── Google Sheets (with backoff + batched writes, mirrors backfill_divando) ──
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


# ── Playwright / cookies / pagination (mirrors backfill_divando.py) ──
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


def main():
    print(f"Starting Yale per-property backfill — up to {MAX_MONTHS} months...")
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
                        file_path = os.path.join(tmp_dir, f"yale_{month_label}{pkt['ext']}")
                        download_via_url(page, pkt["href"], file_path)
                        pdf_path = get_pdf_path(file_path, tmp_dir, f"yale_{month_label}")
                        if not pdf_path:
                            errors.append(f"{month_label}: Owner Packet.pdf not found")
                            continue
                        units, summary = Y.extract_per_unit_from_pdf(pdf_path)
                    except Exception as e:
                        errors.append(f"{month_label}: {e}")
                        continue

                    if not units:
                        errors.append(f"{month_label}: no units parsed")
                        continue

                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    rows = Y.build_rows(units, summary, pkt["date_range"], month_label,
                                        now_str, source="System — Backfill")
                    for row in rows:
                        property_name = row[3]
                        if (property_name, ym) in existing:
                            skipped += 1
                            continue
                        pending.append(row)
                        existing.add((property_name, ym))
                        written += 1
                        print(f"  [{month_label}] {property_name} -> "
                              f"CashIn ${row[4]:,.2f}, Rent ${row[5]:,.2f}, Disb ${row[7]:,.2f}")
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
