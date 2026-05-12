"""
AppFolio Historical Backfill — downloads the last N months of packets per LLC
and writes directly to History.
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
SHEET_ID        = os.environ["GOOGLE_SHEET_ID"]
CREDS_JSON      = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64     = os.environ.get("APPFOLIO_COOKIES", "")
MAX_MONTHS      = int(os.environ.get("BACKFILL_MONTHS", "12"))

LLC_MAP = {
    "Yale Townhomes, LLC": "Yale Townhomes, LLC",
    "5070 Donald, LLC":    "5070 Donald, LLC",
    "Divando LLC":         "Divando, LLC",
    "Dorado LLC":          "Dorado Investment Group LLC",
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
    rows = read_sheet(sheets, "History!A:C")
    for row in rows[1:]:
        if len(row) >= 3 and row[1] == month_label and row[2] == llc:
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
    print(f"Current URL after navigate: {page.url}")
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    print("Cookies invalid — logging in with credentials...")
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")
    print(f"URL after login submit: {page.url}")


def collect_packets(page, appfolio_name, max_count):
    print(f"  Navigating to statements page...")
    page.goto("https://laureatetld.appfolio.com/oportal/statements")
    page.wait_for_load_state("networkidle")
    print(f"  Statements page URL: {page.url}")
    try:
        page.wait_for_selector("#statements-root .card", timeout=20000)
    except Exception:
        print("  WARNING: Timed out waiting for cards")

    cards = page.query_selector_all(".card")
    print(f"  Total cards on page: {len(cards)}")
    for card in cards:
        h2 = card.query_selector("h2.card-title")
        if not h2:
            continue
        card_name = h2.inner_text().strip()
        if card_name != appfolio_name:
            continue

        items = card.query_selector_all("ul.list-group li")
        print(f"  Found matching card with {len(items)} items")
        packets = []
        for li in items[:max_count]:
            date_text = li.query_selector("b")
            date_range = date_text.inner_text().strip() if date_text else ""
            if not re.search(r"\w+ \d+, \d+ to \w+ \d+, \d+", date_range):
                continue

            month_label = None
            m = re.search(r"to\s+(\w+ \d+, \d+)", date_range)
            if m:
                try:
                    to_date = datetime.datetime.strptime(m.group(1), "%b %d, %Y")
                    month_label = to_date.strftime("%Y-%m-01")
                except Exception:
                    continue

            dl_link = li.query_selector(".analytics-statement-download-link a")
            if not dl_link: continue
            href = dl_link.get_attribute("href") or ""
            ext = ".zip" if ".zip" in href else ".pdf"

            packets.append({
                "date_range": date_range,
                "month_label": month_label,
                "href": href,
                "ext": ext,
                "element": dl_link,
            })
        return packets
    return []


def download_packet(page, packet, tmp_dir, name_prefix):
    with page.expect_download() as dl_info:
        packet["element"].click()
    download = dl_info.value
    file_path = os.path.join(tmp_dir, f"{name_prefix}{packet['ext']}")
    download.save_as(file_path)
    return file_path


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
    print(f"Starting backfill — up to {MAX_MONTHS} months per LLC...")
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
                    print(f"  Found {len(packets)} valid packets for {llc}")

                    for idx, pkt in enumerate(packets):
                        if not pkt["month_label"]:
                            continue
                        if already_recorded(sheets, llc, pkt["month_label"]):
                            print(f"  [{pkt['month_label']}] already in History — skip")
                            skipped += 1
                            continue

                        print(f"  [{pkt['month_label']}] downloading...")
                        packets_fresh = collect_packets(page, appfolio_name, MAX_MONTHS)
                        if idx >= len(packets_fresh): continue
                        fresh_pkt = packets_fresh[idx]

                        file_path = download_packet(page, fresh_pkt, tmp_dir, f"{llc}_{pkt['month_label']}")
                        pdf_path  = get_pdf_path(file_path, tmp_dir, f"{llc}_{pkt['month_label']}")
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
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
