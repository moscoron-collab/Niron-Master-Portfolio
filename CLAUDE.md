# Niron Master Portfolio — Project Memory

This file is auto-loaded by Claude Code at session start. It captures the
working context so future sessions don't have to re-learn the setup.

## What this repo is

The Niron Master Portfolio dashboard plus the automation that feeds it.

- **Dashboard**: `index.html` — static page rendered from Google Sheets data.
- **Automation**: `automation/run.py` — Playwright script that logs into
  AppFolio, downloads the monthly Owner Statement PDFs, parses them, and
  writes the results to a Google Sheet.
- **Scheduler**: `.github/workflows/monthly.yml` — GitHub Actions workflow
  that runs the automation on a cron.

## Owner / contacts

- Repo owner: **moscoron@gmail.com** (Ron).
- Notification email recipient: also `moscoron@gmail.com` (stored in repo
  secret `NOTIFICATION_EMAIL`).
- Gmail App Password for SMTP is stored in repo secret
  `GMAIL_APP_PASSWORD`, generated under the `moscoron@gmail.com` Google
  account. If lost, regenerate at
  https://myaccount.google.com/apppasswords (Google only shows the
  password once — copy it immediately).

## The two bottom-line goals

Everything in this repo serves these two outcomes:

1. **Dashboard is automatically updated** each month with new AppFolio data.
2. **Email notification** is sent to the owner when the dashboard updates.

If a change breaks either of those, it's a regression — fix it before
shipping.

## Monthly schedule

- Cron in `.github/workflows/monthly.yml`: `0 16 15-25 * *`
  = 12:00 EDT / 16:00 UTC, daily from the 15th through the 25th of each month.
- AppFolio owner statements are typically posted by ~the 16th, so the
  window catches the first day they're available and keeps retrying
  through the 25th in case of a delay.
- GitHub Actions cron is **best-effort** — runs scheduled on the `:00`
  of the hour are often delayed by GitHub. A 10–60 minute delay is
  normal and does not mean the workflow is broken.
- The workflow can also be triggered manually: Actions tab → "Monthly
  AppFolio Data Pull" → "Run workflow".

## Google Sheet structure (critical)

The Sheet has multiple tabs. The dashboard reads from **`History`**.

- **`History`** — final data. The dashboard renders this.
- **`Pending Review`** — staging tab used only when approval mode is on.
- **`Settings!B3`** — the approval-mode flag:
  - `Yes` → new rows go to `Pending Review` and must be manually
    promoted to `History`. The dashboard will NOT show new data until
    that happens.
  - `No` → new rows go straight to `History`. Dashboard updates
    automatically. **This is the current/desired setting.**
- **`Maintenance Log`** — bookkeeping.

If the dashboard ever stops showing the latest month, the first thing
to check is `Settings!B3`. If it's `Yes`, either flip it to `No` or
manually move the rows from `Pending Review` → `History`.

## How the email notification works

The email is sent directly from the GitHub Actions workflow (not from
`run.py`, not from the Apps Script). See the
`Send dashboard updated notification` step in
`.github/workflows/monthly.yml`.

- Uses `dawidd6/action-send-mail@v3` over Gmail SMTP
  (`smtp.gmail.com:465`, secure).
- Fires only if the `Run automation` step succeeded
  (`if: steps.automation.outcome == 'success'`).
- From: `Niron Automation <moscoron@gmail.com>`.
- To: `${{ secrets.NOTIFICATION_EMAIL }}`.
- Body includes a link back to the workflow run for debugging.

Important: this email path is independent of `Settings!B3`. Even with
approval mode off, the workflow itself confirms a successful pull.

## Known quirk: cookie-save step

The last step in the workflow tries to write updated AppFolio cookies
back to the `APPFOLIO_COOKIES` repo secret using
`gliech/create-github-secret-action@v1`. This step fails with
"Resource not accessible by integration" because the default
`GITHUB_TOKEN` cannot write repo secrets — that needs a PAT with
`secrets:write` scope.

The step is marked `continue-on-error: true` so its failure does NOT
mark the whole workflow as failed (and therefore does not suppress the
notification email). Leave it as-is unless someone adds a proper PAT.

If AppFolio sessions ever start failing because cookies have expired,
the fix is either:
1. Manually re-capture cookies and update the `APPFOLIO_COOKIES` secret, or
2. Create a fine-grained PAT with `secrets:write`, store it as
   `PA_TOKEN`, and swap `pa_token: ${{ secrets.GITHUB_TOKEN }}` →
   `pa_token: ${{ secrets.PA_TOKEN }}` in the workflow.

## Repo secrets (names only — values are not visible)

- `APPFOLIO_EMAIL`, `APPFOLIO_PASSWORD` — AppFolio login.
- `APPFOLIO_COOKIES` — saved session cookies (see quirk above).
- `GOOGLE_SHEET_ID` — target Sheet.
- `GOOGLE_CREDENTIALS_JSON` — service account JSON for the Sheets API.
- `NOTIFICATION_EMAIL` — recipient of the dashboard-updated email.
- `GMAIL_APP_PASSWORD` — Gmail SMTP app password for sending the email.

GitHub secrets cannot be read back — they can only be overwritten. If
you need to verify a value, ask the owner.

## Branch / workflow conventions

- Active feature branch in recent work:
  `claude/combine-dashboards-responsive-l8WnY`.
- Main branch: `main`. Changes to the workflow only take effect on the
  scheduled cron after they're merged to `main`.
- Repo on GitHub: `moscoron-collab/niron-master-portfolio`.

## Working norms for Claude in this repo

- **Don't touch `Settings!B3` programmatically.** That flag is the
  owner's manual gate.
- **Don't add a second email path** in `run.py` or in the Apps Script —
  the workflow-level email is the single source of truth. Duplicates
  caused confusion historically.
- **Don't "fix" the cookie-save step by removing `continue-on-error`** —
  that would silently re-break the notification email.
- **When debugging a missed run**, check in this order:
  1. Did the workflow run at all? (Actions tab — remember cron delays.)
  2. Did `Run automation` succeed?
  3. Is `Settings!B3` set to `No`?
  4. Did the email step run? (Look at the workflow's step log.)
- **Schedule changes**: edit `monthly.yml`, but remember the new cron
  only applies once merged to `main`.

## This repo's audience

This repo is shared with a business partner. Keep this file, commit
messages, code comments, and any other repo content focused strictly
on the Niron Master Portfolio. Do not reference unrelated portfolios,
side projects, or internal-only context in any file that lives in
this repo.
