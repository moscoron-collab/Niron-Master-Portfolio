# AppFolio automation script
"""
AppFolio Monthly Cashflow Automation
Downloads Owner Packets for each LLC, extracts disbursement data,
and writes to Google Sheets (History or Pending Review tab).
"""

import os
import re
import json
import base64
import zipfile
import tempfile
import datetime
import traceback
from pathlib import Path

import pdfplumber
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Configuration ────────────────────────────────────────────────────
APPFOLIO_URL    = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL  = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS   = os.environ["APPFOLIO_PASSWORD"]
SHEET_ID        = os.environ["GOOGLE_SHEET_ID"]
NOTIFY_EMAIL    = os.environ["NOTIFICATION_EMAIL"]
CREDS_JSON      = os.environ["GOOGLE_CREDENTIALS_JSON"]
COOKIES_B64     = os.environ.get("APPFOLIO_COOKIES", "")

LLCS = [
    "Yale Townhomes, LLC",
    "5070 Donald, LLC",
    "Divando LLC",
    "Dorado LLC",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]


# ── Google Sheets helpers ─────────────────────────────────────────────
def get_sheets_service():
    creds_info = json.loads(CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def get_gmail_service():
    creds_info = json.loads(CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("gmail", "v1", credentials=creds)


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


def get_setting(sheets, cell):
    rows = read_sheet(sheets, f"Settings!{cell}")
    if rows and rows[0]:
        return rows[0][0]
    return ""


def require_approval(sheets):
    val = get_setting(sheets, "B3")
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
    mortgage   = float(str(vals[0]).replace("$","").replace(",","")) if len(vals) > 0 and vals[0] else 0
    tax_annual = float(str(vals[1]).replace("$","").replace(",","")) if len(vals) > 1 and vals[1] else 0
    ins_annual = float(str(vals[2]).replace("$","").replace(",","")) if len(vals) > 2 and vals[2] else 0
    return mortgage, tax_annual / 12, ins_annual / 12


def get_maintenance(sheets, llc, month_label):
    rows = read_sheet(sheets, "Maintenance Log!A:D")
    total = 0.0
    for row in rows[1:]:
        if len(row) < 4:
            continue
        date_str, row_llc, _, amount_str = row[0], row[1], row[2], row[3]
        if row_llc.strip() != llc.strip():
            continue
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if f"{date.year}-{date.month:02d}" == month_label[:7]:
                total += float(str(amount_str).replace("$","").replace(",",""))
        except Exception:
            continue
    return total


# ── PDF extraction ───────────────────────────────────────────────────
def extract_from_pdf(pdf_path):
    disbursement = None
    mgmt_fee = None
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        low = line.lower()
        if "owner disbursement" in low:
            disbursement = extract_amount(line, lines, i)
        if "management fee" in low:
            mgmt_fee = extract_amount(line, lines, i)
    return disbursement, mgmt_fee


def extract_amount(line, lines, idx):
    amount = find_amount_in_text(line)
    if amount is not None:
        return amount
    if idx + 1 < len(lines):
        return find_amount_in_text(lines[idx + 1])
    return None


def find_amount_in_text(text):
    matches = re.findall(r"\(?\$?([\d,]+\.?\d*)\)?", text)
    for m in matches:
        try:
            return float(m.replace(",", ""))
        except ValueError:
            continue
    return None


# ── AppFolio browser automation ──────────────────────────────────────
def load_cookies():
    if not COOKIES_B64:
        return []
    try:
        return json.loads(base64.b64decode(COOKIES_B64).decode())
    except Exception:
        return []


def save_cookies(context):
    cookies = context.cookies()
    encoded = base64.b64encode(json.dumps(cookies).encode()).decode()
    print(f"::set-output name=new_cookies::{encoded}")


def login(page):
    print("Logging in to AppFolio...")
    page.goto(APPFOLIO_URL)
    page.wait_for_load_state("networkidle")
    if "log_in" not in page.url:
        print("Already logged in via cookies.")
        return
    page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
    page.fill("input[name='user[password]']", APPFOLIO_PASS)
    page.click("input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Login complete.")


def download_packet_for_llc(page, llc, tmp_dir):
    print(f"Looking for packet: {llc}")
    page.goto("https://laureatetld.appfolio.com/oportal/statements")
    page.wait_for_load_state("networkidle")
    rows = page.query_selector_all("tr")
    for row in rows:
        text = row.inner_text()
        if llc in text and "Download" in text:
            link = row.query_selector("a[href*='download']") or row.query_selector("a")
            if link:
                with page.expect_download() as dl_info:
                    link.click()
                download = dl_info.value
                zip_path = os.path.join(tmp_dir, f"{llc}.zip")
                download.save_as(zip_path)
                print(f"Downloaded packet for {llc}")
                return zip_path
    print(f"WARNING: No download found for {llc}")
    return None


def extract_owner_packet(zip_path, tmp_dir, llc):
    extract_dir = os.path.join(tmp_dir, llc.replace(" ", "_"))
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower() == "owner packet.pdf":
                return os.path.join(root, f)
    print(f"WARNING: Owner Packet.pdf not found in ZIP for {llc}")
    return None


# ── Email notification ───────────────────────────────────────────────
def send_email(subject, body):
    try:
        gmail = get_gmail_service()
        msg = MIMEMultipart()
        msg["To"] = NOTIFY_EMAIL
        msg["From"] = "serviceaccount@appfolio-automation"
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Email failed (non-fatal): {e}")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    today = datetime.date.today()
    if today.day < 5:
        first = today.replace(day=1)
        last_month = first - datetime.timedelta(days=1)
        target = last_month
    else:
        target = today

    month_label   = target.strftime("%Y-%m-01")
    month_display = target.strftime("%B %Y")

    print(f"Processing month: {month_display}")

    sheets  = get_sheets_service()
    results = {}
    errors  = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        login(page)
        save_cookies(context)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for llc in LLCS:
                try:
                    if already_recorded(sheets, llc, month_label):
                        print(f"Already recorded for {llc}, skipping.")
                        continue
                    zip_path = download_packet_for_llc(page, llc, tmp_dir)
                    if not zip_path:
                        errors.append(f"{llc}: Could not find download link")
                        continue
                    pdf_path = extract_owner_packet(zip_path, tmp_dir, llc)
                    if not pdf_path:
                        errors.append(f"{llc}: Owner Packet.pdf not found in ZIP")
                        continue
                    disbursement, mgmt_fee = extract_from_pdf(pdf_path)
                    if disbursement is None:
                        errors.append(f"{llc}: Could not extract Owner Disbursements from PDF")
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
                    print(f"{llc}: Disbursement=${disbursement:,.2f}, Net=${net:,.2f}")
                except Exception as e:
                    errors.append(f"{llc}: {str(e)}\n{traceback.format_exc()}")

        browser.close()

    if not results and not errors:
        print("No new data to process.")
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

    if errors:
        send_email(
            f"⚠️ AppFolio Automation — Errors ({month_display})",
            f"<p>Errors during {month_display}:</p><pre>{'<br>'.join(errors)}</pre>"
            f"<p>Processed: {', '.join(results.keys()) or 'none'}</p>"
        )
    elif approval:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
        send_email(
            f"📋 AppFolio Data Ready for Review — {month_display}",
            f"<p>Data for <b>{month_display}</b> is in <b>Pending Review</b>.</p>"
            f"<p><a href='{sheet_url}'>Click here to review and approve</a></p>"
            f"<p>LLCs: {', '.join(results.keys())}</p>"
        )
    else:
        send_email(
            f"✅ AppFolio Data Saved — {month_display}",
            f"<p>Data for <b>{month_display}</b> saved to History.</p>"
            f"<p>LLCs: {', '.join(results.keys())}</p>"
        )


if __name__ == "__main__":
    main()
