"""
AppFolio Monthly Cashflow Automation — MOSS INVESTMENTS, LLC version.
Pulls the most recent Owner Packet from AppFolio, extracts disbursement
+ mgmt fee, and writes a row to the Moss Google Sheet's Pending Review
(or History if approval is OFF). Forked from run.py.
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

# Only one LLC for Moss. Left as a map for parity with the Niron version.
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


def require_approval(sheets):
    rows = read_sheet(sheets, "Settings!B3")
    val = rows[0][0] if rows and rows[0] else "YES"
    return val.strip().upper() != "NO"


def already_recorded(sheets, llc, month_label):
    rows = read_sheet(sheets, "History!A:C")
    for row in rows[1:]:
        if len(row) >= 3 and row[1] == month_label and row[2] == llc:
            return True
    return False


def get_fixed_costs(sheets, llc):
    rows = read_sheet(sheets, "Settings!A:D")
    def parse(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0
    for row in rows:
        if row and row[0].strip() == llc.strip():
            mortgage   = parse(row[1]) if len(row) > 1 else 0
            tax_annual = parse(row[2]) if len(row) > 2 else 0
            ins_annual = parse(row[3]) if len(row) > 3 else 0
            return mortgage, tax_annual / 12, ins_annual / 12
    print(f"WARNING: LLC '{llc}' not found in Settings tab")
    return 0, 0, 0


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
        if not h2 or h2.inner_text().strip() != appfolio_name:
            continue
        print(f"Found card for: {appfolio_name}")
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
        print(f"Downloading ({ext}): {href[:80]}...")
        with page.expect_download() as dl_info:
            dl_link.click()
        download = dl_info.value
        file_path = os.path.join(tmp_dir, f"{llc}{ext}")
        download.save_as(file_path)
        print(f"Saved: {file_path}")
        return file_path, month_label, date_range

    print(f"WARNING: No card found for '{appfolio_name}'")
    return None, None, None


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
    return None


def main():
    print("Starting AppFolio automation (Moss)...")
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
                    file_path, month_label, date_range = download_packet_for_llc(page, llc, tmp_dir)
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
                        "date_range": date_range, "month": month_label,
                        "disbursement": disbursement, "mgmt_fee": mgmt_fee or 0,
                        "mortgage": mortgage, "tax_mo": tax_mo, "ins_mo": ins_mo,
                        "maintenance": maintenance, "net": net,
                    }
                    print(f"OK {llc}: Disbursement=${disbursement:,.2f}, Net=${net:,.2f}")
                except Exception as e:
                    errors.append(f"{llc}: {str(e)}")
                    print(f"ERROR {llc}: {e}")
                    print(traceback.format_exc())
        browser.close()

    print(f"\nResults: {list(results.keys())}")
    print(f"Errors: {errors}")

    if not results:
        print("Nothing to write.")
        return

    approval = require_approval(sheets)
    tab = "Pending Review" if approval else "History"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for llc, d in results.items():
        row = [
            d["date_range"], d["month"], llc,
            d["disbursement"], d["mgmt_fee"],
            d["mortgage"], d["tax_mo"], d["ins_mo"],
            d["maintenance"], d["net"],
            "System — Automation", now_str,
        ]
        append_row(sheets, tab, row)
        print(f"Written to {tab}: {llc}")


if __name__ == "__main__":
    main()
