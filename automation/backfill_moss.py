"""
AppFolio Historical Backfill — MOSS INVESTMENTS, LLC version.
Paginates through AppFolio Owner Statements for Moss and writes up to
N monthly packets directly to the Moss sheet's History tab. Forked from
backfill.py. Trigger manually via GitHub Actions with the months input.
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
MAX_MONTHS      = int(os.environ.get("BACKFILL_MONTHS", "12"))

LLC_MAP = {
    "Moss Investments, LLC": "Moss Investments, LLC",
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


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


def already_recorded(sheets, llc, month_label):
    """Robust check that handles different date formats in column B."""
    rows = read_sheet(sheets, "History!A:C")
    target_ym = month_label[:7]
    for row in rows[1:]:
        if len(row) < 3 or row[2].strip() != llc.strip():
            continue
        period = str(row[1]).strip()
        matched = False
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                d = datetime.datetime.strptime(period, fmt)
                if d.strftime("%Y-%m") == target_ym:
                    matched = True
                break
            except ValueError:
                continue
        if matched or target_ym in period:
            return True
    return False


def get_fixed_costs(sheets, llc):
    rows = read_sheet(sheets, "Settings!A:D")
    def parse(v):
        try: return float(str(v).replace("$","").replace(",","").strip())
        except (ValueError, AttributeError): return 0
    for row in rows:
        if row and row[0].strip() == llc.strip():
            mortgage   = parse(row[1]) if len(row) > 1 else 0
            tax_annual = parse(row[2]) if len(row) > 2 else 0
            ins_annual = parse(row[3]) if len(row) > 3 else 0
            return mortgage, tax_annual / 12, ins_annual / 12
    return 0, 0, 0


def extract_from_pdf(pdf_path):
    disbursement = None
    mgmt_fee = None
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        low = line.lower()
        if "owner disbursement" in low:
            disbursement = _find_amount(line, lines, i)
        if "management fee" in low:
            mgmt_fee = _find_amount(line, lines, i)
    return disbursement, mgmt_fee


def _find_amount(line, lines, idx):
    v = _parse_amount(line)
    if v is not None: return v
    if idx + 1 < len(lines): return _parse_amount(lines[idx + 1])
    return None


def _parse_amount(text):
    for m in re.findall(r"\(?\$?([\d,]+\.?\d*)\)?", text):
        try: return float(m.replace(",", ""))
        except ValueError: continue
    return None


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
    """Click the 'next page' button within the specified LLC's card."""
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
    max_pages = (max_count // 4) + 3

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


def main():
    print(f"Starting Moss backfill — up to {MAX_MONTHS} months per LLC...")
    sheets  = get_sheets_service()
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
            for llc, appfolio_name in LLC_MAP.items():
                print(f"\n=== {llc} ({appfolio_name}) ===")
                try:
                    packets = collect_packets(page, appfolio_name, MAX_MONTHS)
                    print(f"  Collected {len(packets)} monthly packets")

                    for pkt in packets:
                        if already_recorded(sheets, llc, pkt["month_label"]):
                            print(f"  [{pkt['month_label']}] already in History — skip")
                            skipped += 1
                            continue

                        print(f"  [{pkt['month_label']}] downloading...")
                        file_path = os.path.join(tmp_dir, f"{llc}_{pkt['month_label']}{pkt['ext']}")
                        try:
                            download_via_url(page, pkt["href"], file_path)
                        except Exception as e:
                            errors.append(f"{llc} {pkt['month_label']}: {e}")
                            continue

                        pdf_path = get_pdf_path(file_path, tmp_dir, f"{llc}_{pkt['month_label']}")
                        if not pdf_path:
                            errors.append(f"{llc} {pkt['month_label']}: PDF not found")
                            continue

                        disbursement, mgmt_fee = extract_from_pdf(pdf_path)
                        if disbursement is None:
                            errors.append(f"{llc} {pkt['month_label']}: no disbursement")
                            continue

                        mortgage, tax_mo, ins_mo = get_fixed_costs(sheets, llc)
                        net = disbursement - mortgage - tax_mo - ins_mo

                        row = [
                            pkt["date_range"], pkt["month_label"], llc,
                            disbursement, mgmt_fee or 0,
                            mortgage, tax_mo, ins_mo, 0, net,
                            "System — Backfill",
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                        append_row(sheets, "History", row)
                        written += 1
                        print(f"  OK Disbursement=${disbursement:,.2f} Net=${net:,.2f}")

                except Exception as e:
                    errors.append(f"{llc}: {e}")
                    print(f"ERROR {llc}: {e}")
                    print(traceback.format_exc())

        browser.close()

    print(f"\n=== DONE ===")
    print(f"Written: {written}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {len(errors)}")
    for e in errors: print(f"  - {e}")


if __name__ == "__main__":
    main()
