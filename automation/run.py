"""
AppFolio Monthly Cashflow Automation
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
SHEET_ID       = os.environ["GOOGLE_SHEET_ID"]
NOTIFY_EMAIL   = os.environ["NOTIFICATION_EMAIL"]
CREDS_JSON     = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64    = os.environ.get("APPFOLIO_COOKIES", "")

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
    result = sheets.values().get(spreadsheetId=SHEET_ID, range=range_name).execute()
    return result.get("values", [])


def append_row(sheets, tab, row):
    sheets.values().append(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def require_approval(sheets):
    rows = read_sheet(sheets, "Settings!B3")
    val = rows[0][0] if rows and rows[0] else "YES"
    return val.strip().upper() != "NO"


def already_recorded(sheets, llc, month_label):
    rows = read_sheet(sheets, "History!A:B")
    for row in rows[1:]:
        if len(row) >= 2 and row[0] == month_label and row[1] == llc:
            return True
    return False


def get_fixed_costs(sheets, llc):
    llc_row_map = {
        "Yale Townhomes, LLC": 7,
        "5070 Donald, LLC": 8,
        "Divando LLC": 9,
        "Dorado LLC": 10,
    }
    row = llc_row_map.get(llc)
    if not row:
        return 0, 0, 0
    data = read_sheet(sheets, f"Settings!B{row}:D{row}")
    if not data or not data[0]:
        return 0, 0, 0
    vals = data[0]
    def parse(v): return float(str(v).replace("$", "").replace(",", "")) if v else 0
    return parse(vals[0] if len(vals) > 0 else 0), \
           parse(vals[1] if len(vals) > 1 else 0) / 12, \
           parse(vals[2] if len(vals) > 2 else 0) / 12


def get_maintenance(sheets, llc, month_label):
    rows = read_sheet(sheets, "Maintenance Log!A:D")
    total = 0.0
    for row in rows[1:]:
        if len(row) < 4:
            continue
        try:
            date = datetime.datetime.strptime(row[0], "%Y-%m-%d")
            if row[1].strip() == llc.strip() and f"{date.year}-{date.month:02d}" == month_label[:7]:
                total += float(str(row[3]).replace("$", "").replace(",", ""))
        except Exception:
            continue
    return total


def extract_from_pdf(pdf_path):
    disbursement = None
    mgmt_fee = None
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
    print("=== PDF TEXT ===")
    print(text[:2000])
    print("================")
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
    if v is not None:
        return v
    if idx + 1 < len(lines):
        return _parse_amount(lines[idx + 1])
    return None


def _parse_amount(text):
    for m in re.findall(r"\(?\$?([\d,]+\.?\d*)\)?", text):
        try:
            return float(m.replace(",", ""))
        except ValueError:
            continue
    return None


def _normalize_cookies(cookies):
    out = []
    for c in cookies:
        cookie = {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain"),
            "path": c.get("path", "/"),
        }
        if "expirationDate" in c:
            cookie["expires"] = int(c["expirationDate"])
        if "httpOnly" in c:
            cookie["httpOnly"] = c["httpOnly"]
        if "secure" in c:
            cookie["secure"] = c["secure"]
        if "sameSite" in c:
            ss = c["sameSite"]
            if ss in ("no_restriction", "unspecified", None):
                cookie["sameSite"] = "None"
            elif ss == "lax":
                cookie["sameSite"] = "Lax"
            elif ss == "strict":
                cookie["sameSite"] = "Strict"
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


def download_packet_for_llc(page, llc, tmp_dir):
    appfolio_name = LLC_MAP.get(llc, llc)
    print(f"\nLooking for: {appfolio_name}")
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
        if not h2:
            continue
        card_name = h2.inner_text().strip()
        if card_name != appfolio_name:
            continue

        print(f"Found card for: {card_name}")

        first_li = card.query_selector("ul.list-group li")
        if not first_li:
            print("No list items in card")
            return None, None

        date_text = first_li.query_selector("b")
        date_range = date_text.inner_text().strip() if date_text else ""
        print(f"Most recent packet: {date_range}")

        month_label = None
        to_match = re.search(r"to\s+(\w+ \d+, \d+)", date_range)
        if to_match:
            try:
                to_date = datetime.datetime.strptime(to_match.group(1), "%b %d, %Y")
                month_label = to_date.strftime("%Y-%m-01")
            except Exception:
                pass

        dl_link = first_li.query_selector(".analytics-statement-download-link a")
        if not dl_link:
            print("No download link found")
            return None, None

        href = dl_link.get_attribute("href") or ""
        ext = ".zip" if ".zip" in href else ".pdf"
        print(f"Downloading ({ext}): {href[:80]}...")

        with page.expect_download() as dl_info:
            dl_link.click()
        download = dl_info.value
        file_path = os.path.join(tmp_dir, f"{llc}{ext}")
        download.save_as(file_path)
        print(f"Saved: {file_path}")
        return file_path, month_label

    print(f"WARNING: No card found for '{appfolio_name}'")
    return None, None


def get_pdf_path(file_path, tmp_dir, llc):
    if file_path.endswith(".pdf"):
        return file_path
    extract_dir = os.path.join(tmp_dir, llc.replace(" ", "_"))
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            print(f"  ZIP contains: {f}")
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    print(f"Owner Packet.pdf not found in ZIP for {llc}")
    return None


def main():
    print("Starting AppFolio automation...")
    sheets  = get_sheets_service()
    results = {}
    errors  = []

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
            for llc in LLC_MAP.keys():
                try:
                    file_path, month_label = download_packet_for_llc(page, llc, tmp_dir)
                    if not file_path or not month_label:
                        errors.append(f"{llc}: Could not download packet")
                        continue

                    if already_recorded(sheets, llc, month_label):
                        print(f"Already recorded {llc} for {month_label}, skipping.")
                        continue

                    pdf_path = get_pdf_path(file_path, tmp_dir, llc)
                    if not pdf_path:
                        errors.append(f"{llc}: Owner Packet.pdf not found")
                        continue

                    disbursement, mgmt_fee = extract_from_pdf(pdf_path)
                    if disbursement is None:
                        errors.append(f"{llc}: Could not extract disbursement from PDF")
                        continue

                    mortgage, tax_mo, ins_mo = get_fixed_costs(sheets, llc)
                    maintenance = get_maintenance(sheets, llc, month_label)
                    net = disbursement - mortgage - tax_mo - ins_mo - maintenance

                    results[llc] = {
                        "month": month_label,
                        "disbursement": disbursement,
                        "mgmt_fee": mgmt_fee or 0,
                        "mortgage": mortgage,
                        "tax_mo": tax_mo,
                        "ins_mo": ins_mo,
                        "maintenance": maintenance,
                        "net": net,
                    }
                    print(f"OK {llc}: Disbursement=${disbursement:,.2f}, Net=${net:,.2f}")

                except Exception as e:
                    errors.append(f"{llc}: {str(e)}\n{traceback.format_exc()}")
                    print(f"ERROR {llc}: {e}")

        browser.close()

    print(f"\nResults: {list(results.keys())}")
    print(f"Errors: {errors}")

    if not results:
        print("Nothing to write.")
        return

    approval = require_approval(sheets)
    tab = "Pending Review" if approval else "History"

    for llc, d in results.items():
        row = [
            d["month"], llc,
            d["disbursement"], d["mgmt_fee"],
            d["mortgage"], d["tax_mo"], d["ins_mo"],
            d["maintenance"], "",
            "System — Automation",
        ]
        append_row(sheets, tab, row)
        print(f"Written to {tab}: {llc}")


if __name__ == "__main__":
    main()
