# weekly keepalive script
"""
Weekly keepalive script — logs into AppFolio to keep the session alive
and saves updated cookies back to GitHub Secrets.
"""

import os
import sys
import json
import base64

from playwright.sync_api import sync_playwright

APPFOLIO_URL   = "https://laureatetld.appfolio.com/oportal/users/log_in"
APPFOLIO_EMAIL = os.environ["APPFOLIO_EMAIL"]
APPFOLIO_PASS  = os.environ["APPFOLIO_PASSWORD"]
COOKIES_B64    = os.environ.get("APPFOLIO_COOKIES", "")


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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        cookies = load_cookies()
        if cookies:
            context.add_cookies(cookies)

        page = context.new_page()
        page.goto(APPFOLIO_URL)
        page.wait_for_load_state("networkidle")

        if "log_in" in page.url:
            print("Cookies expired — logging in with credentials...")
            try:
                page.fill("input[name='user[email]']", APPFOLIO_EMAIL)
                page.fill("input[name='user[password]']", APPFOLIO_PASS)
                page.click("input[type='submit']")
                page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Login form interaction failed: {e}")
        else:
            print("Session still active via cookies.")

        # CRITICAL: if we are still on the login page, the session is dead and a
        # human must re-seed APPFOLIO_COOKIES (the runner can't pass 2FA). Saving
        # the cookies now would overwrite the good secret with dead login-page
        # cookies — exactly what perpetuated the Jun 18 2026 outage. So DON'T save,
        # and exit non-zero so the failure is visible (don't keep reporting green).
        if "log_in" in page.url:
            print(f"::error::Keepalive could NOT authenticate — still on {page.url}. "
                  "Expired APPFOLIO_COOKIES + 2FA. NOT saving cookies (would clobber the "
                  "good secret). A human must re-seed APPFOLIO_COOKIES.")
            browser.close()
            sys.exit(1)

        print("Login/session OK.")
        save_cookies(context)
        browser.close()
        print("Keepalive complete.")


if __name__ == "__main__":
    main()
