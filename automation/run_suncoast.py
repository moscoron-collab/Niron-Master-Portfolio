#!/usr/bin/env python3
"""
Monthly pull from Propertyware for:
  Suncoast Property Management (Jacksonville) — 8222 Hare Ave
  Mid South Best Rentals (Memphis)            — 3899 Joest Rd, 6580 Stockport Dr

Both accounts share the same email but have different passwords.
Net cashflow = Net Operating Income (mgmt fees + repairs already deducted by manager).
No mortgage, no insurance on any of these properties.
"""

import os, re, json, base64, datetime, tempfile, time
import pdfplumber
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

PROPERTYWARE_URL  = "https://app.propertyware.com/pw/index.html"
DOCS_HASH         = "#/ownerportal/opdocuments"

EMAIL            = os.environ["SUNCOAST_EMAIL"]
JAX_PASSWORD     = os.environ["SUNCOAST_PASSWORD"]
MEMPHIS_PASSWORD = os.environ["MIDSOUTH_PASSWORD"]
SHEET_ID         = os.environ["GOOGLE_SHEET_ID"]
CREDS_B64        = os.environ["GOOGLE_CREDENTIALS_JSON"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

JAX_PROPERTY      = "8222 Hare Ave"
MEMPHIS_PROPERTIES = ["3899 Joest Rd", "6580 Stockport Dr"]


# ── Google Sheets helpers ─────────────────────────────────────────────────────

def sheets_client():
    info  = json.loads(base64.b64decode(CREDS_B64))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def read_range(svc, rng):
    return svc.values().get(spreadsheetId=SHEET_ID, range=rng).execute().get("values", [])


def already_recorded(svc, llc, month_label):
    for tab in ("History", "Pending Review"):
        for row in read_range(svc, f"'{tab}'!A:C")[1:]:
            if len(row) >= 3 and row[1] == month_label and row[2] == llc:
                return True
    return False


def append_row(svc, row):
    svc.values().append(
        spreadsheetId=SHEET_ID,
        range="History!A:Z",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()


# ── Playwright: login + download PDF ─────────────────────────────────────────

def download_statement(email, password, download_dir):
    """Log into Propertyware, download the most recent Owner Statement PDF."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx  = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        page.goto(PROPERTYWARE_URL)
        page.wait_for_selector('input[type="password"]', timeout=30_000)

        # Fill email — try common input patterns
        for sel in [
            'input[type="email"]',
            'input[name="username"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="user" i]',
        ]:
            if page.locator(sel).count():
                page.locator(sel).first.fill(email)
                break

        page.locator('input[type="password"]').first.fill(password)

        # Submit
        for sel in [
            'button[type="submit"]',
            'button:has-text("Log In")',
            'button:has-text("Sign In")',
            'button:has-text("Login")',
        ]:
            if page.locator(sel).count():
                page.locator(sel).first.click()
                break

        # Wait for portal to load then navigate to documents
        page.wait_for_url("**/ownerportal/**", timeout=60_000)
        page.goto(f"{PROPERTYWARE_URL}{DOCS_HASH}")
        page.wait_for_selector("table tbody tr", timeout=30_000)
        time.sleep(2)  # let React finish rendering rows

        # Click first Download PDF button (most recent statement)
        with page.expect_download(timeout=30_000) as dl_info:
            for sel in [
                "table tbody tr:first-child td:nth-child(3) a",
                "table tbody tr:first-child a[href*='download']",
                "table tbody tr:first-child button",
                "table tbody tr:first-child td a",
            ]:
                locs = page.locator(sel)
                if locs.count():
                    locs.first.click()
                    break

        dl   = dl_info.value
        dest = os.path.join(download_dir, dl.suggested_filename or "statement.pdf")
        dl.save_as(dest)
        browser.close()

    print(f"  Downloaded: {os.path.basename(dest)}")
    return dest


# ── PDF parsing helpers ───────────────────────────────────────────────────────

def parse_period(text):
    """Return (date_range_str, month_label) from 'Report Period: MM/DD/YYYY - MM/DD/YYYY'."""
    m = re.search(
        r'Report Period:\s*(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})', text
    )
    if not m:
        return None, None
    start      = datetime.datetime.strptime(m.group(1), "%m/%d/%Y")
    date_range = f"{m.group(1)} - {m.group(2)}"
    month_label = start.strftime("%Y-%m-01")
    return date_range, month_label


def parse_jax_pdf(pdf_path):
    """
    Suncoast (Jacksonville) PDF — single property, repeated for each owner name copy.
    Reads the portfolio summary page (Month-To-Date Net Income) from the first copy only.
    """
    date_range = month_label = None
    net_income = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            if not date_range:
                date_range, month_label = parse_period(text)

            # Portfolio summary page has "Net Income  $X.XX  $Y.YY" (M-T-D  Y-T-D)
            if net_income is None and "Net Income" in text and "Total Income" in text:
                m = re.search(r'Net Income\s+\$?([\d,]+\.\d{2})', text)
                if m:
                    net_income = float(m.group(1).replace(",", ""))
                    break  # stop after first copy

    return date_range, month_label, {JAX_PROPERTY: net_income}


def parse_memphis_pdf(pdf_path):
    """
    Mid South Best Rentals (Memphis) PDF — 3 pages.
    Page 1: portfolio summary (skip).
    Page 2: 3899 Joest Rd   — Net Operating Income.
    Page 3: 6580 Stockport Dr — Net Operating Income.
    """
    date_range = month_label = None
    results = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            if not date_range:
                date_range, month_label = parse_period(text)

            for prop in MEMPHIS_PROPERTIES:
                if prop in results:
                    continue
                if re.search(rf'^\s*{re.escape(prop)}\b', text, re.MULTILINE):
                    m = re.search(r'Net Operating Income\s+\$?([\d,]+\.\d{2})', text)
                    if m:
                        results[prop] = float(m.group(1).replace(",", ""))

    return date_range, month_label, results


# ── Main ──────────────────────────────────────────────────────────────────────

def save_results(svc, date_range, month_label, data, now_str):
    for prop, net_income in data.items():
        if net_income is None:
            print(f"  ERROR: could not parse net income for {prop}")
            continue
        if already_recorded(svc, prop, month_label):
            print(f"  Already recorded: {prop} {month_label} — skipping")
            continue
        row = [
            date_range, month_label, prop,
            net_income, 0,      # disbursement, mgmt_fee (already netted out)
            0, 0, 0,            # mortgage, tax_mo, ins_mo
            0, net_income,      # maintenance, net_cashflow
            "System — Automation", now_str,
        ]
        append_row(svc, row)
        print(f"  Saved: {prop} {month_label} → ${net_income:,.2f}")


def main():
    svc     = sheets_client()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with tempfile.TemporaryDirectory() as tmpdir:

        print("=== Jacksonville (Suncoast Property Management) ===")
        jax_pdf = download_statement(EMAIL, JAX_PASSWORD, tmpdir)
        date_range, month_label, jax_data = parse_jax_pdf(jax_pdf)
        print(f"  Period: {date_range}  →  {month_label}")
        print(f"  Parsed: {jax_data}")
        save_results(svc, date_range, month_label, jax_data, now_str)

        print("\n=== Memphis (Mid South Best Rentals) ===")
        memphis_pdf = download_statement(EMAIL, MEMPHIS_PASSWORD, tmpdir)
        date_range_m, month_label_m, memphis_data = parse_memphis_pdf(memphis_pdf)
        print(f"  Period: {date_range_m}  →  {month_label_m}")
        print(f"  Parsed: {memphis_data}")
        save_results(svc, date_range_m, month_label_m, memphis_data, now_str)


if __name__ == "__main__":
    main()
