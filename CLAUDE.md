# CLAUDE.md — Niron Master Portfolio (Python automation + standalone dashboard)

> Read this BEFORE asking the user about repo structure, automation, or AppFolio.
> See also: `combined-portfolio/CLAUDE.md` for the React dashboard side.

> 📝 **User shorthand:**
> - **`db`** = dashboard.
> - **"combined"** OR **"moss"** = the **bigger combined db** = the Moss **+** Niron
>   combined version. Its GitHub repo is **`moscoron-collab/Moss-Investments-Niron-combined`**
>   (NOT `combined-portfolio` — that older name in this file is wrong; the React
>   dashboard for both Moss and Niron lives in the `Moss-Investments-Niron-combined`
>   repo). When the user says either word, switch context to that repo.

---

## 🔒 CRITICAL SECURITY CONSTRAINT

This repo holds **both** Niron LLC and Moss Investments automation code.

- **Niron** = partnered LLCs (business partner sees this data) → `run.py`, `monthly.yml`
- **Moss** = personal, Ronen + Oshrat (partner MUST NEVER see) → `run_moss.py`, `monthly_moss.yml`

The two pipelines write to **separate Google Sheets** (separate `GOOGLE_SHEET_ID` vs. `MOSS_SHEET_ID`). Do not let Moss data leak into the Niron sheet or vice versa.

---

## 👤 User context

- **Name**: Ronen Moscovich (`moscoron@gmail.com`, Denver, CO)
- **Language**: English; occasional Hebrew. Always reply in English.
- **Technical level**: NOT a developer. Communicates business-side.
- Step-by-step instructions, copyable commands, explain WHAT each does.
- Decisive when path is clear — don't over-confirm.
- **ALWAYS** put every value, secret, URL, or command in its own code block (` ``` ` or `` ` `` ) so the copy button appears. Never put copyable values inside a table cell or inline prose — the user cannot copy them that way.
- **ALWAYS** make URLs clickable markdown links `[text](url)`, never plain text URLs.
- **PR default (do NOT re-ask):** when work is committed/pushed and ready, **open AND merge the pull request automatically** (`mcp__github__create_pull_request` then `mcp__github__merge_pull_request`, base `main`). The user has standing approval — never ask "want me to open/merge the PR?". Just do it and give the link.
- **IMPORTANT — straggler commits:** After merging a PR, always verify the merge commit contains ALL expected files before reporting it as done. If commits were pushed to the branch AFTER the PR was already merged, they will NOT be on `main`. In that case: open a new PR immediately and merge it. Do not wait for the user to notice. (This happened with PR #23 — the Donald files landed on the branch after merge, only CLAUDE.md made it to main; PR #24 was the fix.)

---

## 📂 What's in this repo

```
Niron-Master-Portfolio/
├── README.md
├── index.html                       ← standalone Niron-only dashboard (legacy,
│                                      still live, separate from combined-portfolio)
├── automation/
│   ├── run.py                       ← Niron monthly pull (4 LLCs)
│   ├── run_moss.py                  ← Moss monthly pull (per-property, 4+1)
│   ├── keepalive.py                 ← Weekly AppFolio session refresh
│   ├── backfill.py                  ← Manual historical pull for Niron
│   └── backfill_moss.py             ← Manual historical pull for Moss
└── .github/workflows/
    ├── monthly.yml                  ← Niron daily 15-25 at 4pm UTC
    ├── monthly_moss.yml             ← Moss  daily 15-25 at 4pm UTC
    ├── weekly.yml                   ← Keepalive Sundays 8am UTC
    ├── backfill.yml                 ← Manual trigger only
    └── backfill_moss.yml            ← Manual trigger only
```

GitHub: `https://github.com/moscoron-collab/Niron-Master-Portfolio`
Local clone: `C:\Users\Owner\Dropbox\PC\Desktop\Niron-Master-Portfolio`

---

## 🏗️ Stack

- **Language**: Python 3.11
- **Key libs**:
  - `playwright` (Chromium headless) — logs into AppFolio, downloads PDFs
  - `pdfplumber` — extracts text from Owner Packet PDFs
  - `google-auth` + `googleapiclient` — writes rows to Google Sheets
- **CI**: GitHub Actions (`ubuntu-latest`)
- **Trigger**: cron-based via `.github/workflows/*.yml`

---

## 🔐 GitHub Secrets (must exist for runs to succeed)

| Secret | Used by | Purpose |
|---|---|---|
| `APPFOLIO_EMAIL` | run.py, run_moss.py, keepalive.py | Laureate AppFolio login email |
| `APPFOLIO_PASSWORD` | same | Laureate AppFolio password |
| `APPFOLIO_COOKIES` | same | Base64-JSON session cookies, refreshed weekly |
| `GOOGLE_SHEET_ID` | run.py, backfill.py | Niron sheet ID |
| `MOSS_SHEET_ID` | run_moss.py, backfill_moss.py | Moss sheet ID (separate!) |
| `GOOGLE_CREDENTIALS_JSON` | all | Service account JSON for Sheets API |
| `NOTIFICATION_EMAIL` | run.py | Where to send "data ready for review" emails |

If a secret is missing, the run crashes with `KeyError` at script start.

---

## 🌐 AppFolio (Laureate) specifics

- **Portal**: `https://laureatetld.appfolio.com`
- **Login URL**: `https://laureatetld.appfolio.com/oportal/users/log_in`
- **Statements URL**: `https://laureatetld.appfolio.com/oportal/statements`
- **Both Niron AND Moss** are managed by Laureate, Ltd. — same login credentials
- Owner Statement cards on the Statements page are labeled by LLC name:
  - `Yale Townhomes, LLC`, `5070 Donald, LLC`, `Divando, LLC`, `Dorado Investment Group LLC` (Niron — note: "Divando, LLC" and "Dorado Investment Group LLC" are slightly different from the internal `LLC_MAP` keys in `run.py`)
  - `Moss Investments, LLC` (Moss — single card, packet contains 4 property pages inside)
- Downloads can come as `.pdf` OR `.zip` (zip contains `Owner Packet.pdf` at any depth)

---

## 🛑 Stop logging in once the month is pulled + blank-row fill (Jun 18 2026)

Two changes applied to **ALL 5 AppFolio pulls** (`run.py`, `run_moss.py`, `run_divando.py`,
`run_yale.py`, `run_donald.py`) so the daily 15th–25th runs don't hammer AppFolio after the
month's data is already in, and so a blank placeholder row can never again hide real data
(the 1959 S Kearney Way bug). Each script now has the same helper set:
`_current_month_label()`, `find_existing(...)`, `month_already_pulled(...)`, `update_row(...)`,
plus a back-compat `already_recorded()` wrapper. `EXPECTED_PROPERTIES`/`LLC_MAP.keys()` is the
per-pipeline expected set (Niron 4 LLCs · Moss 4 core props `[p for p in PROPERTY_FIXED_COSTS
if p != CABO_PROPERTY]` · Divando/Donald `set(PROPERTY_CODE_MAP.values())` = 15/8 · Yale
`YALE_PROPERTY.values()` = 5).

- **Stop re-logging in (Part B):** at the **top of `main()`, BEFORE launching Playwright**, the
  script computes `exp_month = _current_month_label()` (first of the current calendar month — the
  month the 15–25 window pulls, since the statement's "to" date lands in it) and, if
  `month_already_pulled(sheets, exp_month)` is True (every expected entity has a **filled**
  disbursement row), it prints "already pulled — skipping AppFolio login" and **returns without
  logging in**. So once a month lands, the remaining daily runs do a ~2-second sheet read and quit.
  (The workflow cron still fires daily — GitHub cron can't self-disable — but no AppFolio login.)
  Session longevity is still maintained by the **weekly `keepalive.py`** (within the ~1-month
  device-trust window), so reducing daily logins is safe. The Niron skip path also prints
  `::set-output name=wrote_data::false` so no "Dashboard Updated" email fires.
- **Blank row can't block real data (Part A):** `find_existing(...)` returns `(row_index, filled)`
  where **`filled` = the Disbursement cell is non-empty**. A blank placeholder row reads
  `filled=False`, so: if a filled row exists → skip; if only a **blank** row exists → **`update_row`
  fills it in place (cols A:L for History, A:M for Property Detail)** instead of appending a
  duplicate; if no row → append. `$0` is a number (non-empty) so a legitimately-vacant/$0 month
  still counts as filled — only a truly empty cell triggers the fill. Niron threads the existing
  `(tab, row_index)` through `results` and updates in whichever tab (History/Pending Review) the
  blank sits; Moss/per-property update in their data tab.
- **Column refs:** History/Moss rows = 12 cols A:L, key = month col B + LLC/property col C,
  disbursement = col D. Property Detail rows = 13 cols A:M, key = month col B + property col D,
  disbursement = col H. `_month_key` normalizes the month so `2026-06-01` and `6/1/2026` match.
- **Backfills unaffected:** `backfill*.py` keep their own dedup; the run_* changes are additive +
  back-compat (the old `already_recorded(sheets, …)→bool` signature still exists).
- ⚠️ **Edge:** if a unit is genuinely missing from a packet (sold / not-yet-on-AppFolio), the
  expected set never fully fills, so that pipeline keeps logging in daily (safe — never a
  false "complete"). Update the expected set / maps when a property is added or removed.

## ⏰ Monthly pull schedule (updated Jun 18 2026)

Both AppFolio pulls now run **twice daily on the 15th–25th** so a statement that lands
midday is caught the same day (the duplicate-check skips months already saved):
- **Niron `monthly.yml`** (4 LLCs): **12pm ET (16:00 UTC)** + **4pm ET (20:00 UTC)**.
- **Moss `monthly_moss.yml`**: **6am ET (10:00 UTC)** + **5pm ET (21:00 UTC)** — the afternoon
  run is staggered **one hour after Niron's 4pm** on purpose, because both share the same
  `APPFOLIO_COOKIES` secret and would otherwise race on the cookie save.
- Per-property monitors unchanged (Divando 11am / Yale 12pm / Donald 1pm UTC, once daily).

## ⚡ FAST RECOVERY — "the pulls went quiet / data stopped updating" (READ FIRST)

> A condensed runbook so this is a ~5-minute fix next time. Full detail in the section below.

**SYMPTOM:** Actions logs show `Timed out waiting for cards` / `Cards found: 1` /
`No card found for '<LLC>'` / `Nothing to write` on Niron AND/OR Moss — but the jobs are
**GREEN** (they exit 0 on "nothing to write"). Dashboard stops updating for the month.
**CAUSE (99% of the time):** the `APPFOLIO_COOKIES` session expired. AppFolio device-trust
2FA re-SMS-challenges a browser idle ~1 month; the GitHub runner can't enter that code, so it
sits on `/oportal/users/log_in` (the "1 card" IS the login-card). It is **NOT** an AppFolio
layout change — confirm with the diagnostic dump in `run_moss.py download_packet` (prints the
page when `< 2` cards; if `url = …/users/log_in` → expired session, done diagnosing).

**FIX (the agent can do everything except set the secret):**
1. User logs into `laureatetld.appfolio.com` in their browser, completes the SMS 2FA.
2. User exports cookies with the **Cookie-Editor** extension (on the appfolio tab → Export →
   JSON) and pastes the JSON into chat.
3. Agent converts JSON → Playwright **base64** with a python script in-sandbox: map
   `expirationDate`→`expires` (`session:true`→`-1`), `sameSite` `lax/strict/no_restriction`→
   `Lax/Strict/None`, **OMIT** `sameSite` when null. Must include **`_oportal_session`** +
   **`2fa_user_token`**. Round-trip-verify, hand the user the base64 string.
4. User pastes it into the **`APPFOLIO_COOKIES`** repo secret (agent CAN'T write secrets):
   `https://github.com/moscoron-collab/Niron-Master-Portfolio/settings/secrets/actions/APPFOLIO_COOKIES`
5. Agent re-runs the pulls (`workflow_dispatch`). Validate the log says `Found card for …` /
   `Done. Wrote N rows`. Once one run authenticates, its **Save updated cookies** step re-seeds
   a fresh full session → the secret self-heals.

**CATCH UP THE MONTH** (run sequentially — they share the cookie secret): `monthly.yml` (4 Niron
LLCs) + `monthly_moss.yml` + `monthly_divando.yml` / `monthly_yale.yml` / `monthly_donald.yml`
(15/5/8 units). Niron writes straight to History (Settings!B4 = NO); Moss + per-property always
do. **Note:** once a month is already fully pulled, each script now **exits before login**
(prints "already pulled — skipping AppFolio login"), so a re-run that says that is correct, not a
failure — it means the data is already in.

**GOTCHAS that slowed it down the first time (Jun 18 2026):** (a) green checks hid the outage for
~a month — don't trust green, check for `Wrote N rows`. (b) Niron `run.py` cookie-save errors
`Resource not accessible by integration` (can't write the secret) — refresh rides on Moss +
per-property + weekly `keepalive.py`. (c) the Settings approval toggle is at **B4 not B3**
(run.py reads it by label now). (d) Scripts DON'T verify login and save cookies even on failure
(silent-rot hardening still deferred). (e) Agent can't reach `script.google.com`/the sheet
directly (sandbox) — sheet edits go through the user or the dashboard.

## 🚨 AppFolio session expiry — recovery procedure (Jun 18 2026, REAL INCIDENT)

The **entire** AppFolio auto-pull (Niron `run.py` 4 LLCs **and** Moss) silently stopped
pulling for ~a month. Symptom in the Actions log: `WARNING: Timed out waiting for cards` /
`Cards found: 1` / `No card found for '<LLC>'` / `Nothing to write.` — but the jobs still
showed a **green ✓** (they exit 0 when there's "nothing to write"), so it looked fine.

**Root cause = expired session, NOT a layout change.** A diagnostic dump (added to
`run_moss.py` `download_packet`, prints page structure when `< 2` cards are found — keep it)
revealed the runner was sitting on `…/oportal/users/log_in` (the "1 card" was the
`login-card`). The saved `APPFOLIO_COOKIES` lapsed; AppFolio has **device-trust 2FA** that
SMS-challenges a browser unused for ~1 month, and a GitHub runner is a "new browser" every
run, so it can **never** complete that 2FA. The weekly `keepalive.py` had been bounced to the
login wall too and kept **saving the dead login-page cookies back**, perpetuating the break
while reporting "success" (it never verifies login).

**Recovery (what fixed it — repeat this when it recurs):**
1. User logs into AppFolio in their **browser** and completes the SMS 2FA (trusts the device).
2. User exports cookies for `laureatetld.appfolio.com` with the **Cookie-Editor** browser
   extension (Export → JSON). The two that matter: **`_oportal_session`** (the login) +
   **`2fa_user_token`** (device-trust, so the runner isn't re-challenged).
3. Convert that Cookie-Editor JSON → Playwright format → **base64**: map `expirationDate`→
   `expires` (or `-1` for session cookies), `sameSite` `lax/strict/no_restriction`→
   `Lax/Strict/None`, **omit** `sameSite` when null (Playwright errors on `None`+insecure).
   `run.py`/`run_moss.py` `_normalize_cookies` tolerates raw or base64; **`keepalive.py` needs
   base64-of-Playwright**, so produce that canonical form.
4. User pastes the base64 into the **`APPFOLIO_COOKIES`** repo secret (the agent can't set
   secrets — `…/settings/secrets/actions/APPFOLIO_COOKIES`).
5. Re-run the pulls. ✅ Verified Jun 18: Moss + all 4 Niron LLCs + Divando(15)/Yale(5)/Donald(8)
   per-property all pulled June. Once a run authenticates, its **Save updated cookies** step
   re-seeds a fresh full session, so the secret self-heals going forward.

**Known latent issues:**
- ⚠️ **`run.py` (Niron monthly) cannot write the secret** — its cookie-save step errors
  `Resource not accessible by integration` (GITHUB_TOKEN lacks secret-write). Moss + the
  per-property workflows **can** write it, so cookie refresh rides on those. Pre-existing.

## ✅ Silent-rot hardening — login is now verified, failures are LOUD (Jun 19 2026, BUILT)

The deferred hardening from the Jun 18 incident is now in. Applied to `run.py`, `run_moss.py`,
and `keepalive.py`:
- **`login()` returns a bool and VERIFIES success** — after submitting credentials it checks the
  URL is no longer `/oportal/users/log_in`. A GitHub runner can't pass the device-trust SMS 2FA,
  so an expired session lands back on `log_in`; `login()` now returns **False** there instead of
  printing a fake "Login complete."
- **Never save dead cookies:** `save_cookies()` is only called when `login()` returns True. On a
  failed login the scripts **do NOT** overwrite `APPFOLIO_COOKIES` (this was the loop that let
  `keepalive.py` clobber the good secret with login-page cookies and perpetuate the outage).
- **Fail loudly:** on failed login — or when the Statements page shows **0 owner cards**
  (`h2.card-title` count < 1, the outage signature) — the scripts print a `::error::` annotation
  and **`sys.exit(1)`** so the GitHub job goes **RED** instead of green-with-no-data. (GitHub
  emails on workflow failure = the "real notification.")
- **Still green when legitimately done:** the `month_already_pulled(...)` early-return (before
  login) is unchanged, and "statement not posted yet" still finds the prior-month card (≥1 card,
  logged in) → no false red. Only a true auth/0-card outage trips the non-zero exit.

## 🧹 Bogus $0 Moss rows — writer fixed + cleanup script (Jun 19 2026, Part B)

**Root:** the old `backfill_moss.py` (and `run_moss.py`) parsed `disbursement or 0`, so a page
that failed to parse wrote a **real-looking $0 row**. This produced the 2023 "$0.00 /
System — Backfill" Kearney rows (02–10/2023) that distorted history and — mirrored as a browser
override — masked live data on the combined dashboard.
- **Writer fixed:** `extract_per_property_from_pdf` in BOTH `run_moss.py` and `backfill_moss.py`
  now **skips a property when the Owner Disbursement can't be parsed** (`disbursement is None`) —
  it never writes a $0 row. A genuinely-parsed `0.0` (real vacant/reserve month) is still kept.
  (`run.py` already had this guard.) Safe side effect: a skipped property leaves
  `month_already_pulled` False, so the daily run keeps retrying — never a false "complete".
- **Cleanup of the existing bad rows** (agent can't reach the sheet — sandbox blocks
  `script.google.com`): `automation/cleanup_moss_zero_rows.py` + workflow
  `cleanup_moss_zero_rows.yml`. It matches History rows where Disbursement (col D) is blank/0
  **AND** "Entered By" (col K) contains `Backfill`, with optional `PROPERTY_FILTER`/`YEAR_FILTER`.
  **DRY RUN by default**; only with `confirm=YES` does it (1) copy every matched row to a new
  `History_Backup_<timestamp>` tab FIRST, then (2) delete them bottom-up. **Run it from
  GitHub Actions:** Actions → "Cleanup — remove bogus $0 Moss rows" → Run workflow → review the
  dry-run log → re-run with confirm = `YES`. Cabo plug rows ($2,300, "Manual plug") and real
  backfill rows (non-zero disbursement) are never matched.

## ⚙️ Settings!B4 — "Require Approval Before Saving" (Jun 18 2026 fix)

The Niron **Settings** tab: row 3 = `AUTOMATION MODE` header, **row 4** = label
`Require Approval Before Saving to History` (A4) with the value in **B4** (`YES`/`NO`).
`run.py` previously read **`Settings!B3`** (the blank header row) → always defaulted to
`YES` → every pull went to **Pending Review** even though B4 said **NO**. Fixed: `run.py`
`require_approval()` now **scans column A for the "Require Approval" label** and reads the
adjacent B cell (robust to row shifts). `NO` (any case) → writes **straight to History**;
anything else → Pending Review. **Moss's sheet has the toggle at B3 and works**, so
`run_moss.py` was left as-is. (User confirmed they want auto-save = `NO`/no approval.)

---

## 📡 Divando per-property monitoring (BUILT)

A per-property monitor for Divando's 18 properties (15 AppFolio + 3 manual out-of-state).

- **Automation**: `automation/run_divando.py` (monthly) + `automation/backfill_divando.py`
  (history to Jan 2025, `BACKFILL_MONTHS=18`). Both write ONLY to a new **`Property Detail`**
  Google Sheet tab (header: Date Range, Month, LLC, Property, Cash In, Rent Collected,
  Mgmt Fee, Disbursement, Mortgage, Insurance/12, Status, Source, Updated). They NEVER touch
  `History` or the existing consolidated Divando row — partner-visible cards stay untouched.
  Workflows: `monthly_divando.yml` (daily 15–25, 11am UTC) + `backfill_divando.yml` (manual).
- **🐛 Bates matching fix (PR — comma-space):** for months the per-property monitor existed,
  **both Bates units were silently missing** (only 13 of 15 AppFolio props wrote rows →
  `234 = 13×18`). Cause: AppFolio prints the Bates page header as **`BATES, 15559 LOWER`** /
  **`BATES, 15559 Upper`** (a space after the comma + mixed case "Upper"), but every other
  property has no space (`13TH,15655`, `CROWN,5101A`). `_match_code` required an exact `==`,
  so both Bates pages failed and were skipped with no error. Fixed in `run_divando.py` +
  `backfill_divando.py`: `_match_code` now strips ALL whitespace and uppercases both sides
  before comparing (strictly more permissive — cannot break the 13 that worked). Also added a
  skip-warning print to `backfill_divando.py` so future unmatched property pages are visible,
  not silent. That warning then surfaced a SECOND quirk: in older months (Dec 2024–May 2025)
  AppFolio abbreviates the upper unit as **`BAT, 15559 Upper`** (literally "BAT", not "BATES"),
  so the first re-run still skipped those 6 months → only 30 of 36 Bates rows wrote (18 Lower +
  12 Upper). Fix: added `BAT,15559 LOWER`/`BAT,15559 UPPER` aliases to `PROPERTY_CODE_MAP` in
  both scripts (same canonical addresses). **After deploying, re-run `backfill_divando.yml`**
  to fill both Bates units across all 18 months (dedup means it only adds the missing rows). Note: Bates **Upper (top
  unit) moved out end of May 2026** → its May packet shows a Property Reserve hold (no Owner
  Disbursement, Net Owner Funds −$364.61), so that month reads $0 disbursement (correct — same
  as other props' reserve/turnover months); it shows **Vacant** from June until re-rented.
  - **🗓️ Decision (Jun 6 2026):** the user noticed Bates Upper still reads **Occupied** and
    asked why, since the May statement clearly shows the move-out (rent collected but held in
    reserve by Laureate, $0 owner disbursement, Net Owner Funds −$364.61). Confirmed: the
    automation's Occupied/Vacant flag is **only** `occupied = "Rent Income" in text` — it does
    NOT interpret the reserve-hold/no-disbursement signal. May still had a Rent Income line
    (last month's rent), so it correctly reads Occupied (tenant was there through end of May).
    **User chose to WAIT for the June statement** (first packet with no rent income → auto-flips
    to Vacant) rather than code a reserve-hold rule or manually edit the sheet. **Do NOT add a
    "reserve hold = vacant" rule** — a reserve hold also happens for repairs on occupied units,
    so it would create false vacancies. The "no Rent Income line" test is the reliable signal.
- **✅ Per-property backfill COMPLETE & verified (Jun 4 2026).** Three `backfill_divando.yml`
  re-runs filled every unit: run #1 = 234 rows (13 props, pre-Bates); run #2 (comma-space fix)
  added 30 (18 Bates Lower + 12 Bates Upper); run #3 (BAT alias) added the final 6 Bates Upper
  months (Dec 2024–May 2025). **`Property Detail` now = 504 rows = 28 units × 18 months**
  (Divando 15×18=270, Yale 5×18=90, Donald 8×18=144). Yale & Donald were already complete
  (counts were exactly 5×18 and 8×18) — Bates was the only gap. The daily `monthly_*` workflows
  keep it current. Reusable lesson: AppFolio page codes are inconsistent (comma-spacing,
  case, **and abbreviation** like `BAT`↔`BATES`); `_match_code` is whitespace/case-insensitive
  and the backfill prints a skip-warning for any unmatched property page — watch that log when
  adding a new LLC so a unit never goes missing silently again.
- **AppsScript.gs** `getDashboardJson()` now serves `data.property_detail` from that tab.
  ⚠️ There are 3 identical `getDashboardJson()` defs — Apps Script uses the LAST one (the
  one with the richer `maintenance` fields + `properties` + `property_detail`). Edit that one.
- **index.html** renders a "Divando — Per-Property Monitor" section between Recent
  Maintenance and History: a Chart.js chart + a table (Property | Status | Income |
  Disbursement | Repairs | Net | YTD Net | Occ %).
  - **3 dropdowns**: Chart style (`PD_CHART` bars|lines) · **View** · Metric (`PD_METRIC`
    net|disbursement|cash_in|occupancy).
  - **View dropdown = month picker ONLY** (`pdSetView`, value `m:YYYY-MM-DD` → `PD_MONTH`):
    a plain `<select>` listing every available month (newest first), defaulting to the newest.
    The table + bars chart always reflect that ONE selected month; the trend-line chart uses
    the full month history. **The old 3/6/9/12/YTD/All range options were REMOVED** (user
    request, PR #29) — they aggregated incorrectly and the range concept confused things. Do
    NOT re-add a range filter unless the user explicitly asks. (`PD_RANGE` still exists in the
    code but is effectively unused/dead for the dropdown.)
  - **Totals row** at the bottom of the per-property table (PR #34): dark background
    (`#0d1e30`), label shows "TOTAL — May 2026" (updates with selected month), Net is
    slightly larger (15px). Sums Income, Disbursement, Repairs, Net, YTD Net for the
    selected month across all properties in view.
  - A **plain-English caption** under the title states the current view, e.g.
    "Showing **Net Cashflow** · **Month: Apr 2026** · Bars view".
  - **Chart default = horizontal bars** (one bar per property for the selected/anchor month,
    green positive / red negative, blue for occupancy) — the line view had 18 overlapping
    lines and was unreadable. Toggle to **trend lines** for month-over-month movement;
    lines have **hover-highlight** (hovered property thickens, rest fade via `onHover`).
  - Ordering = `PD_LLC_CONFIG[key].order` (grouped by building, A-Z within group).
  - The 3 manual out-of-state props (Hare/Joest/Stockport) are pulled from History rows
    whose Source matches `Manual Entry: <prop>` (they're not in Property Detail).
  - Vacancy = `Status` column ("vacant" → Vacant badge); "no rent in" rule set by run_divando.py.
  - Per-property net = disbursement − mortgage − ins_mo − repairs (tax is annual/0 for Divando).
    Repairs come from the Maintenance Log matched by property-name substring.

### 🐛 Multi-row double-count fix (important)
LLCs can have **multiple History rows in one month** (Divando = AppFolio statement +
manual Suncoast/MidSouth entries). Maintenance and the Divando property mortgage are
**whole-LLC monthly costs**, so applying them per-row and summing counted them N times
(e.g. $8k maintenance shown as $16k; property mortgage subtracted twice → wrong Net).
Fixed via **`aggregateLlcPeriod(rows, maintenance)`** in `index.html`: collapse to one row
per (LLC, month), sum only the additive fields, then apply maintenance + `extraMortgage`
**once**. Used by the Divando card (`groupedSelected`), headline Net/YTD/Total-Mortgage,
the trend chart, and the History table. **Any new per-LLC monthly cost must be applied at
the (LLC, period) level, never per-row.**

### ✅ Divando card corrected (3-month bank-statement verified)
The Divando LLC card previously showed only the **$2,334/mo SBA** draft as "Mortgage" and
omitted all property mortgages. Verified across **Mar/Apr/May 2026** bank statements
(acct `3 Divando LLC 3442`) — both numbers are identical every month:
- **Property Mortgages = `$12,199.86`/mo** (6 building loan transfers: 0210 $2,352.90 +
  0211 $1,718.36 + 0212 $2,315.84 + 0213 $2,014.78 + 0214 $2,107.42 + 0215 $1,690.56).
- **SBA Loans = `$2,334.00`/mo** (6 SBA drafts on the 1st: $48+$731+$64+$273+$487+$731).
- **Total Divando monthly debt = `$14,533.86`/mo.**

The **Loan Balances** table also lists the 6 Divando building loans individually
(`DIVANDO_PROPERTY_LOANS` in `index.html`, $12,199.86/mo total) alongside the SBA line —
they're not in the Loans sheet tab so they're injected on the frontend. Their Original /
Remaining columns show **"—"** because the user has NOT provided those balances yet
(bank statements only show the monthly transfer, not the balance). When the user gives
remaining balances per acct (0210–0215), fill them in (and decide: Loans sheet tab vs
hardcoded). Left blank for now per user.

`index.html` now adds the property mortgages back via `DIVANDO_PROPERTY_MORTGAGE = 12199.86`
+ `extraMortgage(llc)`, wired into `recalcNet`, the enriched-net maps, and `totalMortgage`.
The card shows two lines: **Property Mortgages $12,199.86** + **SBA Loans $2,334.00**. This
DOES lower Divando's net (it was overstated before) — intentional, the card is now 100%.
State Farm insurance still comes from the Noble Insurance tab (authoritative); April tax
lump-sum stays excluded from monthly net.

> ⏳ **TODO (Moss combined repo)**: mirror this per-property section read-only on the Niron
> tab of `moscoron-collab/Moss-Investments-Niron-combined` (view-only — all editing is here).

---

## 📡 Yale per-property monitoring (BUILT — same pattern as Divando)

Per-unit monitor for Yale Townhomes, LLC's **5 townhome units** at 2991–2999 W Yale Ave,
Denver. Built exactly like Divando but adapted to Yale's different PDF structure.

- **Automation**: `automation/run_yale.py` (monthly) + `automation/backfill_yale.py`
  (imports `run_yale` for parsing so they never drift). Both write ONLY to the shared
  **`Property Detail`** tab (LLC = `Yale Townhomes, LLC`) — never touch History or the
  consolidated Yale card. Workflows: `monthly_yale.yml` (daily 15–25, **12pm UTC** — one
  hour after Divando's 11am so they don't race on AppFolio cookies) + `backfill_yale.yml`
  (manual, `BACKFILL_MONTHS` default 18).

### ⚠️ Yale PDF is STRUCTURALLY DIFFERENT from Divando
- Divando = one PDF **page per property** (clean per-property summary blocks, 15 pages).
- Yale = **ONE consolidated property** ("YALE, 2991-2999") with a single Property Cash
  Summary (2-page packet). The 5 units (2991/2993/2995/2997/2999) appear ONLY as a
  **prefix inside the Transactions table line descriptions** (e.g. "2991 - Rent Income").
  There is **NO per-unit Owner Disbursement or per-unit Management Fee** — those exist
  only at the whole-Yale level (one pooled disbursement, four unlabeled mgmt-fee checks).

### How `run_yale.py` parses it
- Walks the Transactions table using the running **Balance column** to classify each
  line as cash-in or cash-out by the **delta sign** (this nets NSF/reversal lines
  correctly and avoids guessing which number is amount vs. balance).
- **AppFolio wraps long descriptions**, so a reversal/deposit line's unit number +
  category lands on the line(s) ABOVE the date+amount line. The parser stitches each
  date line together with the non-date fragment lines since the previous date line
  (a context window) before matching unit/keywords. **Without this, rent is overcounted
  and cash-in falls short** (the bug that was caught & fixed during the build).
- Per unit it recovers **Rent Collected** (net of reversals) + **occupancy** (rent
  present = Occupied, absent = Vacant). The pooled **Management Fees + Owner Disbursement**
  from the summary are then **allocated to each unit in proportion to its cash-in**, so
  the per-unit disbursements **sum back exactly to the statement total** (verified:
  $10,076.61 for the Apr16–May15 2026 statement).

### Yale fixed costs (bank-verified: acct `2 Yale LLC 2321`, Mar/Apr/May 2026, all identical)
- **Mortgage = Lument `$7,279.08`/mo** (LUMENT7313 ACH ~6th of month) → **÷5 = $1,455.82/unit**.
- **Insurance = Acuity `$1,037.55`/mo** (ACUITY INS PREM, policy ZM1786) → **÷5 = $207.51/unit**.
  ⚠️ This is the **real bank draft**, NOT the old card figure ($1,024.54) or the policy
  quote ($11,248/yr). The dashboard card + Noble tab were **corrected to $1,037.55**.
- **SBA Loan `$225`/mo** = LLC-level business debt (like Divando's SBA) — kept at LLC
  level, **NOT** spread across the per-unit table.
- **Tax** = escrowed in the mortgage (`isTaxEscrowed` includes Yale) → tax NOT deducted
  in per-unit net.
- Fixed costs are split **equally 1/5** per user decision (one mortgage + one policy
  covers all 5 units). Vacant 2993 still carries mortgage/5 + ins/5 → shows a vacancy
  loss, and per-unit nets sum to the Yale LLC-level net.

### Dashboard (index.html) — now multi-LLC
- The per-property section is **no longer Divando-only**. `PD_LLC_CONFIG` holds one entry
  per LLC (`divando`, `yale`) with a `label`, a `match` substring (robust to "Divando, LLC"
  vs "Divando LLC"), and a per-LLC `order`. `PD_LLC` + `pdSetLlc()` drive an **LLC dropdown**
  added to the section header (only LLCs that have data appear). The section title, table,
  chart, and ordering all switch with it.
- `buildPropertyRecords` tags each record with `llc`; the section filters `recsAll` by the
  selected LLC's `match`. Everything else (metric/view/chart dropdowns, caption, bars/trend,
  occupancy, YTD) is shared and unchanged.
- AppsScript `getDashboardJson()` Property Detail reader is **generic by LLC** — Yale rows
  flow through with no Apps Script edit (only a comment updated).

> 🔜 **Next LLCs**: Dorado follows the SAME pattern. Check its Owner Packet structure
> first — if per-page like Divando, copy run_divando.py; if single-consolidated like Yale,
> copy run_yale.py. Add a `PD_LLC_CONFIG` entry + per-LLC fixed costs verified against 3
> months of that LLC's bank CSV.

---

## 📡 Donald per-property monitoring (BUILT — clean Divando-style pattern)

Per-unit monitor for 5070 Donald, LLC's **8 units = 4 duplexes** (5060 & 5062, 5064 &
5066, 5070 & 5072, 5080 & 5082 E Donald Ave, Denver). Donald's Owner Packet is the
**clean Divando structure** — 9 pages, one page per unit (page 1 = consolidated
summary), each with its own Property Cash Summary including a **per-unit Owner
Disbursement**. So `run_donald.py` is essentially `run_divando.py` with Donald's
`PROPERTY_CODE_MAP` + fixed costs — no allocation/estimation like Yale needed.

- **Automation**: `automation/run_donald.py` (monthly) + `automation/backfill_donald.py`
  (imports `run_donald` for parsing + fixed costs so they never drift). Both write ONLY
  to the shared **`Property Detail`** tab (LLC = `5070 Donald, LLC`) — never touch History
  or the consolidated Donald card. Workflows: `monthly_donald.yml` (daily 15–25, **1pm UTC**
  — one hour after Yale's 12pm so they don't race on AppFolio cookies) + `backfill_donald.yml`
  (manual, `BACKFILL_MONTHS` default 18). Page header format: `DONALD, NNNN - NNNN E Donald
  Ave, ...` → `PROPERTY_CODE_MAP` key is `DONALD, NNNN`.

### Donald fixed costs (bank-verified: acct `1 Donald LLC 9364`, Mar/Apr/May 2026, all identical)
- **Mortgage = CBRE `$13,708.00`/mo** (CBRE LOAN SERV PAYMENT, one blanket loan) → split
  **equally ÷8 = $1,713.50/unit** (per user; units valued equally at $562,750 each).
- **Insurance = Westfield `$1,210.84`/mo** (OH WESTFIELD BILLPAY, policy 499841Y, one policy
  for all 8) → **÷8 = $151.36/unit**. ✅ This matches the existing card figure — no correction.
- **SBA Loan `$444`/mo** = LLC-level business debt (like Divando/Yale SBA) — kept at LLC
  level, **NOT** spread across the per-unit table.
- **Tax** = escrowed in the mortgage (`isTaxEscrowed` includes Donald) → tax NOT deducted
  in per-unit net.
- All 8 units are on AppFolio (no manual entries). Per-unit nets sum to the Donald LLC-level
  net (verified: 8 disbursements = $20,705.21 for Apr16–May15 2026 → net ≈ $5,786).

### Dashboard
- `PD_LLC_CONFIG.donald` added (label `Donald`, match `donald`, 8-unit order by duplex).
  The shared LLC dropdown picks it up automatically; nothing else changed. AppsScript
  Property Detail reader is generic by LLC — Donald rows flow through with no edit.

---

## 🩺 Dashboard self-audit + correctness fixes (Jun 5 2026, PR #42)

A full accuracy audit was run against the live data (recomputing every total from the
raw sheet). The math engine was internally consistent; the issues were labeling,
stale inputs, cross-section mismatches, and "missing-data-shown-as-$0". All 11 findings
were fixed (user-approved decisions). **The findings reference the audit numbering #1–#11.**

> ⚙️ **`index.html` now has ONE `MANUAL OVERRIDES` block** (just below the formatters,
> search `MANUAL OVERRIDES`). It is the ONLY place to edit these code-held numbers:
> `DIVANDO_PROPERTY_MORTGAGE`, `DIVANDO_PROPERTY_LOANS`, `INSURANCE_OVERRIDE`, and the
> tax-treatment functions. (Full migration of these into the Google Sheet was explicitly
> DEFERRED — "level 1" only — to avoid risking the Sheets connection.)

**What changed (all user-approved):**
- **#1 Tile rename:** `Gross Total Income` → **`Cash Collected`** (+ `Gross YTD` → `Cash YTD`).
  The number is unchanged — it is the **total owner disbursement** (cash that reached the
  LLC bank accounts), NOT gross rent. Gross rent isn't recorded for Dorado / out-of-state,
  so "Cash Collected" is the honest label. Do NOT relabel it "Income/Rent" again.
- **#2 + #3 Insurance overrides** (`INSURANCE_OVERRIDE = { divando: 2473.08, yale: 1037.55 }`,
  applied via `effectiveIns(llc, sheetIns)`):
  - **Yale → `$1,037.55`/mo** (the real Acuity bank draft; the sheet/History still held the
    stale `$1,024.54`). Lowers Yale net by `$13.01`/mo.
  - **Divando → `$2,473.08`/mo** = Divando-OWNED houses only (`$29,677/yr ÷ 12`); EXCLUDES the
    2 Dorado-owned units that ride the State Farm policy. Was `$2,885.83` (full policy) →
    raises Divando net by `$412.75`/mo. After this, the Divando card net and the Divando
    per-property TOTAL net differ ONLY by the `$2,334` SBA (by design, SBA isn't per-property).
  - `effectiveIns` overrides BOTH the displayed Insurance line AND the net everywhere
    (cards, History, KPIs, trend) by mutating `g.ins_mo` in `aggregateLlcPeriod` and in the
    grouped-card map. Per-property records (`buildPropertyRecords`) are NOT overridden — they
    already use correct per-unit insurance from the Property Detail tab.
  - **🏦 Divando insurance corrected to `$2,909.98`/mo (BANK-VERIFIED, Jun 12 2026).** The
    `$2,473.08` above was a calculated guess. The user uploaded the Divando operating-acct
    (`3 Divando LLC 3442`) Mar–May 2026 transactions; the real **STATE FARM** auto-draft =
    **`$2,909.98`/mo** (Mar 3, Mar 31, Apr 29 — the standing premium). **May 29 dipped once to
    `$2,633.15`** but that's a one-off, not the new normal (user confirmed "most months were
    2909.98"). `INSURANCE_OVERRIDE.divando` is now `2909.98` — the **gross** amount drawn.
    Dorado separately credits Divando **`$138.00`/mo** ("TRANSFER FROM DDA ACCT …2189") for its
    2 units on the policy; this is **NOT netted** into the insurance line (user wanted the real
    drawn figure, not net). If ever wanted, net-of-credit = `$2,909.98 − $138 = $2,771.98`/mo.
  - **Noble Insurance tab synced to `$2,909.98` (Jun 12 2026).** The user noticed the Noble →
    Divando card still showed the quote figure `$2,885.83/mo` (= `$34,630/yr ÷12`). Updated 4
    spots to the real draft `$2,909.98/mo`: the Divando card **Monthly Payment** field, the
    **Total Monthly · All Active** summary (`$5,587.55 → $5,611.70`, Divando line `$2,909.98`),
    the 13-property **TOTAL footer** (`$34,630/yr · auto-draft $2,909.98/mo`), and the
    **renewal-history** row. **Annual premium stays `$34,630/yr`** (the real policy quote); the
    monthly draft is `$24.15` higher than quote÷12 because the SFPP monthly plan adds an
    installment fee. Also fixed the draft date "2nd of month" → **"end of month"** (bank shows
    Mar 31/Apr 29/May 29). The per-property itemized policy table rows were left as-is.
  - **Audit "Hardcoded vs sheet" warning RETIRED for insurance (same PR).** Now that Divando +
    Yale insurance are bank-verified, `auditRun`'s insurance check reports a **PASS**
    ("Insurance (bank-verified)") instead of a `warn` — the override IS the source of truth, so
    it's no longer drift to review. This is what clears the amber chip (not silencing — the
    number is now correct + verified). ⚠️ The Google **Sheet** still holds the old per-row
    `ins_mo`, but it no longer drives the dashboard (the override wins everywhere) and no longer
    trips the audit. AppsScript `dashboardKnowledge()`/`buildPortfolioContext` still quote the
    old `$2,473.08`/`$2,885.83` — sync on the next redeploy.
- **#8 Tax:** `isTaxLumpSum(llc)` now includes **Divando AND Dorado** (was Divando-only via
  `isTaxAnnual`, kept as a back-compat alias). Tax is shown on the card as info with
  `(paid in spring ⓘ)` but **excluded from monthly net** for both. **This RAISED Dorado net
  by `$945`/mo** (Dorado used to deduct tax monthly). Donald/Yale unchanged (escrowed).
- **#4 History table foots on screen:** added an **Insurance** column and the Mortgage column
  now shows the **full** mortgage (`mortgage + extraMortgage`). Tax is always 0 in net now,
  so `Disbursement − Mortgage − Insurance − Maintenance = Net` reconciles on every row.
- **#5 Loan table** reduced to **LLC | Lender | Monthly** only (removed Original / Remaining /
  Maturity — the blank balances were rendering as a misleading `$0.00` "paid off"). Real
  remaining balances are still not entered; revisit when adding DSCR/equity (Phase 2).
- **#6 Occupancy %** in the per-property table now reflects the **selected month** (100 / 0),
  not a lifetime average (it was mixing time windows with the single-month columns).
  ⚠️ **SUPERSEDED (Jun 6 2026, see below)** — the single-month 100/0 column was deleted
  and replaced with two real "% of months occupied" columns.
- **#10 Repairs matching:** `maintenanceForProp` is now **one-directional** (`normAddr(invoice)
  .startsWith(normAddr(unit))` via the new `normAddr` helper). A generic invoice like
  `15559 E Bates Ave` or `5101 Crown Blvd` (no Lower/Upper or Unit A/B) will NOT attach to
  both units → no double-count. Trade-off: an invoice MUST include the unit suffix to match.
- **#7 Distribution dedup (AppsScript `addDistributionEntry`):** rejects a duplicate with the
  **same LLC + month + your_amount + partner_amount** (mirrors the statement dedup). Prevents
  a double-click inflating Your Distribution / YTD.
- **#9 "Last Updated" (AppsScript `getDashboardJson`):** now the **latest real write timestamp**
  (`max` of History "Logged At" + Property Detail "Updated") via `bumpChange()`, instead of the
  page-load time. Manual maintenance edits don't carry a timestamp, so they won't bump it.

**Net effect (May 2026):** Cash Collected unchanged `$79.8K`; Net Cashflow `$25.1K → $26.4K`.

> 🚀 **AppsScript NOT auto-deployed:** #7 and #9 only take effect after pasting the updated
> `automation/AppsScript.gs` into the Sheet's Apps Script editor and redeploying (New version).
> The `index.html` fixes go live on merge.

> ⚠️ **Known follow-ups (do NOT forget):** (a) the chatbot's `dashboardKnowledge()` and the
> Noble Insurance tab still quote the OLD figures (Divando insurance `$2,885.83`, Dorado tax
> deducted) — sync them when convenient. (b) **Still TODO from the original request:** the
> self-audit **"Run Audit" button** (on-load + manual, read-only) was NOT built yet — user
> chose to land these fixes first. Then the Phase-2 partner-grade plan. **NOTE: DSCR / equity /
> LTV are OFF the table per user (Jun 5 2026) — do NOT propose them.** Phase 2 = NOI, cap rate,
> cash-on-cash, reserves/capex tracker, and the CPA invoice workflow: Paid By / Paid / Notes
> fields + CPA-ready CSV/print view.

---

## 🩺 Self-Audit (Run Audit button) — BUILT (Jun 5 2026, PR #44)

A read-only self-audit lives in `index.html`. It **recomputes every total straight from
the raw `PORTFOLIO_DATA`** and compares it to what is actually painted on screen, so it
catches real rendering / label / totalling drift (not just re-printing the same math).

- **Runs on every render** (`auditRun(false)` is called at the end of `renderAll`, wrapped
  in try/catch so it can never break the dashboard) → updates a header **chip**
  (green `✓ Audit OK` / amber `⚠ N to review` / red `✗ N issues`).
- **Manual:** the **🩺 Run Audit** button in the header (and clicking the chip) opens the
  full pass/fail report modal (`auditRun(true)` → `renderAuditModal`), with a **Copy report**
  button. Modal id `audit-modal`; reuses the existing `.modal-overlay`/`.modal-box` theme.
- **NEVER writes to the sheet.** The "write-back" check is a read-only proxy: it verifies
  maintenance `row` indices are valid (≥5) and unique, and flags duplicate History /
  Distribution rows — it does NOT perform a live test write.
- **KPI tiles now carry stable IDs** (`kpi-cash`, `kpi-cash-ytd`, `kpi-net`, `kpi-net-ytd`,
  `kpi-dist`, `kpi-dist-ytd`, `kpi-mort`, `kpi-value`) so the audit reads them reliably.
  KPIs are compared at display precision (via `fmtShort`); tables/cards to the penny.
- **What it checks:** 8 KPI tiles; each per-LLC card net + sum-of-cards = Net tile; every
  visible History row foots (`Disb − Mortgage − Insurance − Maintenance = Net`); per-property
  table each unit net = raw recompute, TOTAL = sum of units, and the bars chart = the Net
  column (when metric = net); trend totals finite each month; month-dropdown sync; duplicate
  History/Distribution rows; maintenance row integrity; insurance override-vs-sheet drift
  (expected until #11 migration); date format; `last_updated` validity.
- **❌ Loan remaining-balance check REMOVED (user decision, Jun 5 2026):** DSCR / equity / LTV
  are **NOT being tracked** and the Remaining column was dropped from the loan table (#5), so a
  missing remaining balance is not a finding — the check was deleted to stop 5 noise warnings.
  **Do NOT propose DSCR/equity/LTV in Phase 2 unless the user revives it.**
- **Expected steady state (updated Jun 24 2026):** insurance is now a **PASS** (bank-verified, no
  longer drift), so the only remaining warning is the **1 April-2026 Divando "Manual Entry" group**
  (see below) — everything else is green. The chip stays amber solely because of that one April
  data-label leftover; clearing it (relabel the 3 rows' Source) takes the chip green.
- Verified with a synthetic-DOM harness: 22 pass / 0 fail / 3 expected warns on correct data;
  catches an injected wrong KPI as a FAIL.

### 🐛 "no matching data" × 4 on the LLC cards = audit-selector bug, FIXED (Jun 24 2026)
A June-2026 audit showed **4 WARN | LLC card | Divando/Donald/Yale/"Dorado (÷3 w/ Simon)" | no
matching data**. **Not a data problem** — the audit's per-LLC-card check used the broad selector
`#tab-master .llc-card`, which the **Distribution Planner** (`renderDistributionPlanner`, line ~2402)
and the **True-Cash bank section** (line ~2501) ALSO use. Those planner cards have short titles
("Divando", "Donald", "Dorado (÷3 w/ Simon)") that don't match a canonical LLC data row, so the check
emitted bogus "no matching data" warnings every run. **Fix:** the check now scopes its `.llc-card`
query to the **Monthly Breakdown section only** (found via its `<h2>`), which contains exactly the 4
real per-LLC summary cards. The real cards still PASS and `sum-of-cards = Net tile` is unaffected.
Pure frontend, live on merge.

### 🏷️ The 1 remaining audit warning = April-2026 Divando "Manual Entry" rows (known, deferred)
**WARN | History data | 2026-04-01 | Divando LLC | Manual Entry | 1 row | 3 rows | Possible duplicate
statement.** The 3 out-of-state manual props (8222 Hare Ave / 3899 Joest Rd / 6580 Stockport Dr) for
April 2026 all carry a **bare Source `"Manual Entry"`** instead of `"Manual Entry: <property>"`, so the
audit's dedup key (`month | LLC | source`) collapses all 3 into one and flags a "possible duplicate."
They are **NOT duplicates** (3 distinct properties) and the **dollars are correct** — col C is already
`Divando LLC`, so they roll up into the Divando card/net properly. The only effects are this cosmetic
warning + April's per-property table can't split them by property. **Fix = relabel col K (Source) on
those 3 April rows** to `Manual Entry: <property>`. ✅ **`relabel_manual.py` now does this in one click**
(Jun 24 2026): it was extended to also catch the "Shape B" rows (col C already `Divando LLC` + bare
`Manual Entry` source) by matching the **Owner Disbursement amount** (col D) to the property, using the
user-confirmed April mapping (`$478.25`→Joest · `$920`→Stockport · `$1,209`→Hare). Run **Actions →
"Relabel Manual Entries (Suncoast / Mid South)" → Run workflow**; it only relabels the Source (never
changes the amount) and is idempotent. The writer `enter_suncoast_manual.py` is already fixed (writes
the per-property Source), so this won't recur for new months. ⚠️ The April Hare row's amount reads
**$1,209** in the sheet (the $1,125.40 figure was *May's* Hare deposit) — the relabel does not touch it;
correct the amount separately only if the user says $1,209 is wrong.

> Self-audit is pure frontend (`index.html`) — no Apps Script change, goes live on merge.

---

## 🩺 Operational Health tiles (Jun 5 2026, PR #46)

A second row of 4 tiles sits **just below the top KPI row** in `renderAll` (mirrors the
health-check row the user built on the Moss combined db's Niron tab). Same `summary-card`
theme; they react to the month dropdown like everything else. Pure frontend.
- **Occupancy — now a DUAL tile (Year | Month), Jun 12 2026.** User: "occ rate is measured by the
  year not month." Left half **`Occupancy · {year}`** (`kpi-occ-year`) = year-to-date **pooled**
  occupancy = occupied unit-months ÷ unit-months WITH DATA (Jan→selected month), the same
  `poolOcc` math the per-property TOTAL uses; color green ≥95, gold ≥85, red <85, `—` if no data.
  Right half **`Occupancy · Month`** (`kpi-occ`, **id preserved** so the audit's monthly recompute
  still passes) = occupied/total units for the selected month, from `buildPropertyRecords` filtered
  to `source !== 'Manual'` (the 3 out-of-state manual entries have no vacancy signal; **Dorado has
  no per-unit data so it is not in the denominator**); green 100, gold ≥90, red <90, sublabel
  `X/Y units · Month`. The self-audit recomputes BOTH halves (`htile('kpi-occ-year', …)` added).
- **Vacant Units** — count + the vacant unit name(s) (e.g. `2993 W Yale Ave`). Gold if >0.
- **Repairs · This Month** (`kpi-rep-month`, red) — sum + count of Maintenance-log invoices for
  the selected month. Verified = `$11,615.00 / 4` for May 2026. **Per-LLC mini-table (Jun 14 2026):**
  the tile is a flex row — total/label/count on the LEFT, a small **vertical 2-col table** (LLC · amount,
  `fmtShort` e.g. `$8.0K`) on the RIGHT, via `repairsMiniTable()` (groups maintenance by `shortLlc(llc)`,
  biggest first, only LLCs with repairs). The `kpi-*` value div + total are unchanged → self-audit
  unaffected. (Started as a breakdown line under the total, moved to a right-side table per user.)
  - **FAB-overlap fix (Jun 14 2026):** the floating action buttons (`.chat-fab`/`.maint-fab`/etc,
    `position:fixed; right:24px`) were covering the rightmost tile's mini-table numbers. Added a
    right "lane": `@media (max-width:1560px){ .container{ padding-right:84px } }` (reset to 12px on
    mobile ≤768). Reserves space so no tile content sits under the FABs.
- **Repairs · YTD** (`kpi-rep-ytd`) — sum + count for Jan→selected-month of the year. Same per-LLC
  breakdown line.
  Verified = `$18,615.00 / 6` for 2026-through-May.
- The self-audit recomputes all 3 numeric tiles (`Health tile` rows).

> 🔔 **REMINDER (user asked to be reminded later, Jun 5 2026):** Occupancy currently EXCLUDES
> the 3 out-of-state manual units (and Dorado, which has no per-unit data). User said leave it
> for now but **remind them later** about whether to fold the manual units into the occupancy
> denominator.
> 🔔 **REMINDER:** the April 2026 Divando `Manual Entry` rows (3 rows, generic source) still
> need a look — relabel to `Manual Entry: <property>` (and fix `enter_suncoast_manual.py`,
> which writes a bare `"Manual Entry"` + puts the property in the LLC column). User deferred.

---

## 🏠 Vacancy / Notice flags — manual real-time vacancy (Jun 12 2026)

**Why:** the statement-derived vacancy (`occupied = "Rent Income" in text`) is always **one
statement-cycle behind** — a unit only reads Vacant once a full statement period collected zero
rent (e.g. Bates top moved out end-May but May still had rent income → didn't flip until June).
The real-time signal is the **tenant's notice**, which only Laureate knows. So we added a manual
flag you set the moment you hear "notice given," and the **Vacant Units** tile reflects it
**immediately, ahead of the statement**. (This is feature **#1** of the "1+2" plan: #2 = a standing
notice habit from Laureate. The reserve-hold early-warning was discussed and **deferred** — it's
ambiguous, a hold also happens for repairs on occupied units; do NOT auto-flag vacant from it.)

**Data — new `Vacancy` Google Sheet tab** (auto-created/seeded-empty by `ensureVacancyTab()` in
`AppsScript.gs`, like the Property Tax tab). Title row 1, headers row 4, data from row 5. Cols
A–G: `Property · LLC · Vacant From · Re-rented On · Note · Entered By · Updated At`. Live
`getDashboardJson` reads it → `data.vacancy` (each row tagged with absolute `row`). `doPost`
routes `add_vacancy` / `update_vacancy` / `delete_vacancy` → `addVacancyEntry` /
`updateVacancyEntry` (used for "mark re-rented", rewrites 7 cols) / `deleteVacancyEntry`, each
`logActivity`-logged. Edit the **LAST** copies (duplicate-function footgun).

**Frontend (`index.html`, pure frontend):**
- Helpers `monthStartOf` / `vacancyActiveForMonth(flag, monthPS)` / `unitMatch` / `manualVacant`.
  A flag covers month M if `vacant_from`'s month ≤ M and (`rerented_on` empty or its month > M).
- `buildPropertyRecords` now forces `occupied=false, manual_vacant=true, status='Vacant'` on any
  per-unit record whose unit has an active flag for that month (applies to per-property units +
  the 3 manual props). So occupancy %, the per-property table, and the chart all respect a flag.
- **Vacant Units tile** = the selected month's statement/override-vacant units **PLUS EVERY
  active manual flag** (any flag not yet marked re-rented), deduped by unit. **The flag count is
  deliberately NOT tied to the selected month** (changed Jun 12 2026 — the user added 3 flags and
  the tile still read 1 because they were future-dated vs the May view): once you flag a unit it
  stays counted until you mark it re-rented, so "3 flagged" reads as 3 on any month. **Occupancy %**
  stays month-based, computed independently from `healthRecs` (`occOccupied = healthRecs.filter(
  occupied)`), so the self-audit's `kpi-occ` recompute is unaffected (the audit checks occupancy %,
  not the Vacant count). `buildPropertyRecords` still applies flags **month-aware** (via
  `vacancyActiveForMonth`) so per-month occupancy %, the per-property table, and the chart are
  correct for each month — only the headline tile count is "all active flags."
- The **Vacant Units tile is now clickable** (`onclick="openVacancyModal()"`, label `Vacant Units
  🏠`, sublabel "· click to flag") → `vac-modal`: pick unit (dropdown built from
  `property_detail` + manual props via `vacancyUnits()`), Vacant-From date, optional note; lists
  current flags with **Re-rented** (sets `rerented_on=today`) + 🗑 delete. Requires `ensureActor()`.
- ⚠️ **Tile count = all active flags (NOT month-tied).** A flag shows on the headline Vacant
  Units tile as soon as it's added and stays until re-rented, regardless of the month dropdown.
  (The per-property table / occupancy % ARE still month-aware via `vacancyActiveForMonth` — only
  the tile count is the simple "currently flagged" total, per user request Jun 12 2026.)
- **Backward-safe:** if the Apps Script isn't redeployed yet, `data.vacancy` is undefined →
  `(data.vacancy||[])` = no flags → zero behavior change. So `index.html` is safe to ship first.

> 🚀 **Going live (REQUIRED):** redeploy `AppsScript.gs` (Sheet → Extensions → Apps Script →
> paste → Deploy → Manage deployments → Edit → New version → Deploy). The `Vacancy` tab
> auto-creates on the first load after redeploy. No new permission scope. `index.html` goes live
> on merge; flags just won't save/read until the redeploy.

---

## 🏠 Per-property Occ % → "% of months occupied" (Jun 6 2026)

User said the single-month **100/0** Occ % column (audit fix #6) was **irrelevant** — a
unit either had rent that one month or didn't, so every row just read 100%. **Deleted it**
and replaced it in the per-property table (`renderPropertySection` in `index.html`) with
**TWO real occupancy-rate columns** (user picked two columns):
- **`Occ % {year}`** = % of months occupied **this calendar year** (Jan → selected/anchor month).
- **`Occ % since Jan ’25`** = % of months occupied **lifetime, since Jan 2025** (→ anchor month).

**Calc:** `occupied months ÷ months WITH DATA`, per unit. **Months a unit has no data row
(pre-monitoring / pre-backfill) are IGNORED, not counted as vacant** (user decision — so a
unit that started late isn't unfairly dragged down). Both windows are capped at the selected
anchor month, so picking an earlier month in the View dropdown shows occupancy "as of" then.
`occupied` is the existing per-row flag (rent in = occupied) from `buildPropertyRecords`.
Helpers `occClass`/`occCell` (green ≥95, red <80, neutral between; `—` when no data).

**Totals row** shows portfolio-wide occupancy = **pooled occupied unit-months ÷ total
unit-months** (data only) for each window (`poolOcc` helper), not an average of the per-unit %.

**Self-audit unaffected:** the new columns were appended AFTER `YTD Net`, so the audit's
positional reads (`td[5]` = Net) didn't shift. Pure frontend, live on merge.

> Note: the **chart's** "Occupancy %" metric (the Metric dropdown) is a SEPARATE thing and
> still shows single-month 100/0 for the bars view (the trend-line view over time is the
> useful one). Left as-is — the user's complaint was about the TABLE column. Revisit only if
> asked.
> 🔔 Earlier reminder still open: occupancy currently EXCLUDES the 3 out-of-state manual units
> and Dorado (no per-unit data). Unchanged here.

---

## ℹ️ Net Cashflow card tooltip (Jun 6 2026)

The **Net Cashflow** KPI card now has a small **ⓘ info icon** next to its label (`netTip` in
`renderAll`, ~line 1627 of `index.html`) that opens a CSS hover tooltip (`.kpi-info` /
`.kpi-tip` styles near the `.summary-card` block) explaining exactly what the number is:
- **Formula shown:** `Cash Collected − Mortgage − Insurance − Maintenance (repairs)`.
- Notes that Cash Collected = the owner disbursement that hit the bank, and Mortgage is the
  full loan cost (Divando = 6 property loans + SBA).
- **Tax note (the key clarification the user asked for):** property tax is NOT subtracted
  again in this number — **Yale & Donald pay tax through the lender (escrowed in the
  mortgage)**, while **Divando & Dorado pay tax manually as a spring lump sum** (shown for
  info only, left out of monthly net). This matches `isTaxEscrowed` (Donald/Yale) +
  `isTaxLumpSum` (Divando/Dorado), both of which make `effectiveTax` return 0.
Pure frontend, live on merge. To add the same tooltip to another KPI, reuse the
`<span class="kpi-info">💡<span class="kpi-tip">…</span></span>` pattern inside that card's label.

### 📊 Two efficiency ratios added to the KPI cards (Jun 7 2026)
Two live ratios now appear in `renderAll` (computed via the `ratioPct(num, den)` helper, which
returns `'—'` when the denominator ≤ 0). Both recalc with the month dropdown.
- **Net Cashflow card** → on-card chip **`📊 {marginPct} kept`** + a line in its 💡 tooltip.
  `marginPct = ratioPct(totalNet, totalDisb)` = **Net Cashflow ÷ Cash Collected** ("cash
  efficiency" — share of collected cash left after mortgage, insurance & repairs).
- **Your Distribution card** → on-card chip **`💸 {payoutPct} of net`** + a NEW 💡 tooltip
  (`distTip`, "Return on net cashflow"). `payoutPct = ratioPct(distThisMonth, totalNet)` =
  **Your Distribution ÷ Net Cashflow**. ⚠️ Numerator is YOUR share only while Net is the whole
  portfolio (you + Nir), so an even split reads ~50% — the tooltip explains this. (User picked
  "Your Distribution ÷ Net", NOT total-payout ÷ net.)
- Chip style = `.kpi-ratio` (green) / `.kpi-ratio.blue` (blue for the dist card), shown as a
  second line in the sublabel. Percentages use **one decimal** (`toFixed(1)`).
- Self-audit unaffected (it reads `#kpi-*` values via `fmtShort`, not the sublabel chips).

### 🌐 Hebrew translate toggle on Net Cashflow + Your Distribution cards (Jun 7 2026)
A small **`עב`/`EN` button** (`.kpi-lang-btn`, calls `toggleKpiLang()`) sits in the label of the
**Net Cashflow** and **Your Distribution** KPI cards. It flips a shared `KPI_LANG` state
(`localStorage 'niron_kpi_lang'`, default `en`) and re-renders, translating BOTH cards' **label,
sublabel chips, and 💡 tooltip** between English and Hebrew. Built via an inline `L(en, he)` helper
in `renderAll`; the Hebrew tooltips get `dir="rtl"` + right-align. The dynamic numbers
(`marginPct`, `payoutPct`, dollar values) are unchanged — only the words translate. **Self-audit
unaffected** — it reads the `#kpi-net`/`#kpi-dist` VALUE elements by ID (the numbers), not the
translated labels (the `'Net Cashflow'` strings in `auditRun` are internal report text, not DOM
lookups). To translate another card, wrap its label/tooltip text in `L('English','עברית')` and add
`langBtn` to its label. Pure frontend, live on merge — no Apps Script redeploy.

---

## 💸 Partner Distributions section (Jun 5 2026, PR #47) — Phase 2 item 1

A **Partner Distributions (You vs Nir)** section sits just below Monthly Breakdown. Pure
read of the Distributions tab; no new data needed. Answers the partners' #1 question: how
much each has taken out, this month and YTD.
- **SIMPLIFIED Jun 28 2026 (user request — "much simpler", lifetime "not realistic"):** the 3
  Lifetime tiles (`kpi-life-you/nir/total`) were **REMOVED**. Now just **2 dual tiles**:
  **This Month — You | Nir** (`kpi-dist-mo-you` / `kpi-dist-mo-nir`) and **YTD — You | Nir**
  (`kpi-dist-ytd-you` / `kpi-dist-ytd-nir`).
- **Own month dropdown** (`DIST_MONTH` / `distSetMonth()`, in the section `<h2>` like the
  Maintenance section) lists every month that has a distribution (newest first), defaults to the
  newest. The This-Month tiles reflect the picked month; YTD = Jan→picked month of that month's year.
  Independent of the main/Monthly-Breakdown picker.
- A **per-year table** (Year | You | Nir | Total) with an **"All time" total row** — KEPT as-is
  (handy at tax time; `byYear` + `lifeYou`/`lifeNir` still computed for the table only).
- **Self-audit updated** to recompute the **4 new tiles** (This Month + YTD, You & Nir) via the
  same `DIST_MONTH` logic — the old 3-lifetime-tile audit block is gone. Pure frontend, live on merge.

### 💰 Add Distribution modal — 50/50 default + Equal/Custom split (Jun 12 2026)
Reworked so Nir (or anyone) can enter the monthly distribution without confusion once the db is
shared. Pure **frontend** (`index.html`), **no Apps Script redeploy** — still saves the same
`your_amount` (Ron) + `partner_amount` (Nir) fields via the existing `add_distribution` action.
- New **`Split` dropdown** (`dist-split`, `distSetSplit()`): **`Equal — 50/50`** (default) shows
  ONE box **"Amount each ($)"** (`dist-each`) → on submit, fills BOTH Ron's and Nir's amount with
  that number. **`Custom — enter each`** reveals the two separate boxes for unequal/true-up months
  (and seeds them from the "amount each" value when you switch).
- The two amount boxes were **relabeled from "Your/Partner" to "Ron's Amount" / "Nir's Amount"**
  (fixed names — they do NOT flip based on who is signed in; the data model is always Ron =
  `your_amount`, Nir = `partner_amount`). This removed the POV trap where Nir, signed in as
  himself, would otherwise have to put his own figure in a box labeled "Partner".
- `submitDistribution` is now **mode-aware** (reads `dist-each` in equal mode, the two boxes in
  custom); `openDistModal`/`closeDistModal` reset the split to `equal`.
- ⚠️ **Dorado + Simon still NOT handled here** — the form only records Ron + Nir, so Dorado's
  3-way split (Ron/Nir/Simon) can't log Simon's third. The "amount each" number is still correct
  per partner, but Simon isn't stored (he was never in the Distributions tab). **TODO if user
  wants it:** add a Simon amount field shown only for Dorado (needs a `simon_amount` schema col +
  Apps Script redeploy + Partner Distributions section update). User was asked; deferred for now.
- **Sharing the db with Nir:** one shared password (`PASSWORD_HASH` in `index.html`) gates the
  whole dashboard — no per-user logins. Nir uses the same URL + password, sets **"Signed in as:
  N.S — Nir"** (top-right, remembered per browser, honor-system → Activity Log). He does NOT need
  ctrl-shift-r to enter data (page always fetches fresh + re-pulls after save). A hard refresh is
  only ever needed once to pick up a NEW version of the page itself.

> 🧭 **Investor decision (Jun 5 2026):** which Phase-2 metrics are worth it given our data:
> - ✅ Built: Partner distributions (above). Next: **CPA invoice workflow** (Paid By / Paid /
>   Notes + CPA-only filtered CSV/print view) — needs 3 new Maintenance Log columns (I/J/K) +
>   Apps Script redeploy; backward-compatible with existing 8-col rows.
> - ✅ Worth doing (no schema change): split repairs into **recurring vs one-off turnover**
>   (use the existing `Tenant Turnover` category) so a hit like the $8,000 Blackhawk doesn't
>   distort "true operating net". (Planned.)
> - ❌ Declined as dishonest-without-data: **cap rate, cash-on-cash, true NOI, expense ratio**
>   need inputs we don't track (cash invested / equity, gross rent for Dorado + out-of-state,
>   an opex breakdown). DSCR/equity/LTV already off the table. Don't fake them.

---

## 💵 Distribution Planner v2 — cushion + safe-to-distribute (Jun 13 2026)

> ### 🔁 ROLLING "until next income" cushion + auto roll-forward wording (Jun 30 2026, supersedes the late/early toggle)
> The user reported that on the 30th the **"Coming up this cycle"** list showed every bill as `✓ drafted`
> (the calendar-month "cycle" had ended) and the header still said "Coming up" — and that once a month's
> bills have drafted it should **roll forward to next month's bills**. Also surfaced a real bug: in `late`
> mode the cushion reserved bills by `day ≥ refDay` (a fixed window-day, NOT today's date), so on Jun 30 it
> was still reserving Divando's ACE(28th)/Insurance(29th) + Yale's Insurance(25th) that had **already
> drafted** → overstated cushion, understated safe-to-distribute. (Dorado's "41st end-of-month" worry =
> the **property tax**, correctly excluded from the cushion — no per-property utility was missing.)
> **User decisions (all via AskUserQuestion):** rolling **"until next income"** window · **fix the cushion**
> · income cutoff = **the 21st** · **remove** the After-bills/Early timing toggle · keep a dimmed/collapsed
> **"✓ Drafted this month"** reference group.
> **What changed in `index.html` (frontend-only, no redeploy):**
> - New helpers `nextDraftDate(fromDate, day)` + **`planUpcoming(key, c, fromDate, untilDate)`** (next draft
>   DATE of each recurring bill, rolling across the month boundary, seasonal `utilMonths` honored by the real
>   draft month) + const **`CASHPLAN_INCOME_DAY = 21`**.
> - The cushion now = **`planUpcoming(today → next 21st)`** sum + upcoming maintenance + buffer. So it reserves
>   exactly the bills that draft **before your next income deposit** (your balance must carry those until the
>   next paycheck); a bill that already drafted this month is gone → NOT reserved. **This matches the
>   `/monthly-distribution` skill** ("reserve all outflows before next income incl. next-month mortgage").
> - ⚠️ **Expected behavior:** at/near month-end the cushions look BIG and safe-to-distribute drops, because
>   next month's mortgage/SBA are imminent while income is weeks out (e.g. Jun 30: Divando holds Jul 1 SBA +
>   Jul 15 mortgage+utilities ≈ $17K). This is correct, not a bug — `balance − cushion` (the real surplus)
>   stays ~stable across the month. The flush window for an LLC is **after its mortgage drafts, before the
>   21st** (e.g. Donald's cushion = just its buffer ~Jul 10).
> - Display: header → **"📅 Coming up before your next deposit (Mon D)"** (rolls to next month once past the
>   21st); a `<details class="plan-drafted">` collapsed **"✓ Drafted this month (N)"** group lists this
>   calendar month's already-drafted bills (reference only, not reserved). Cushion/upcoming lines show the
>   bill's **actual draft month** (e.g. "Jul 15"), not always the current month.
> - **Removed:** `CASHPLAN_MODE`, `setCashplanMode`, `localStorage 'niron_cashplan_mode'`, and the
>   After-bills/Early toggle UI + `refDay` logic. `planExpenseItems` is kept (now only feeds the
>   drafted-this-month reference list). `CASHPLAN_CONFIG`/`CASHPLAN_DAYS` unchanged. Self-audit unaffected
>   (no `#kpi-*` IDs). Added `.plan-drafted` CSS (collapsible ▸/▾). Footer + intro text rewritten.

**REBUILT on a cushion model** (the PR #65 planner below was removed for running on the wrong
AppFolio net). This one is **frontend-only / localStorage v1** (no redeploy): `renderDistributionPlanner(data)`
in `index.html`, rendered **just BELOW the Monthly Breakdown section** (user swapped the two on Jun 16 2026
so Monthly Breakdown sits above the planner; order is True Cash → Monthly Breakdown → Planner → Partner
Distributions). Per LLC: you **type the current bank balance**
→ it subtracts a **cushion** (bills still coming) → shows **Safe to distribute** + **Each partner**
(÷2; Dorado **÷3** with Simon).
- **DATE-AWARE cushion (rebuilt Jun 16 2026, user choice "only reserve what's still coming").** The cushion
  reserves **only the recurring bills whose draft day ≥ `refDay`** (where `refDay` = 22 in `late` mode, 1 in
  `early` mode) **+ upcoming repair drafts (mailed checks) + safety buffer**. A bill that already drafted by
  your distribution date is gone from the typed balance, so reserving it would double-count (the same bug
  class as the debit-card / mortgage-on-wrong-day issues). `renderDistributionPlanner` builds
  `items = planExpenseItems(key, c, monthIdx)`, then `reserved = items.filter(it => it.day >= refDay)` and
  `cushion = sum(reserved) + repairsDue + buffer`. The breakdown lists each reserved bill with its date; if
  none are pending it shows "All fixed bills already drafted this cycle ✓". **Property tax is NOT in the
  cushion** (removed Jun 16 2026): annual lump (Divando/Dorado ~by May; Donald/Yale escrowed), tracked on the
  Property Tax tab + KPI tile. The **timing toggle** (`CASHPLAN_MODE`, localStorage `niron_cashplan_mode`,
  default **`late`**) sets `refDay`:
  - **`late` (~22nd–25th, recommended):** anything before the 22nd already cleared → not reserved → small
    cushion. For **Donald** (mortgage/SBA/insurance ALL draft in the first ~4 days) this means the late
    cushion = just the safety buffer (+ repair checks).
  - **`early` (1st week):** `refDay`=1 → everything still coming this month is reserved (incl. mortgage+SBA).
    This is the user's current habit and is **what caused the Yale overdrafts** (4/8, 4/15, 5/13 fees).
- **Per-LLC numbers** live in **`CASHPLAN_CONFIG`** (bank-verified Mar–May 2026, editable):
  - Divando (**REBUILT from 12-mo CSV, user-reviewed Jun 16 2026**): mort `12199.86` (~15th) · SBA `2334` (1st) ·
    ins `2909.98` (~29th) · **accountant `0`** · util `685` (~15th, lumped+tooltip) · **software `288.98`** (ACE Cloud
    Hosting, ~28th via Amex) · buffer `2000`
  - Donald (**REBUILT from 12-mo CSV, user-reviewed Jun 16 2026**): mort `13708` (CBRE, **1st** — was wrongly
    16th) · SBA `444` (1st) · ins `1210.84` (Westfield, **~4th** — was wrongly 28th; switched from State Farm
    ~Oct 2025) · acct `0` · util `336` **quarterly** (`utilMonths [0,3,6,9]` = Jan/Apr/Jul/Oct, Denver Compost,
    ~3rd) · software `0` · buffer `1500`. **All fixed bills draft in the first ~4 days** → in `late` mode the
    cushion is just the buffer. No Amex/software on Donald.
  - Yale (**REBUILT from 12-mo CSV, Jun 16 2026**): mort `7279.08` (Lument, ~6th — ✓ was right) · SBA `225`
    (1st) · ins `1037.55` (Acuity, **~25th** — was wrongly 28th) · acct `0` · util `315` **quarterly**
    (`utilMonths [0,3,6,9]`, Denver Compost, ~15th — was flat $105/mo) · software `0` · buffer `1500`. Insurance
    (drafts ~25th) IS reserved in `late` mode (after a 22nd distribution it's still coming). Bergman $969.48 = one-off.
  - Dorado (**REBUILT from 12-mo CSV, Jun 16 2026**): **mort `0` (mortgage-FREE)** · SBA `0` · ins `453.31`
    (National Indemnity, ~7th — ✓ was right) · **acct `0`** (Bergman $1,386 one-off) · util `454`
    **monthly** (Xcel + Denver Water + Compost, varies — **~5th**, was wrongly 20th; NOT quarterly like
    Donald/Yale) · software `0` · buffer `1000`, **÷3** (Ron/Nir/Simon). All fixed bills draft early month →
    `late` cushion ≈ buffer. Property tax (City&County/Adams, big) + the $138/mo Divando ins-comp transfer
    excluded from the cushion.
- **⚠️ Accountant (Jeff Bergman) is NOT a recurring monthly cushion item (user correction, Jun 16 2026).**
  The user confirmed the Divando **$3,255 was a ONE-TIME payment**, not a monthly bill, so it must NOT be
  baked into the planner's recurring cushion (it was wrongly showing as "Jun 15th · Accountant ✓ drafted
  $3,255"). `accountant` is now `0` in `CASHPLAN_CONFIG` for **all** LLCs and removed from `CASHPLAN_DAYS`
  (so it no longer appears in the dated "Coming up this cycle" list). This supersedes the earlier
  bank-CSV finding that called Bergman "recurring ~$3,255/mo" — the charges are actually occasional /
  per-project (varying amounts, different LLCs different months), so a fixed monthly reserve was wrong.
  If a known accountant bill is coming, enter it as a maintenance invoice (Paid By = Check) so it's
  reserved just for that month. (The True Cash bank-import section is unaffected — it reads the ACTUAL
  Bergman charge from each month's CSV, which is correct.)
- **Key bank findings (Mar–May 2026 CSVs):** (a) Bergman charges appear across months (Divando, plus
  occasional Donald $1,630.94 Apr / Yale $969.48 May / Dorado $1,386.51 May) but are **occasional /
  per-project, NOT a fixed monthly** (user confirmed) — so not in the recurring cushion. (b) **Dorado has
  NO mortgage and no SBA** (all 3 props free & clear). (c) Income (Laureate owner funds) lands ~the **18th–21st**; mortgages pull ~**15th–20th**
  (same window → why early distribution bounces). (d) Utilities/mo: **Divando ~$685** (Google+Xcel+Aurora
  Water+Denver Compost — varies monthly; user said lump it with a tooltip, NOT itemize), Donald ~$112,
  Yale ~$105, Dorado ~$454 (Xcel+DenverWater+Compost). Dorado pays Divando **$138/mo** ins comp.
  (e) **Divando Amex autopay (~$450/mo, ~28th): only the recurring `ACE CLOUD HOSTING` $288.98 is reserved**
  (user, Jun 16 2026 — "ignore the rest" of the Amex, the rest is variable/non-recurring). Stored as the new
  `software` field in `CASHPLAN_CONFIG` (Divando `288.98`, others `0`); shows as its own "− Software (ACE
  Cloud Hosting)" cushion line + a dated list item (~28th). (f) **Mortgage rebuilt:** it's 6 loan transfers
  = `12199.86` total drafting **~the 15th** (ranged 15th–21st across the year) — the old hardcoded "16th"
  made it light up as "today" on Jun 16; now `15th`, shows ✓ drafted by mid-month. Mortgage+SBA stay in the
  dated list as **✓ reference** (user choice) — visible but dimmed once past, and excluded from the cushion
  in `late` mode (already cleared before a 22nd–25th distribution).
- Balances persist in `localStorage 'niron_cash_balances'`; handlers `setCashBalance` / `setCashplanMode`
  call `renderAll()`. Self-audit unaffected (no `#kpi-*` IDs).
- **🎚️ Card layout aligned across all 4 (Jun 16 2026, user request "align tiles, professional").** Each
  `.llc-card` is a flex column (`height:100%`) with zones: `.plan-top` (balance+stamp), **`.plan-cushion`
  (`min-height:118px`** so the breakdown pads to equal height → the totals line up row-for-row),
  `.plan-totals` (Cushion to leave / Safe to distribute / Each partner — always 3 rows, `Each partner`
  shows `—` when no balance), and **`.plan-upcoming` (`margin-top:auto`** → pinned to the bottom so all
  cards bottom-align). User picked "totals aligned across all 4" (vs. bottom-aligned only). Pure CSS/markup,
  no logic change. ⚠️ A card with many maintenance invoices can exceed the 118px min-height and push its own
  totals down (acceptable edge case; bump min-height if it becomes common).
- **📅 "Coming up this cycle" dated list (Jun 16 2026):** each LLC card now shows a dated list of its
  recurring expenses (the user wanted to SEE upcoming expenses by date, not just the lumped cushion).
  `CASHPLAN_DAYS` holds the expected **draft day-of-month** per cost per LLC; `planExpenseItems(key, c)`
  builds the sorted list (amounts from `CASHPLAN_CONFIG`, days from `CASHPLAN_DAYS`); `ordinal()` formats
  the day. Rendered after "Each partner" as `📅 Coming up this cycle` — `<Mon> <day>th · <label>  $amt`,
  sorted by day; items with `day < todayDay` are **dimmed + "✓ drafted"**, `day === todayDay` shows
  **"today"** (amber). Repairs-just-paid + pending tax append as undated "soon"/"when due" lines.
  **Dates bank-verified where known** (SBA 1st, Yale Lument ~6th, Dorado Nat'l Indemnity ~7th, Divando
  State Farm ~29th/end-of-month, other mortgages ~16th mid-month) and **ESTIMATES otherwise** (utilities
  ~20th, accountant ~15th, Yale/Donald insurance ~28th) — footnote says "tell me to correct any." If the
  user gives exact draft dates, update `CASHPLAN_DAYS`. Frontend-only, live on merge.
- **🔧 UPCOMING MAINTENANCE reserve (broadened Jun 16 2026 — user: "upcoming maintenance is one of the most
  important things to know before distribution").** The cushion holds back **all maintenance still owed from
  this LLC's account**, not just mailed checks. `upcomingMaintenance(data, matchStr)` returns the LIST of
  `data.maintenance` rows for the LLC where: it's **UNPAID** (`!m.paid` — logged but not paid = upcoming
  spend) **OR** paid by **mailed `Check` within the last ~7 days** (about to draft, auto-clears after 7d).
  **Excluded:** `paid_by === 'Sent to CPA'` (CPA pays it, not this account) and paid-by-**Debit Card**
  (drew instantly → already out of the typed balance, reserving would double-count). The planner sums the
  list (`maintSum`), **always adds it to `cushion`** (it's owed money, not tied to a draft day), shows a
  **"− Upcoming maintenance (N invoices)"** line that **itemizes each invoice** (property/vendor + unpaid|check
  mailed + amount), and a "soon · Upcoming maintenance" line in the dated list. **So logging a repair invoice
  immediately reserves its cash before distribution** — that's the workflow. It is **ALWAYS shown on every LLC
  card** — when nothing qualifies it prints **"Upcoming maintenance: none unpaid (N already paid this month)"**
  so you can tell the planner checked vs. is broken (this resolved the user's "Divando didn't show maintenance"
  confusion — Divando just had no UNPAID invoices; paid-by-debit repairs are already withdrawn, not reserved).
  The reserve is fully generic by `c.match` — Divando/Donald/Yale/Dorado run identical code. **Frontend-only, no redeploy.**
  (Replaced the older narrow `upcomingRepairDrafts` which only caught paid-by-check-within-7-days and missed
  unpaid invoices — that was the gap the user hit.) ⚠️ Still keys off invoice date for the check-clearing
  window (no paid-date column); a Paid-Date column would need an Apps Script redeploy (not built).
- **Per-LLC "updated" stamp (Jun 14 2026):** `setCashBalance` also writes `localStorage
  'niron_cash_balances_ts'` (`{key: ISO}`); a small `updated <Mon D, YYYY, h:mm AM/PM ET>` line shows
  under each balance box (`fmtDateTime`). **Always Eastern time** (`timeZone:'America/New_York'`,
  hardcoded `ET` label — user picked one fixed zone, ET, so Ron + Nir always see the same stamp; NOT
  the viewer's local tz). Legacy balances (no saved ts) show "re-enter to set the date".
  A **"✓ Mark balances checked today"** button (`markBalancesChecked()`) stamps today on all entered
  balances WITHOUT changing the amounts — needed because re-typing the SAME number fires no `onchange`,
  so an unchanged-but-still-correct balance couldn't otherwise get a fresh date. The balance input also
  shows a **`$`** prefix. Per-LLC by design, but since the user enters all 4 in one sitting
  (logs into the bank, sees all accounts) they'll usually share the same stamp. Flags a stale balance.
- **🔭 Next (the redeploy batch):** save balances to a shared sheet tab so Nir sees them; add the
  **"Check Mailed" date** on maintenance (rename from "Paid", auto-reserve the check ~7 days then assume
  cleared — user wants NO manual "cleared"); set up a **recurring 22nd-of-month reminder** (Google Calendar)
  pinging "open dashboard, do distributions." User confirmed distribution cadence = **first week of the
  following month** historically, but was shown that shifting to ~22nd–25th (after mortgage clears) keeps the
  cushion small and stops the overdrafts — left as the `late`/`early` toggle for them to choose.

---

### 👁 Distribution Planner hide/show toggle — HIDDEN by default (Jun 28 2026)
The Distribution Planner section is now gated behind a **`👁 Show Planner` / `🙈 Hide Planner`
button** in the header button row (next to 📖 Monthly Guide, `id="planner-btn"`). Per-browser
state in `localStorage 'niron_show_planner'` (`'1'` = show, default/null = **HIDDEN**). Helpers in
`index.html`: `plannerVisible()`, `syncPlannerBtn()` (sets the button label, called at the top of
`renderAll`), `togglePlanner()` (flips the flag + re-renders). The render call at ~line 2161 is
`if (plannerVisible()) html += renderDistributionPlanner(data);`. **Why:** the user wants the
planner hidden until they walk Nir through it in person, then they'll decide whether to keep it
visible. Pure frontend, live on merge — no redeploy. To default it visible later, flip the toggle
in the browser or change `plannerVisible()` to default true. (Item #1 from the same request — the
invoice payment-lifecycle / "paid vs cashed" tracking — was discussed as **ideas only**, NOT built;
the user will decide after showing Nir the whole db. Gist: an invoice has a lifecycle sent-to-CPA →
check mailed → in transit → cashed, and cash only truly leaves at "cashed"; the fix direction is a
status field where anything not "Cleared" is held back from distribution, auto-clear ~10 days after
mailed, trued up by the monthly bank reconcile. Not implemented.)

### 💬 Header-button explanatory tooltips (Jun 28 2026)
All **6 header buttons** (🩺 Run Audit · 🧾 CPA Invoices · 📋 Activity · 📥 Import Bank · 📖 Monthly
Guide · 👁 Show/Hide Planner) now have **styled hover tooltips** written for a **first-time viewer**
(Nir/anyone): each is two short sentences — **what it does + what it's for**. Replaced the old terse
native `title=` attributes (removed from these 6 to avoid a double tooltip). Each button is wrapped in
`<span class="btn-wrap">` containing the button + a `<span class="btn-tip">`; CSS (`.btn-wrap` /
`.btn-tip` near the `.kpi-tip` block, ~line 60) matches the KPI-card `ⓘ` tooltip theme (dark
`#0c1a2e`, cyan border, instant on hover, 250px). The **3 rightmost** tooltips (Import Bank, Monthly
Guide, Show Planner) use **`.btn-tip.right`** (right-anchored) so they don't overflow the viewport
edge. `syncPlannerBtn()` still finds the button by `id="planner-btn"` (wrapping doesn't break it).
Pure frontend, live on merge — no redeploy. To add a tooltip to another button, wrap it the same way.

## ❌ Distribution Planner DROPPED + 🚨 Net Cashflow is UNDERSTATED (Jun 7 2026, PR #65)

**The Distribution Planner was REMOVED (PR #65).** The user reviewed 3 months (Mar–May 2026)
of actual bank statements for all 4 LLC operating accounts and the planner was badly wrong —
it told them "take ≈$4.6K each" in months where the accounts actually went **negative after
distributions** (overdraft fees on Yale 4/8, 4/15, 5/13; "COVER OVERDRAFT" transfers; Divando
wired Yale $2,850 in May just to stop it bouncing). **Do NOT rebuild a distribution planner
until Net Cashflow reflects true bank cash (below).**

### 🚨 ROOT CAUSE — the dashboard's `net_cashflow` OMITS large real cash costs
`net = disbursement − mortgage − insurance − maintenance(log)` (tax excluded). But the bank
statements show the owner ALSO pays, every month, from the operating account, things the
formula never subtracts:
- **Property TAX is real and recurring — NOT a "spring lump sum."** Bank shows it paid across
  Mar/Apr/May: Divando-area Denver/Arapahoe tax (Apr ~$7,680: City&County $2,721.32 + $2,399.30
  + Arapahoe $2,559.37; May City&County **$6,370.20**), Shelby Co TN tax on the Memphis manual
  props (Mar $614.47 + $3,064.74), Dorado City&County (May **$4,281.14**). The dashboard
  excludes Divando+Dorado tax entirely (`isTaxLumpSum`) → **the single biggest overstatement.**
- **Owner-paid city utilities** (not in formula): Xcel, Denver Water (DNVRWTR), City of Denver
  Compost, City of Aurora BillPay, Google. ≈ $600–800/mo Divando, ≈ $476/mo Dorado.
- **"BILL PAID-JEFF BERGMAN"** — recurring vendor (bookkeeper/contractor, NOT a partner),
  ≈$1,386–$7,482/mo across Divando/Dorado/Donald. Not in the formula. ⚠️ Need to confirm with
  user whether this is repairs (→ Maintenance Log) or bookkeeping/opex (→ new bucket).
- **Owner-paid repair checks** that may not be in the Maintenance Log: Donald checks 7251–7255
  (~$2,950/mo recurring + more), Yale checks 1207/1209/207, Divando checks 256/257/258.

**Net effect: the dashboard overstates portfolio net by ≈$25K+/month across the 4 LLCs.**
User approved (Jun 7 2026): **"make net = true cash"** — rework net so each LLC's monthly
number matches what actually nets out in the bank.

### 💸 DISTRIBUTION STRUCTURE — reverse-engineered from the bank (CONFIRMED)
The statements made the partner structure unambiguous (equal-split amounts on the same date):
- **Ron's distribution** = `BILL PAID-RONEN MOSCOVICH CONF #…`
- **Nir's distribution** = `TRANSFER … TO X9562` (account **X9562 = Nir's** personal account).
  (Proof: Donald 5/26 = Ronen $3,300 + transfer X9562 $3,300; Divando 5/26 = Ronen $4,000 +
  X9562 $4,000 — always paired & equal for the 2-partner LLCs.)
- **Simon Haviv** = `BILL PAID-SIMON HAVIV` — a **3rd EQUAL partner on DORADO ONLY.**
  (Proof: Dorado 3/20 = Ronen $5,200 + Simon $5,200 + X9562 $5,200 = 3-way equal split.)
- **Jeff Bergman is NOT a partner** — he's a vendor/expense.

### 🏠 DORADO LLC — corrected ownership & properties (user, Jun 7 2026)
**Dorado = 3 EQUAL partners: Ronen + Nir + Simon Haviv** (Simon is Dorado-only). So Dorado
distributions split **in THIRDS**, not halves (the other 3 LLCs are Ron/Nir 50/50).
**Dorado properties are ALL mortgage-free:** **4641 Enid Way**, **2397 Jamaica St**, and a
**fourplex on 41st** ("41st 4plex"). (Enid + Jamaica also ride Divando's State Farm policy per
the insurance note; Dorado credits Divando $138/mo, ends Dec 2026.) Dorado still pays real cash
costs the dashboard ignores: property tax (~$4,281 in May), utilities (~$476/mo), Bergman, and
its own National Indemnity insurance ($453.31/mo, 5/7).

### ✅ Plan (approved direction; confirm specifics before building)
Make `net_cashflow` = true bank cash. Cleanest accurate path = a **monthly bank-CSV importer**:
the 4 `*_Transactions_*.csv` exports already classify cleanly — Income = `OWNERFUNDS` credits +
Suncoast/MidSouth `WEB PMTS`; Distributions (exclude from net, track per partner) = `BILL PAID-RONEN`
/ `BILL PAID-SIMON HAVIV` / `TRANSFER … TO X9562`; inter-account `TRANSFER FROM/TO X####` =
exclude; everything else = expense. True net = income − expense; matches bank to the penny.
Dorado net ÷3, others ÷2. (Alternative = hardcode tax/12 + utility/opex estimates — less
accurate, lumpy tax.) STILL TO CONFIRM: what Bergman is; annual tax per LLC; whether owner-paid
repair checks should be logged. **Lesson: do NOT build distribution/cash tools on the AppFolio-
only net again — it is not true cash.**

### ❌ REMOVED — Bank-CSV importer + "True Cash — Bank-Verified" section (Jun 28 2026)
**The entire Import Bank / True Cash feature was DELETED** (user decision — it duplicated the
`/monthly-distribution` skill, which does the same bank-true-cash math better, and it sat empty
because it required manually re-importing CSVs in the browser every month + was per-browser so Nir
never saw it). Removed from `index.html`: the **📥 Import Bank header button**, the `bank-modal`,
`renderBankSection()` + its render call, and ALL bank JS (`BANK_ACTUALS`/`BANK_LLCS`/`BANK_MONTH`,
`parseBankFile`/`bankCategorize`/`handleBankFiles`/`bankStoredSummary`/`openBankModal`/`clearBankData`/
`bankAllMonths`/`bankSetMonth`/`blankBankMonth`/`parseCsvLine`). **Verified self-contained first:**
nothing else read `BANK_ACTUALS`, so no card/KPI/net/audit calculation changed. The Distribution
Planner (which was sandwiched BETWEEN the bank functions in the source) was carefully preserved.
The month-end bank-true-cash workflow now lives ONLY in the **`/monthly-distribution` skill** (chat) +
the **Distribution Decider** walkthrough added to the Monthly Guide modal (see that section). The
classification rules below are kept for reference (the skill mirrors them) but no longer run in the page.

#### (historical) The removed importer — Bank-CSV importer + "True Cash" section (Jun 7 2026)
Frontend-only (no Apps Script, no redeploy, no sheet changes — user was fed up with the redeploy
dance). In `index.html`:
- **`📥 Import Bank` header button** → `bank-modal`: user picks the monthly transaction CSVs
  (all 4 at once). `handleBankFiles` reads each **in the browser** (`File.text()`), `parseBankFile`
  detects the LLC from the `Account Name` column, classifies every line via `bankCategorize`, and
  aggregates per LLC per month. Stored in **`localStorage['niron_bank_actuals']`** (per browser;
  nothing uploaded — keeps sensitive distribution/partner data off the shared sheet).
- **True net = income − (mortgage+sba+insurance+tax+utilities+accountant+repairs+bankfee+other).**
  Distributions tracked separately per partner; inter-account transfers excluded.
- **`renderBankSection()`** renders a "💵 True Cash — Bank-Verified" section (between the
  Operational Health tiles and Monthly Breakdown) with its OWN month dropdown (`BANK_MONTH`,
  defaults newest imported), one card per LLC showing the full real-expense breakdown, **True Net
  Cash**, the month's total **Distributed** split per policy, "Left after payout" (red = drew down/
  overdrafted), and true-net-per-partner. Totals strip at the bottom. If nothing is imported, shows
  a prompt pointing at the Import button.

#### ⚖️ Distribution split = ALWAYS 50/50 (Dorado 1/3) — user rule (Jun 7 2026)
**Distributions are ALWAYS equal: Ron/Nir 50/50 on Divando/Yale/Donald, and Ron/Nir/Simon 1/3
each on Dorado.** The bank statements sometimes show UNEQUAL monthly per-partner amounts (e.g.
Divando Mar: Ron $11,750 vs Nir $8,000) because the partners **true up over time** — the user
confirmed the policy is always equal and does NOT want raw unequal amounts shown. So the Bank
section sums the month's TOTAL detected distributions and **divides equally** (÷2, Dorado ÷3) for
display; it no longer prints the raw per-line `dist_ron/dist_nir/dist_simon`. `m.distributed`
(total) still drives "Left after payout". Do NOT revert to showing unequal per-partner amounts.
- **Self-audit UNAFFECTED** — new section uses no `#kpi-*` IDs and doesn't touch the existing
  AppFolio-based cards/net (that stays as the auto-updating estimate until you import bank data).

#### 🔑 Categorization rules (validated to the penny vs the Mar–May 2026 CSVs)
- **Income** = any `Credit` (Laureate `OWNERFUNDS`/`VENDOR`, Suncoast/MidSouth `WEB PMTS`, refunds).
- **Distributions** (not expenses): `BILL PAID-RONEN…`=Ron, `BILL PAID-SIMON HAVIV`=Simon,
  `TRANSFER … TO X9562`=Nir (**X9562 = Nir's personal account**).
- **Exclude (zero-sum):** `TRANSFER` involving `DDA ACCT` or any own account
  (`X9364/X2321/X3442/X2189/X5369/X0422`).
- **Mortgage** = `TRANSFER TO LOAN` / `CBRE LOAN` / `LUMENT`. **SBA** = `SBA LOAN`.
  **Insurance** = STATE FARM/ACUITY/WESTFIELD/NATIONAL INDEMNITY. **Tax** = CITY AND COUNTY/
  TAXPYMT/CO TAX. **Utilities** = DNVRWTR/COMPOST/XCEL/CITY OF AURORA/GOOGLE. **Accountant** =
  JEFF BERGMAN (user confirmed: accountant). **Repairs** = CHECK#/DBT CRD/DDA B/P/BILL PAID(other)/
  AMEX. **Bank fees** = OVERDRAFT FEE. Else **other**.
- Verified output (true net): Donald Mar/Apr/May $3,207.57 / $1,109.96 / $757.87; Yale $5,379.35 /
  −$6,650.01 / $265.50; Divando $9,048.19 / −$601.26 / $7,780.78; Dorado $16,436.36 / $10,055.95 /
  $4,838.54. The importer detects per-partner lines to get the monthly TOTAL distributed, but the
  DISPLAY always splits that total equally per policy (see "Distribution split" above).

> 🔭 **Future (not built):** move bank actuals to a shared Google Sheet tab (so Nir/the Moss combined
> db see them) — deferred to keep this redeploy-free and to keep partner distribution data private.
> Then optionally REPLACE the AppFolio-based Monthly Breakdown net with bank-true net for imported
> months, and (only if the user revives it) a distribution planner built on TRUE net.

---

## 💰 Distribution Planner + investor-audit fixes (Jun 7 2026) — SUPERSEDED, SEE ABOVE

After a full investor-grade audit of BOTH tabs (the user reviewed screenshots of the
Master Portfolio + Noble Insurance tabs), these were built/fixed. The headline is the
**Distribution Planner** — it answers the owners' #1 question: *"after expenses and an
emergency cushion, how much can Ron and Nir EACH take this month?"* Pure frontend, lives
on merge.

### 💰 Distribution Planner (NEW section, `renderDistributionPlanner` in `index.html`)
Sits **just below the Operational Health tiles, above Monthly Breakdown**. Reads only data
already on screen (per-LLC `net_cashflow`, fixed costs, distributions) — no new sheet data.
- **Hero line:** big green "**You & Nir can each take ≈ $X**" for the selected month, with
  the total distributable + the You/Nir split beside it.
- **Reserve model (IMPORTANT — this resolved the user's fear):** the emergency reserve is a
  **ONE-TIME cushion ≈ 1 month of each LLC's fixed costs** (full mortgage incl. Divando's 6
  property loans + SBA, plus insurance — **repairs excluded**, too lumpy). It is **NOT
  re-deducted every month.** A **`RESERVE_STATUS`** toggle (localStorage `niron_reserve_status`,
  default **`funded`**) drives it: `funded` ⇒ distribute **100% of net**; `building` ⇒ this
  month tops the cushion up first (distributable = net − reserve). User was worried "1 month
  of expenses leaves nothing to distribute" — answer baked into the UI copy: the cushion is
  funded ONCE, then you take the full net. Default `funded` because the portfolio has been
  distributing for years ($230K lifetime), so the cushion is long since in place.
- **Net basis = REPORTED net as-is** (user choice — turnover-normalized net was offered and
  declined). So a heavy-repair month (e.g. the $8K Blackhawk) does lower distributable; that's
  intended/conservative.
- **Per-LLC distributable clamps negatives to 0** (`Math.max(0, net)`), so a loss-making LLC
  never drags down what the others can safely pay out.
- **4 supporting tiles:** Net Cashflow · Emergency Reserve (one-time, with funded/building
  state + 💡 tooltip) · Distributable This Month · **Retained in LLCs** (= YTD net − all
  distributions You+Nir YTD = cash sitting in the accounts, with 💡 tooltip).
- **Per-LLC table:** LLC | Net | 1-Mo Reserve | Distributable | Each (÷2) + TOTAL row.
- **Forward run-rate** caption: trailing-3-data-month avg net × months left in the year ÷ 2 =
  "~$Y more each could be available by year-end (estimate)."
- Uses no `#kpi-*` IDs → **self-audit unaffected** (its positional/ID reads don't see this
  section). To change the reserve definition later, edit `renderDistributionPlanner`'s
  `reserve = mortgage + extraMortgage + ins_mo` line.

### 🩹 Phase-1 correctness fixes shipped alongside
- **Per-property TOTAL caption (`renderPropertyDetailSection`):** the per-property TOTAL Net
  is property-level and **excludes each LLC's general SBA loan** (Divando $2,334 · Yale $225 ·
  Donald $444/mo). Added a one-line note under the table so the TOTAL ($14,933.75 for Divando
  May 2026) no longer looks like it contradicts the Divando card net ($12,599.77) — the gap is
  exactly the SBA, by design.
- **`enter_suncoast_manual.py` FIXED (real bug):** the GitHub-Actions manual-entry path wrote
  rows with the **property name in the LLC column** and a bare **`"Manual Entry"`** source, so
  those months were **invisible to the per-property monitor AND didn't roll up under Divando**.
  Now writes **LLC = `Divando LLC`** + **Source = `Manual Entry: <property>`** (matching what
  the dashboard `📋 Add Statement` modal / `addStatementEntry` already do), and `already_recorded`
  dedups on period_start + Source. (The dashboard modal path was always correct; only this
  Actions script was wrong.)
- **Chatbot `dashboardKnowledge()` (`AppsScript.gs`) precision fix:** now states Divando net
  uses the **Divando-owned insurance $2,473.08/mo** (full policy $2,885.83/mo includes 2
  Dorado units), and that **Dorado tax is also a spring lump sum** (not deducted). Keeps the
  chatbot from quoting the old $2,885.83 / Dorado-tax-deducted figures to Nir.
- **Removed dead code:** unused `recalcNet()` in `index.html`.

### ⏳ Outstanding USER actions (I can't do these from here)
- **Relabel the 3 April 2026 Divando "Manual Entry" rows** in the Google Sheet History tab:
  set col C = `Divando LLC` and col K (Source) = `Manual Entry: 8222 Hare Ave` /
  `Manual Entry: 3899 Joest Rd` / `Manual Entry: 6580 Stockport Dr`. Until then they stay out
  of the per-property monitor and may show as the audit's duplicate/"to review" warning.
- **Redeploy `AppsScript.gs`** for the chatbot knowledge fix to go live (Sheet → Extensions →
  Apps Script → paste → Deploy → Manage deployments → Edit → New version → Deploy). The
  `index.html` changes (planner, caption, cleanup) go live on merge with no redeploy.

### 🔭 Audit backlog (presented to user, NOT yet built — pick later)
Insurance tab: live renewal **countdowns** (dates are static text now) + insurance as % of
cash collected + surface the Dorado→Divando $138/mo "end Dec 2026" & "call IMA by Oct 2026"
as dated reminders. Master tab: mobile table overflow wrappers + de-clutter the per-property
control row; trim the redundant YTD-distribution tile (top KPI vs Partner Distributions);
drop the bars-chart "Occupancy %" metric (100/0 only); a tuned "needs attention" watch list
(must SKIP known-good cases — Holly/Bates fund-holds, Blackhawk turnover, per user). Turnover-
normalized net is also still available as a future toggle if the user reverses the "reported
net as-is" choice.

---

## 🧾 Property Tax tracker — 3rd main tab (Jun 8 2026)

A **`🧾 Property Tax`** main tab (3rd, next to Master Portfolio + Noble Insurance) tracks the
property tax the user **pays manually online** for Divando + Dorado, with Donald + Yale shown
as **escrow reference**. Built from the user's `Niron_Property_Taxes` Excel (uploaded Jun 8).

### Model = ONE annual payment per parcel (NOT two halves)
The user's spreadsheet tracks **one annual tax bill per property per year** (single paid date +
confirmation #), not Colorado's two halves. **I initially built a two-halves schema and scrapped
it** after seeing the Excel. Design (user-confirmed): single annual payment, **partials allowed**
(Amount Due + Amount Paid → Balance); **current-year focus with prior years shown small**;
**include Donald/Yale as escrow**; **include routing/account** (user OK with partner seeing them).

### Data — `Property Tax` Google Sheet tab (auto-created + seeded)
`AppsScript.gs → ensurePropertyTaxTab()` creates + seeds the tab on first read if missing (like
`logActivity` lazily creating Activity Log). Title row 1, headers row 4, **data from row 5**.
Columns A–R: `LLC · State · Property · County · Parcel/PIN · Tax Year · Amount Due · Amount Paid ·
Paid Date · Paid By · Confirmation# · Tax Link · Routing# · Account# · Prior Yr1 · Prior Yr2 ·
Prior Yr3 · Comments`. Routing/Account/Confirmation are written **as text** (apostrophe prefix in
`setValues`) so big account numbers don't lose digits. The seed = all 20 rows from the Excel with
**real** amounts, parcels, county links, paid dates, and prior-year history (2025/2024/2023).
- **`getDashboardJson`** (live copy) reads it → `data.property_tax` (each row tagged with absolute
  `row` for edit/delete).
- **`doPost`** routes `add_property_tax` / `update_property_tax` / `delete_property_tax` →
  `addPropertyTaxEntry` / `updatePropertyTaxEntry` / `deletePropertyTaxEntry` (write 18 cols,
  `logActivity`). All in the **live (last)** doPost + after `addStatementEntry`.

### Paid/Outstanding logic (the yellow rule)
In the Excel, **green = paid, yellow = still owed** (will be paid after the next disbursement).
Seed sets yellow rows to **Amount Paid 0 + blank paid date**; green rows Paid = Due. Status is
**derived** (`taxStatus` in `index.html`): **binary** — Escrow (paid_by contains "escrow") else
Outstanding when Owed > 0 else Paid. **Never a dash** (user request, Jun 8 — a blank/$0 Tax Bill
row now reads Paid, not "—"). **Outstanding $ excludes escrow** (lender pays).
Validated against the Excel: Divando outstanding = Crown `$1,328.82` + 15655 13th `$2,459.00` =
**`$3,787.82`**; Dorado = 41st `$2,944.56` + Enid `$1,087.20` = **`$4,031.76`** (matches the
sheet's "2026 3/25 due Dorado 4031.76" line). Sold 2116 4th Ave kept as a `[SOLD]` $0 row.

### Dashboard (`index.html`, pure frontend)
`renderTaxSection()` (called from `initialRender` + on `switchMainTab('tax')`) renders into
`#tax-content`: an outstanding banner (yellow $ owed, split per LLC), a 3-tile KPI strip (Tax Due ·
Paid · Outstanding), then a table grouped by LLC (Divando → Dorado → Donald/Yale escrow) with
Property · County · Parcel · **Tax 2026** (full annual bill) · Paid · **Owed** (bill − paid) · Status badge · Paid Date · **Tax 2025** (prior-year amount, `lastYrCell`) ·
💳 Pay link · ✏️ edit / 🗑 delete. The **Tax 2025** column is **hidden by default** behind a
**👁 Show 2025 / 🙈 Hide 2025** header toggle (`toggleTax2025()`, localStorage `niron_tax_2025`,
default off): when hidden the column is fully omitted (no header/cell, colspans + table min-width
shrink 11→10 cols / 1040→960px); Show widens the table to fit it. Choice is remembered per browser.
Edit/Add uses the **`tax-modal`** (`openTaxModal`/`submitTax`/
`deleteTax`); setting a Paid Date auto-fills Amount Paid to Amount Due (`taxAutofillPaid`).
Deep-link `?tab=tax`. Self-audit unaffected (no `#kpi-*` IDs).

### 🚀 Going live (REQUIRED) — redeploy AppsScript.gs
The `index.html` side goes live on merge, but the **tab data + reads/writes need the Apps Script
redeploy** (Sheet → Extensions → Apps Script → paste new `automation/AppsScript.gs` → Deploy →
Manage deployments → Edit → New version → Deploy). The `Property Tax` tab auto-creates + seeds on
the first dashboard load after redeploy. No new permission scope (no DriveApp).

> 🔭 TODO / open: parcel column left blank for most (full parcel/transaction text is in Comments);
> the user can split it out later. Confirm the yellow Dorado 41st/Enid are truly still owed (their
> Excel rows had stray 5/26 paid dates but were yellow + matched the "due" line — treated as
> unpaid). When 2027 rolls in, the prior-year columns + Tax Year need bumping (no auto-roll yet).

### 🤖 Auto-fill Amount Due from county sites — ATTEMPTED & ABANDONED (Jun 8 2026)
User asked to automate reading each county's live balance into Amount Due. Built a Playwright
scraper (`automation/run_tax.py` + `tax_update.yml`, calibration-first) and ran 3 real calibration
passes on GitHub Actions. **Verdict: NOT FEASIBLE — every county portal blocks automated access**,
so the files were **REMOVED** (user decision). Do NOT rebuild this without a new approach.
- **Denver** (denvergov.org): **Radware bot-detection wall** — serves the headless browser a blank
  ~1,070-char shell with no figures (captured an `rb_…?type=js3` bot-manager script). 7 parcels.
- **Duval FL** (county-taxes.com): **Cloudflare Turnstile CAPTCHA** (captured a
  `challenges.cloudflare.com/.../turnstile/` challenge) — needs a human checkbox.
- **Adams** (adcotax.com): the `account.jsp` deep link **redirects to `login.jsp`** — balance is
  behind a sign-in.
- **Arapahoe** (search form) + **Memphis** (payit901) were already phase-2 search forms; same class
  of protection expected.
- Naive fetches also 403 (confirmed via WebFetch on denvergov + adcotax). Getting past these would
  need CAPTCHA-solving services / residential proxies / credential automation — fragile, ToS-violating,
  and inappropriate for this tooling. **Property tax stays MANUAL** (the ✏️ edit on each Property Tax
  row is the intended fast path: paste amount + paid date + confirmation #, balance/banner update live).
  Reusable lesson: county treasurer sites are anti-bot — don't promise live-balance scraping.

### 🔢 Parcel # as copy-chip + corrected county "Pay" links (Jun 8 2026)
Since auto-fill is impossible, the manual flow had to be smooth. Two fixes in `index.html`
(frontend-only, live on merge):
- **The stored "Pay" deep links were dead** — Denver retired `…/property/realproperty/taxes/<parcel>`
  (now a 404 "Uh oh" page), Adams' `account.jsp` forces a login, Arapahoe moved domains. `taxPayLink()`
  now keeps the stored link UNLESS it matches a known-dead pattern, in which case it sends the user to
  the county's working **search page** (`TAX_COUNTY_SEARCH`): Denver = the official **Pay-Property-Taxes**
  page (`…/Treasury/Property-Taxes/Pay-Property-Taxes`, user-confirmed; a secondary "Make a Payment"
  link was added then REMOVED per user — single Pay link only), Arapahoe
  `arapahoeco.gov/.../treasurer/tax_search.php`, Adams = a **per-account deep link**
  `adcotax.com/treasurer/treasurerweb/account.jsp?account=<R-acct>` built from each property's R-account
  (user-confirmed it works for a logged-in human — it only bounced the scraper to login;
  `treasurerweb/` is the fallback). Duval/Memphis deep links still work for a human, so they're kept.
- **The parcel # was buried/truncated in Comments.** `TAX_PARCEL_INFO` holds the clean parcel/account #
  per property (keyed by the normalized property name; Adams uses the R-account #, which its guest search
  accepts). The Parcel/PIN column now renders a **click-to-copy `.tax-parcel` chip** (`copyParcel()` →
  clipboard, "✓ copied" feedback). Display precedence: sheet col E if the user filled it, else the map,
  else blank. So adding a new property still shows whatever parcel is typed into the sheet.
- Parcels (authoritative): Denver schedule #s 00193-10-013-000 (43rd), 00181-02-016-000 (Dearborn),
  01241-13-015-000 (Blackhawk), 00185-06-020-000 (Crown — the Excel's Pay link wrongly pointed at
  Blackhawk's parcel), 01292-08-022-000 (Holly), 02214-26-001-000 (Dorado 41st), 00191-04-005-000
  (Enid), plus escrow 06301-31-014-000 (Donald), 05321-02-022-000 (Yale). Arapahoe PINs 031319692
  (13th), 031500222 (Bates), 031164265 (Virginia). Adams accounts R0095746 (Oakland), R0093130 (Tucson),
  R0094745 (Boston), R0096240 (Jamaica). Duval 144116-0000 (Hare), 029712-0000 (sold 4th). Memphis
  071037 00010 (Joest), 071037 00000100 (Stockport). To add a county, extend `TAX_COUNTY_SEARCH` +
  `TAX_PARCEL_INFO`. Self-audit unaffected (no `#kpi-*` IDs).
- **Parcel chip now shows a county "kind" label** (`TAX_COUNTY_KIND`): Denver `Parcel ID` (user renamed
  from "Schedule"), Arapahoe `PIN`, Adams `Acct`, Duval/Memphis `Parcel` — because Arapahoe has a **PIN
  and a different AIN**, so the user must know which number to enter. The label is display-only; the click
  still copies just the number. 15655 E 13th's value `031319692` is the **PIN** (the AIN `197505203015`
  is a different number).
- **Table styling + blink (Jun 8 2026):** the Property Tax table has scoped CSS (`#tax-content`):
  sticky header, right-aligned tabular-num money columns (`.num`) + centered Status (`.ctr`), subtle
  zebra row shading (`tr.tax-alt`, on data rows only — replaced the grid lines per user), row hover,
  an LLC section band (`tr.tax-llc`), a **red subtotal
  band** (`tr.tax-sub`, user request — label+owed in red), and a faint red tint + red left-accent on
  **Outstanding rows** (`tr.tax-out`). The Outstanding **status badge is a SOLID red pill**
  (`taxStatus` → `color:#fff, bg:#d92f43`, white text), and every Outstanding marker (badge +
  Outstanding/Property-Tax-Owed KPI tiles when >0) carries `.tax-blink`.
  ⚠️ **`.tax-blink` is NO LONGER animated** (Jun 9 2026): the user found the opacity flicker/pulse
  "very bad looking" — twice. It is now a **static** `font-weight:700` emphasis only (red color comes
  from the inline styles / solid badge). **Do NOT re-add any opacity/blink/pulse animation to it** —
  the user explicitly chose "solid red, no motion."

### 🐛 Edits "not saving" (revert to old value) = browser-cached GET, FIXED (Jun 8 2026)
User reported Property Tax edits (e.g. set Amount Due 0) reverting to the old value "hence not
saving." Root cause was NOT the save — the POST writes fine; the dashboard re-read a **browser-cached**
copy of the Apps Script `/exec` GET, so the just-saved value didn't show. Fix in `index.html`:
**`dashGet()`** = `fetch(API_URL + '?cb=' + Date.now(), {cache:'no-store'})`, now used by `load()`,
`reloadTax()`, and the audit refresh (all the GET reads). Apps Script ignores the extra `cb` param.
If an edit STILL reverts after this + a hard refresh, THEN it's a stale Apps Script deployment →
redeploy (New version). (Holly/Tucson showing "Paid" is separate: they were seeded paid from the green
Excel rows — the user sets Amount Paid 0 + clears Paid Date to flip them to Outstanding.)

> ⚠️ **Cannot write the live sheet from the agent box** — the Apps Script `/exec` endpoint is "Host not
> in allowlist" (sandbox blocks `script.google.com`), and the county sites block scraping. So dollar-
> amount / paid-status corrections must be done by the user via the ✏️ Edit modal (or directly in the
> sheet). User-reported current amounts owed (Jun 8 2026, to be entered via ✏️): 15655 E 13th **$2,509.18**,
> Dorado 1460 W 41st **$3,035.64**, Dorado 4641 Enid **$1,120.81**; and **Crown** must read **Outstanding**
> (set Amount Paid 0 + clear Paid Date) — it was showing fully paid.

### 🏠 "Property Tax Owed" KPI tile + chatbot knowledge + intro reword (Jun 8 2026)
- **New Master Portfolio KPI tile `kpi-tax-due`** ("Property Tax Owed") added to the top
  summary-grid in `renderAll`, **between Your Distribution and the Mortgage/Value card**.
  Value = total outstanding property tax = `Σ taxOutstanding(r)` over `data.property_tax`
  (escrow rows return 0, so Donald/Yale never count). **Static red** (`.tax-blink` = bold only, no
  animation; value color `#ff4455`) when owed > 0; green `all paid` when 0. The tile is **click-through**
  to the Property Tax tab (`onclick="switchMainTab('tax')"`).
- **"Shrink the 2 right cards" (user request):** the two former single cards **Total Mortgage /
  Mo** (`kpi-mort`) + **Portfolio Value** (`kpi-value`) were merged into **ONE `summary-card
  dual`** (two half-cells + divider) so they each take half width, making room for the new tax
  tile. **IDs `kpi-mort`/`kpi-value` were preserved** → self-audit unaffected.
- **Chatbot now knows the Property Tax tab.** Added a **`=== PROPERTY TAX ===`** section to the
  **live (last, ~line 1301) `buildPortfolioContext()`** in `AppsScript.gs` (reads the `Property
  Tax` tab: per-parcel bill/paid/owed/status + TOTAL outstanding + per-LLC outstanding; escrow
  excluded from owed). Also: system prompt now says **FIVE sections** with a new **#5 PROPERTY
  TAX**, and `dashboardKnowledge()` got a **PROPERTY TAX TAB** paragraph. ⚠️ Chatbot changes need
  the usual **AppsScript redeploy** to go live (New version). User hasn't tested the chatbot on
  this tab yet.
- **Intro sentence reworded** (user dropped the yellow/green legend): now just "You pay these
  online, one bill per parcel per year. ✏️ a row to record what you paid (date · amount ·
  confirmation #) and the balance updates. Donald & Yale are escrow (lender pays)."
- `index.html` parts (tile, merged card, sentence) go live on merge; the chatbot part needs the redeploy.

---

## 🎨 Main tabs — refined sliding pills (Jun 8 2026)

The 3 main tabs (Master Portfolio · Noble Insurance · Property Tax) were restyled from
heavy full-width gradient buttons to a **refined segmented control with a sliding highlight**
(user pick; the old look felt sloppy/unbalanced). `.main-tab` is now auto-width (`flex:0 0 auto`,
not stretched), transparent, with brighter inactive text (`#8aa6c4`) and white when active — the
background is provided by a single **`.tab-thumb`** pill (`#tab-thumb`, absolutely positioned in
the `position:relative` `.main-tabs`) that **slides** between tabs via a CSS transform transition.
`positionTabThumb()` sets the thumb's `translateX`/width/top/height from the active button's
`offsetLeft`/`offsetWidth`/`offsetTop`/`offsetHeight`; it's called at the end of `switchMainTab`,
on `window resize`, and on `document.fonts.ready` (so it stays aligned after the web font loads).
Emojis were kept as-is (user chose "leave icons alone"). Pure frontend, live on merge.

### 🔲 Boxed tabs for separation (Jun 28 2026)
User wanted visual separation between the (now 6) main tabs. Each `.main-tab` now reads as its own
**outlined box** (`border:1px solid #243750` + faint `rgba(255,255,255,0.025)` bg, gap bumped 4→8px);
hover brightens border+bg. The **active tab goes `background:transparent; border-color:transparent`**
so the existing blue **`.tab-thumb` sliding highlight shows through behind it** (user chose: boxed +
keep the sliding highlight). The thumb is sized from the active tab's `offsetWidth/Height` (border-box),
so the 1px transparent border keeps it aligned — no `positionTabThumb` change. Pure CSS, live on merge.

### 🏦 Loan Details moved to its OWN main tab (Jun 28 2026)
The **Loan Details per LLC** table used to render at the BOTTOM of the Master Portfolio page
(inside `renderAll`). User moved it to its **own 4th main tab `🏦 Loan Details`**, placed to the
**right of Property Tax** (order: Master · Noble Insurance · Property Tax · Loan Details). User
decisions: **move it** (removed from Master, not duplicated) + **add per-LLC subtotals + a grand
TOTAL monthly-debt row**.
- **Frontend (`index.html`, pure — no redeploy):** new pane `#tab-loans` / `#loans-content`; new
  `renderLoansSection()` (placed just before `renderTaxSection`) reads `PORTFOLIO_DATA.loans`
  concatenated with `DIVANDO_PROPERTY_LOANS` (the 6 Divando property mortgages aren't in the Loans
  sheet), groups rows by LLC, prints a **"<LLC> — monthly total"** subtotal per LLC and a bottom
  **"TOTAL — monthly debt (all LLCs)"** row (red). Has the same `ⓘ` tooltip pattern explaining the
  numbers are monthly payments, not remaining balances.
- **Wiring:** `switchMainTab` handles `'loans'` (chat tag `LOAN DETAILS`, calls `renderLoansSection()`,
  persists `?tab=loans`); the `?tab=` deep-link parser + URL-persist list now include `loans`;
  `initialRender` calls `renderLoansSection()` after data loads. The old loan block in `renderAll`
  (the `allLoans`/"Loan Details per LLC" section ~line 2275) was deleted. Self-audit unaffected (it
  never footed the loan table; the histSec lookup is scoped to `#tab-master`).
- Dorado shows **PAID OFF $0.00** (from the Loans sheet) → its subtotal is $0, correct.
- **Redesigned to CARD layout (Jun 28 2026, user request — the wide table "looked messy").** User
  reviewed a band-header table version and rejected it (full-width stretch, tall rows, repeated
  colored tags = noise). Final design (user-chosen via 4 questions): **compact card per LLC + a
  summary tile strip + NO tags + shortened lender (full address on hover)**. Scoped `#loans-content`
  CSS only — no table.
  - **Summary tiles** (`.loan-tiles`): a highlighted **Total Monthly Debt** tile (red value) + one
    small tile per LLC (label = `shortLlc(name)`, value = that LLC's monthly total).
  - **Cards** (`.loan-cards` grid, `repeat(auto-fill, minmax(320px,1fr))`): one `.loan-card` per LLC
    with a header (LLC name + `$X/mo` total, green; grey when $0) and one `.loan-row` per loan
    (lender left, amount right). Dorado (paid off) → `.paid` styling, row reads "No loan (paid off)".
  - **No type tags** (removed `loanTag`). **Lender shortened** via `loanShort(lender)`: Divando's
    long "Property Mortgage — <addresses> (acct 0210)" becomes **"Property Mortgage · acct 0210"**
    with the **property list on hover** (native `title`, dotted-underline `.has-tip` hint); CBRE /
    SBA / Lument show as-is. Amounts right-aligned tabular-nums.

### 🏠 Per-Property Monitor moved to its OWN main tab (Jun 28 2026)
The **Per-Property Monitor** (the multi-LLC Divando/Yale/Donald section with the chart + table +
LLC/chart/month/metric dropdowns) was moved off the Master Portfolio page into its own **5th main
tab `🏠 Property Monitor`**, right of Loan Details (order: Master · Noble Insurance · Property Tax ·
Loan Details · Property Monitor). User decisions: **move it** (removed from Master) · **keep the LLC
dropdown / all 3 LLCs** · **visuals unchanged** (just relocated).
- **How (pure frontend, no redeploy):** new pane `#tab-props` / `#props-content`. `renderAll` no
  longer appends `renderPropertyDetailSection(...)` to the Master `#content`; instead, right after
  `el.innerHTML = html`, it does `document.getElementById('props-content').innerHTML =
  renderPropertyDetailSection(data, maintenance)` and still calls `renderPropertyChart()` (the
  `#propChart` canvas now lives in the props pane). All the `pdSet*` controls still call `renderAll`,
  so the pane rebuilds on every interaction.
- **Chart-while-hidden fix:** a Chart.js canvas drawn while its pane is `display:none` comes out
  0-sized, so `switchMainTab('props')` calls `renderPropertyChart()` again to redraw at full size
  once the pane is visible.
- **Wiring:** `switchMainTab` handles `'props'` (chat tag `PROPERTY MONITOR`, persists `?tab=props`);
  the `?tab=` deep-link parser + URL-persist list include `props`.
- **⚠️ Table-CSS scoping fix (Jun 28 2026):** the per-property table came out cramped/unstyled on the
  new tab because the table rules (`width:100%`, th/td padding/borders, `.green`/`.red`) were scoped
  to **`#tab-master`** only. Fixed by extending those 6 selectors to **`#tab-master, #tab-props`** so
  the moved table looks identical to before. **Lesson: when moving a styled section to a new pane,
  any `#tab-master`-scoped CSS it relied on must be extended to the new pane id.**
- **Self-audit kept:** the audit's per-property check looked up `secByTitle('Per-Property Monitor')`
  scoped to `#tab-master`; widened to search **all panes** (`document.querySelectorAll('.section h2')`)
  so the per-property table/chart/TOTAL checks still run from the new tab. (The History `secByTitle`
  stays `#tab-master`-scoped — that table is still on Master.)

---

## 📖 Monthly Guide & Distribution Decider button (Jun 8 2026 · renamed + expanded Jun 28 2026)

A header button (`id="guide-btn"`) opens a static checklist modal (`guide-modal`,
`openGuideModal`/`closeGuideModal`, toggles the `.open` class — no render function, content is
hardcoded HTML). User-picked shape: **in-dashboard button · Niron only · everything end-to-end ·
partner-shareable** (written so Nir/Oshrat could follow it). Pure frontend, live on merge.

**Renamed Jun 28 2026** from `📖 Monthly Guide` → **`📖 Monthly Guide & Distribution Decider`** (user
picked this exact name) when the Import Bank / True Cash feature was removed. The old step 6 ("📥
Import Bank CSVs for the True Cash section") was **deleted** and replaced by a **"💸 Distribution
Decider"** explainer block appended after the checklist — a step-by-step of **how we decide what's
safe to distribute** (so Nir can see the logic; Ron actually runs it via the `/monthly-distribution`
skill). The decider block mirrors the skill: ending balance − per-LLC cushion (Divando $2,000 ·
Donald $1,500 · Yale $1,500 · Dorado $1,000) − uncleared repair checks − bills before next income −
inter-account amounts owed = safe ceiling, split Ron/Nir 50/50 (Dorado Ron/Nir/Simon ⅓), rounded
**down to nearest $50**; an account that can't cover its cushion + upcoming bills → take $0. Keep
this block in sync with the `/monthly-distribution` SKILL.md if the cushions/rules change.

The guide's ordered steps (keep in sync if the workflow changes): **(0)** set "Signed in as" + pick
the new month first; **(1)** confirm the AppFolio auto-pull landed (runs daily 15th–25th, the 4 LLCs
are automatic — nothing to push); **(2)** 📋 enter the 3 out-of-state statements (Hare/Joest/Stockport,
deposited amount not NOI, roll up under Divando); **(3)** 🔧 maintenance invoices (Paid By + CPA flag);
**(4)** 💰 partner distributions (Ron/Nir, Dorado +Simon, equal split); **(5)** 🧾 Property Tax tab — ✏️
record paid date/amount/conf# only when a bill is actually paid (Donald/Yale escrow = nothing);
**(6)** 🩺 Run Audit chip + eyeball the cards. Then the **💸 Distribution Decider** explainer block.
Note in the modal: order matters most for step 1; 2–5 are any order, then verify (6).

---

## 🗓️ Month picker = data months + current month (Jun 5 2026, PR #50)

The header/inline month dropdown offers every month present in History **plus the current
calendar month** (`currentPeriod()` → e.g. `2026-06-01`), so the user can select the current
month and work in it (enter statements / maintenance / distributions) **before** its AppFolio
data has landed. `pickerMonths` (data ∪ current) drives the dropdown; the trend chart still
uses `months` (data only) so there's no zero-dip. The default `SELECTED_MONTH` stays the
**newest month with data**, so it auto-advances to the new month the moment that month's data
arrives (no yearly maintenance). The self-audit treats the current month as a valid selection
even with no data (no false "month not in data" fail).

---

## 📋 Activity Log + "Signed in as" + Last-Updated fix (BUILT — Jun 5 2026, PR #53)

Every change is now logged with **who + when + what**, and "Last Updated" reflects it.

- **"Signed in as" picker** in the header (`actor-select`: R.M / O.M / N.S, stored in
  `localStorage('niron_actor')`, restored on load). Self-reported (one shared password, so
  it's honor-system, same as the Save modal). **Every write requires it** — `ensureActor()`
  blocks the save with an alert if nobody is selected.
- The frontend sends `actor` on **every** write (maintenance add/edit/delete, mark-paid,
  distribution, statement). Each Apps Script handler calls **`logActivity(actor, action,
  details)`**, which appends to a new **`Activity Log`** tab (`Timestamp · Who · Action ·
  Details`, auto-created, wrapped in try/catch so logging can never block the real write).
- **📋 Activity button** in the header opens a modal listing the feed (When · Who · What,
  newest first). Built from `data.activity` = the Activity Log rows **+ synthesized
  "System - Automation" entries** derived from History `logged_at` + Property Detail
  `updated` (grouped per batch timestamp), so the automatic AppFolio pulls appear too.
  Capped at 200 newest.
- **"Last Updated" fix:** `getDashboardJson` now bumps the change-timestamp from the
  Activity Log too (not just History/Property Detail), so adding a maintenance invoice today
  correctly shows today. (Before, maintenance writes carried no timestamp, so the stamp
  stayed on the last AppFolio/statement write — that was the 6/4-vs-6/5 bug.)
- Self-audit unaffected; the audit's month/data checks still pass.

### 🚀 Going live (REQUIRED) — redeploy (no new permission this time)
Paste new `automation/AppsScript.gs` → Deploy → Manage deployments → Edit → New version →
Deploy. The `Activity Log` tab is created automatically on the first logged change. The
`index.html` side goes live on merge. **"Who" is only recorded going forward** — changes made
before this won't have a person attached (they appear as automation/unknown).

### 🐛 "Last Updated" still showed 6/4 after a 6/5 invoice (Jun 6 2026) — DEPLOY GAP, not a code bug
User reported the header "Last Updated" still read **6/4/2026 7:47 PM** after adding a
maintenance invoice on **Jun 5**. Diagnosed: the **`index.html` side of PR #53 is live**
(the Activity / CPA / Run Audit buttons are visible), **but the Apps Script backend was
NOT redeployed.** `last_updated` is computed **server-side** in the deployed web app
(`getDashboardJson` → `bumpChange` off the Activity Log + History `Logged At` + Property
Detail `Updated`). The repo's `AppsScript.gs` is already correct (adding an invoice calls
`addMaintenanceEntry` → `logActivity` → an Activity Log row dated 6/5 → `bumpChange` →
`last_updated` = 6/5). The OLD deployed code has no Activity-Log read, so a maintenance add
carries no timestamp and the stamp stays on the last AppFolio/Property-Detail write (6/4).
**Fix = the required PR #53 redeploy** (Sheet → Extensions → Apps Script → paste new
`AppsScript.gs` → Deploy → Manage deployments → Edit → New version → Deploy). No code change
was needed. (Caveat: invoices added **directly in the Google Sheet** rather than via the
dashboard 🔧 button never log to the Activity Log, so they also won't bump the stamp — that
is expected, the bump is tied to dashboard writes.)

### 👤 "Signed in as" picker added to the Maintenance card (Jun 6 2026)
User hit the `ensureActor()` block ("Please pick who you are first…") when adding an invoice
because the only actor picker was in the **header (top-right)** — easy to miss. Fix: added a
**second "Signed in as" `<select>` at the TOP of the Add/Edit Maintenance modal, before the
Date box** (user's exact request). Both pickers carry class **`.actor-pick`** and are kept in
sync by **`syncActorSelects()`** (sets every `.actor-pick` to `getActor()`); `setActor()` and
`restoreActor()` now call it, and `openMaintModal`/`openMaintEdit` call it on open so the modal
shows whoever is already signed in. `closeMaintModal` does NOT reset `maint-actor` (the person
persists). The `ensureActor()` alert now says "at the top of this form, or top-right" and
focuses the open modal's picker if there is one. Pure frontend, live on merge — **no Apps
Script redeploy needed for THIS change.** (Reminder: the invoice **file upload** itself still
needs the PR #48 Drive-scope redeploy, and Activity-Log / Last-Updated still need the PR #53
redeploy — those are separate backend deploys.) To add another actor-aware modal later, just
give its picker `class="actor-pick"` and it auto-syncs.

### 🗑 Delete (trash) button painted red on the Maintenance table (Jun 6 2026)
User: "the trash can, paint it red as I can't see it." The 🗑 in each Maintenance row was a
faint emoji at `opacity:0.7` on the near-black background. Fix in `index.html`: `.maint-del-btn`
now has a **permanent red look** (`color:#ff4455; border-color:#ff4455; background:#ff445522;
opacity:1`) instead of only turning red on hover, and the glyph carries a text-presentation
selector (`🗑&#xFE0E;`) so it inherits the red `color` rather than rendering as a multicolor
emoji. The ✏️ edit button is unchanged (still neutral until hover). Pure frontend, live on merge.

### 🗓️ History table month shown by name, not `YYYY-MM-DD` (Jun 6 2026)
User: "the month must be by name not number (jan feb…)." The **History (newest first)** table
was the ONLY place still printing the raw `period_start` (`2026-05-01`) even though its column
header says "Month" — every other section already used the `monthLabel()` helper
(`MONTH_NAMES` → "May 2026"). Fixed in `index.html` (the `sortedHistory` row render): now
`monthLabel(h.period_start)` → **"May 2026"**. Pure frontend, live on merge. Self-audit
unaffected (it recomputes from `PORTFOLIO_DATA`, not the table DOM; the 7 columns are unchanged).

---

## 🧾 CPA Invoice Workflow + invoice upload (BUILT — Jun 5 2026, PR #48)

Closes the loop between entering an invoice, how it was paid, and the CPA paying it.

### Maintenance Log now has 12 columns (was 8) — BACKWARD COMPATIBLE
`A Date · B LLC · C Property · D Sub · E Category · F Description · G Amount · H Entered By`
**+ new:** `I Paid By · J Paid · K Notes · L Invoice File URL`. Old 8-col rows still read
fine (the new fields come back blank/false). `getDashboardJson` maint reader now reads 12
cols and emits `paid_by, paid, notes, invoice_url`; `addMaintenanceEntry` /
`updateMaintenanceEntry` write all 12.

### Form (Add/Edit Maintenance modal)
- **Paid By** dropdown (Jun 16 2026, reworked): `Debit Card` (instant draw — Home Depot etc.) /
  `Check` (mailed, drafts ~1 wk) / `Sent to CPA`. **Defaults to blank "-- choose --"** (forces a
  conscious pick so an invoice can't silently skip the CPA list). **Why the split:** the planner's
  maintenance reserve (`upcomingMaintenance`) reserves **unpaid** invoices + **`Check`** invoices paid in the
  last ~7 days — a **Debit-card** buy draws instantly so it's already gone from the typed bank balance
  (reserving it would double-count), and **CPA-paid** invoices don't draft from the LLC account. Legacy rows
  with the old value `LLC Debit Card` render the 💳 Debit badge (treated as instant, not reserved). Table
  badge: `🧾 Check` /
  `💳 Debit` / `🧾 CPA · paid|unpaid`.
- **Paid** checkbox (defaults unpaid) — check it once the CPA actually pays.
- **Notes** free-text.
- **Invoice file** upload (image/PDF). Frontend reads it to base64 (`readFileAsPayload`) and
  posts it; Apps Script `saveInvoiceFile()` writes it to a **`Niron Maintenance Invoices`**
  Drive folder (auto-created), sets it **ANYONE_WITH_LINK / VIEW**, and stores the URL in col L.
  Shows as a 📎 in the maintenance table + CPA view. (25 MB client cap.)

### CPA view
- **🧾 CPA Invoices** button in the header (next to Run Audit) opens a modal listing invoices
  where **Paid By = Sent to CPA AND Paid = unchecked**: Date, LLC, Property, Vendor, Category,
  Description, Amount, Notes, 📎 file, + a one-click **Mark paid** (per row) and a total.
  **Export CSV** + **Print** (clean printable window) so the CPA reconciles without seeing the
  rest of the dashboard.
- **Mark paid** uses a dedicated `set_maintenance_paid` action (flips only col J) — no risk of
  clobbering other fields from stale data.
- Maintenance table got a **Pay / File** column: `💳 Debit` / `🧾 CPA · unpaid|paid` badge + 📎.

### 🚀 Going live (REQUIRED) — needs redeploy AND a NEW permission
`automation/AppsScript.gs` now uses **DriveApp** (to store invoice files), so the redeploy
will prompt for a **new Google Drive authorization** — accept it. Steps: Sheet → Extensions →
Apps Script → paste new `AppsScript.gs` → **Deploy → Manage deployments → Edit → New version →
Deploy** → approve the Drive scope when asked. Until then, uploads + the new fields won't save.
The `index.html` side goes live on merge.

> ⚙️ Invoice file sharing defaults to **ANYONE_WITH_LINK / VIEW** (so the link opens for the CPA
> from the CSV/print, matching the Noble policy-docs Drive pattern). To make invoices private,
> change the one `setSharing` line in `saveInvoiceFile`.

---

## 🏷️ Maintenance Category + Sub/Vendor dropdowns (Jun 16 2026)

**Category dropdown** (`#maint-category` in `index.html`) gained **Paint** + **Landscape**
options and a **`+ Add new category...`** option (`onCategoryChange` → `prompt`, mirrors the
sub pattern). Cleaned up the overlap at the same time: **"Flooring / Walls / Paint"** →
**"Flooring / Walls"**, and **"Yard / Irrigation"** was removed (covered by Landscape). Custom
categories are session-only (not persisted) — only the **subs** list is remembered (below).

**Subs/Vendors are now SHARED, server-side** (not per-browser). The maintenance form's
**`+ Add new sub...`** option saves the new vendor to a **`Subs` Google Sheet tab** so it shows
for everyone on every device — like all other data.
- **Apps Script (`AppsScript.gs`):** `ensureSubsTab(ss)` auto-creates + seeds the tab (base list
  Rigo/Samuel/Rolando/Tamir/Rudy/Rosalio/Melchor) on first read, like the Vacancy/Property Tax
  tabs. Cols A–C = `Sub / Vendor · Added By · Updated At`, data from row 5. Live `getDashboardJson`
  reads it → `data.subs`. `doPost` routes **`add_sub`** → `addSubEntry` (case-insensitive de-dupe,
  `logActivity`). Edit the **LAST** copies (the live `getDashboardJson` ~1741 + live `doPost` ~1125).
- **Frontend (`index.html`):** `loadCustomSubs()` (called in `openMaintModal` + `openMaintEdit`)
  injects `PORTFOLIO_DATA.subs` into the dropdown; `rememberSub(name)` POSTs `add_sub` to the
  sheet AND keeps a `localStorage 'niron_custom_subs'` fallback (so a sub added before the redeploy
  still shows that session). **Backward-safe:** if the script isn't redeployed, `data.subs` is
  undefined → falls back to localStorage, base list still works.
- 🚀 **Going live (REQUIRED):** redeploy `AppsScript.gs` (Sheet → Extensions → Apps Script → paste
  → Deploy → Manage deployments → Edit → New version → Deploy). The `Subs` tab auto-creates on the
  first load after redeploy. The `index.html` side goes live on merge; new subs just won't persist
  to the shared sheet until the redeploy.

## 🔧 Maintenance Invoices — Add / Edit / Delete (BUILT)

The **Maintenance Invoices** table on the dashboard (index.html, rendered ~line 1459) is
**fully editable in-place** — no need to open Google Sheets.

- **Add** = the floating **🔧** button (`openMaintModal` → `submitMaintenance` →
  Apps Script `add_maintenance`). Unchanged.
- **Edit** = an **✏️ button on each row**. `openMaintEdit(rowNum)` reuses the SAME maintenance
  modal in edit mode (title → "✏️ Edit Maintenance Invoice", button → "Save Changes"),
  pre-fills it from `PORTFOLIO_DATA.maintenance`, and `submitMaintenance` sends
  `action:"update_maintenance"` with the target row → `updateMaintenanceEntry` overwrites that
  exact row's 8 columns.
- **Delete** = a **🗑 button on each row**. `deleteMaint(rowNum)` confirms, then sends
  `action:"delete_maintenance"` → `deleteMaintenanceEntry` does `sh.deleteRow(row)`.

### How the row is targeted (the key wiring)
The **live** `getDashboardJson` maintenance reader (last copy, ~line 1631) now tags every
record with **`row: 5 + i`** (data starts at sheet row 5). The frontend passes that `row` back
on edit/delete so Apps Script changes the exact sheet row. Both handlers validate
`row >= 5 && row <= getLastRow()`. `setSelectValue()` (index.html) inserts a temporary
`<option>` if a legacy/freeform property or sub isn't in the dropdown, so old rows still
pre-fill correctly; llc is set directly from the record (not via `onPropertyChange`).

### ⚠️ Edit the LAST copies (duplicate-function footgun)
Apps Script runs the **last** definition of duplicated functions. The live ones are:
`doPost` (~line 1087, now routes `update_maintenance` + `delete_maintenance`),
`addMaintenanceEntry` (~line 1547, with the new `updateMaintenanceEntry` +
`deleteMaintenanceEntry` right after it), and `getDashboardJson` (~line 1563, the
maintenance reader that emits `row`). Don't add this to the earlier dead copies.

### 🚀 Going live (REQUIRED — AppsScript.gs is NOT auto-deployed)
Same as the chatbot: Sheet → **Extensions → Apps Script** → paste the new `AppsScript.gs`
(or just `doPost`, `getDashboardJson`, `updateMaintenanceEntry`, `deleteMaintenanceEntry`)
→ **Deploy → Manage deployments → Edit → New version → Deploy**. Until that redeploy, the
✏️/🗑 buttons appear but Edit/Delete will fail (the old web app doesn't know those actions and
the maintenance JSON won't carry `row`). `index.html` is served separately, so it updates on
its own once merged.

---

## 🔧 Maintenance Invoices moved to its OWN main tab (Jun 28 2026)
The **Maintenance Invoices** section moved off the Master Portfolio page into its own **6th main
tab `🔧 Maintenance`** (rightmost: Master · Noble Insurance · Property Tax · Loan Details · Property
Monitor · Maintenance). User decisions: **move it** (removed from Master) · **🔧 Add-Invoice FAB shows
on BOTH** Master and the Maintenance tab · **visuals identical**.
- **How (pure frontend, no redeploy):** new pane `#tab-maint` / `#maint-content`; the section body
  was extracted verbatim into **`renderMaintenanceSection(maintenance)`** (own month dropdown defaulting
  to current month, ⬇ Export + 🖨 Print, the edit/delete table, Total row). `renderAll` no longer
  appends it to Master `#content`; instead, after `el.innerHTML`, it does
  `document.getElementById('maint-content').innerHTML = renderMaintenanceSection(maintenance)`. Empty
  state shows "click the 🔧 button to add one."
- **FAB on both:** `switchMainTab` now shows `maint-fab` when `tab === 'master' || tab === 'maint'`
  (dist-fab/stmt-fab stay master-only). The FAB is `position:fixed` so it floats over the tab.
- **Table CSS:** extended the `#tab-master, #tab-props` table rules to also include **`#tab-maint`**
  (same scoping lesson as Property Monitor — a moved table needs its `#tab-master`-scoped CSS on the
  new pane id). `.header-month-select` / `.maint-edit-btn` / `.maint-del-btn` / `.section h2` are
  global, so they worked unchanged.
- **Wiring:** `switchMainTab` handles `'maint'` (chat tag `MAINTENANCE`, persists `?tab=maint`); the
  `?tab=` deep-link parser + URL-persist list include `maint`. Self-audit unaffected (it reads
  maintenance from `PORTFOLIO_DATA`, never the DOM table). Add/edit/delete still call the same reload →
  `renderAll` path, which now refreshes `#maint-content`.

---

## 📤 Maintenance Export — CSV + Print, grouped by LLC (Jun 24 2026)

The **Maintenance Invoices** section header now has two buttons next to its month dropdown
(pushed right via `margin-left:auto`): **`⬇ Export`** (`exportMaintCsv()`) and **`🖨 Print`**
(`printMaint()`). Purpose (user, Jun 24 2026): send Nir a **per-LLC view of maintenance spend**
so he can decide how much to distribute to each partner from each LLC, and let the user
reconcile against each LLC's **bank account** to see which invoices haven't cashed yet.
- **Scope = the Maintenance table's own month dropdown** (`MAINT_MONTH`; `''` = All months). So
  "export what you see" — pick a month to narrow it, or All months for everything. Both buttons
  alert + no-op if the current scope has zero invoices.
- **Grouped by LLC** (alphabetical), every invoice as a detail row, then **two subtotal lines per
  LLC**: `— subtotal` (all invoices) and **`— still owed (unpaid)`** (sum of rows where the
  `paid` checkbox is false — the "upcoming" number), then a **GRAND TOTAL** + **GRAND TOTAL —
  still owed (unpaid)** at the bottom.
- **Columns:** LLC · Date · Property · Vendor (sub) · Category · Description · Amount · **Paid By**
  (`maintPaidByLabel`: `Debit Card` = instant draw / `Check (mailed)` = may not have cleared /
  `Sent to CPA` = CPA pays it / `—`) · **Paid** (Yes/No from the `paid` flag) · Notes · Invoice File.
  The Paid By + Paid columns are what the user ticks against the bank to find uncashed invoices.
- Helpers: `maintExportRows()` (filter+sort by LLC then date desc), `maintGroupByLlc()`,
  `maintPaidByLabel()`, `maintScopeLabel()`. CSV is UTF-8 (em-dash labels are fine), filename
  `Niron_Maintenance_<month|all-months>_<today>.csv`. Print opens a clean B/W sheet (per-LLC
  table + subtotal + grand total, "still owed" in red), like `printCpa()`.
- **Pure frontend (`index.html`), live on merge — NO Apps Script redeploy.** Mirrors the existing
  CPA export pattern (`exportCpaCsv`/`printCpa`). Self-audit unaffected (no `#kpi-*` IDs). The
  "still owed (unpaid)" subtotal keys off the `paid` checkbox only — there is no per-invoice
  "cleared by bank" flag (that would need an Apps Script column + redeploy; not built — the user
  does the bank reconciliation manually, which is the point).

---

## 🗓️ `/monthly-distribution` skill — month-end reconcile + distribution prep (Jun 24 2026)

A project skill at **`.claude/skills/monthly-distribution/SKILL.md`** (invoke with
**`/monthly-distribution`**). Built from the Jun 2026 session where we reconciled maintenance
against the bank and worked out safe-to-distribute per LLC. Run it at the **end of every month**
for the **4 LLC accounts**. **READ-ONLY** — produces analysis + a Nir text, never writes the
sheet/dashboard.

- **Inputs the user provides:** (1) the **4 bank-statement CSVs** (`3 Divando LLC 3442` →
  Divando ÷2 · `1 Donald LLC 9364` → Donald ÷2 · `2 Yale LLC 2321` → Yale ÷2 · `4 Dorado LLC
  2189` → Dorado ÷3 +Simon); (2) the **dashboard Maintenance export CSV** (the `⬇ Export`
  button, month dropdown set to the closing month); (3) **each account's END-OF-MONTH BALANCE**
  (the chosen basis — ask if missing).
- **Step 1 — maintenance reconcile:** match each invoice to a bank line. Debit-card (`DBT CRD`/
  `DDA B/P`) by exact amount; checks (`CHECK ####`) by amount, trying **per-vendor sums** (the
  CPA cuts **one check per vendor per LLC** — e.g. Divando `CHECK 260` $2,650 = Rolando's 5 jobs).
  No match in-window = **still to clear**; a check dated before the work = prior-month. **Flag
  invoices marked `Paid` in the sheet but not yet cashed** (the gap the user wants).
- **Step 2 — safe to distribute (balance-based, user-chosen method):**
  `safe = ending_balance − cushion − maintenance_still_to_clear − upcoming_recurring_bills_not_yet_drafted
  − inter_account_owed`, clamp ≥0, then `÷2` (Dorado `÷3`).
  - **Cushions (user-chosen per-LLC):** Divando **$2,000** · Donald **$1,500** · Yale **$1,500** ·
    Dorado **$1,000**.
  - **Reserve upcoming bills** not yet drafted by the statement date — most importantly **Divando
    insurance ~$2,909.98 (~the 29th)**, which never lands in a statement cut on/before the 24th.
  - **Inter-account owed:** an unrepaid overdraft-cover `TRANSFER FROM X####` credit (e.g. Jun:
    Donald got **$3,000 from Yale X2321**) is **owed back** → subtract it. Note any account that
    overdrafted (distribute conservatively).
- **Step 3 — output:** per-LLC cleared/pending tables + a safe-to-distribute table + a short
  **copyable Nir text** (per-LLC: repairs total, still-to-clear, safe-to-split → each).
- **Splits (fixed):** Divando/Donald/Yale = Ron 50% / Nir 50%; **Dorado = Ron/Nir/Simon ⅓ each**.
- **Rounding (user pref, Jun 2026): ALWAYS round per-partner distribution amounts to clean numbers —
  round DOWN to the nearest $50** (never over-distribute). e.g. $1,133→$1,100, $1,053→$1,050, $938→$900.
  Note Dorado looks smallest per person not because it earns less (its pot is the largest of the three)
  but because it's split 3 ways (Simon) and took a big $4,156 Denver property-tax hit in June.
- The SKILL.md embeds the full **bank-line classification** rules + the **recurring-cost/draft-day
  reference table** (so it can tell what's still "upcoming") + a **June worked example** as a
  sanity check. Distributions on the statement (`BILL PAID-RONEN`=Ron, `BILL PAID-SIMON HAVIV`=Simon,
  `TRANSFER … TO X9562`=Nir) and own-account transfers are excluded from expenses, like the dashboard's
  bank importer. Keep the reference numbers in sync with `CASHPLAN_CONFIG` when fixed costs change.

**Cushion is a run-time lever (user request Jun 24 2026):** the skill applies the default per-LLC
cushions but must **state them and offer to change them every run** (the user explicitly wants to
adjust the buffer per month). It also shows the $0-cushion numbers as a quick trade-off reference.

**Co-owned-pair rule:** Yale + Donald are both Ron/Nir 50/50, so a loan between them is just the
owners' own money — they can be viewed as one combined pool for the decision. And **a tight account
that can't cover its cushion + repay a sibling from the month's cash → recommend $0 (hold), let it
rebuild** (don't force a distribution out of an account that just overdrafted).

**✅ June 2026 decision (all 4 reconciled; CORRECTED after user note):** distribute from **all four** —
**Divando $2,069 ea** (Ron/Nir) · **Donald $1,133 ea** (Ron/Nir) · **Yale $1,053 ea** (Ron/Nir) ·
**Dorado $938 ea** (Ron/Nir/Simon). Totals: **Ron $5,193 · Nir $5,193 · Simon $938** (cushion-conservative,
flow-based — recompute from ending balances when provided; Donald/Yale likely have a touch more room).
**⚠️ LESSON — the first pass WRONGLY held Donald & Yale at $0** over their overdrafts + a $3k Yale→Donald
transfer. The user corrected it: the early-month overdrafts were **timing only** (mortgages draft ~1st–8th,
Laureate owner funds land ~22nd). **Ron personally wired the bridge** ($5k into Yale + $1.5k into Donald on
the 12th) and **both repaid him on the 23rd** → the accounts are **square, not depleted**. A timing overdraft
that an owner/sibling covered and was **repaid the same cycle is NOT a reason to hold** — each account's own
income covers its bills with a surplus. (Yale also moved $3,000 to Donald on the 1st; if not yet returned,
take Yale's share from Donald — same Ron/Nir 50/50 pockets.) Skill + worked example updated to match.
**Follow-up (Divando July checks):** user then flagged ~$4,500 of repair checks drafting **first week of
July** (Rolando/Holly ~$3,000 + Rigo the painter ~$1,500) — before July income (~22nd). Since that
consumes essentially all of Divando's $4,138 June surplus, **recommended holding Divando's June
distribution (take $0), distribute from the other 3, and pay Divando's share in July** once the checks
clear + income lands (unless Divando's actual balance has slack beyond the checks — then it can spare
some). Revised totals with Divando held: **Ron $3,124 · Nir $3,124 · Simon $938.** **Principle added to
the skill: reserve known upcoming maintenance/checks due before next income — ask the user every run.**
**🔑 BALANCE-BASED re-run (user sent the 4 ending balances — Jun 24):** Divando **$12,671** · Donald
**$18,002** · Yale **$6,651** · Dorado **$9,932**. This revealed the real driver of the overdrafts —
**mortgage draft timing vs the ~22nd income deposit:** Donald CBRE drafts ~1st and Yale Lument ~8th
(both BEFORE income → most of their balance is committed to the next mortgage), Divando loans ~22nd
(same day as income → not a gap), Dorado has **no mortgage** (balance mostly free). Safe = balance −
cushion − everything due before the 22nd. Result: **Donald ~$800 → $400 ea; Dorado ceiling ~$7,500 →
up to $2,500 ea (it's the only flush/mortgage-free account) but conservative = its ~$900/ea earnings;
Divando $0 (cash committed to insurance + the ~$4,500 July checks); Yale $0 — its $6,651 balance is
LESS than its $7,337 July mortgage, so it overdraws ~the 8th regardless and needs ~$2,700 bridged.**
Recommended conservative: **Ron $1,300 · Nir $1,300 · Simon $900** (Dorado $900 ea; can pull more).
✅ **User confirmed (Jun 24): no more Dorado property tax this year** → Dorado goes to its full safe
ceiling **$2,500 ea**. **FINAL June distribution: Ron $2,900 · Nir $2,900 · Simon $2,500** (Donald $400
ea, Dorado $2,500 ea, Divando + Yale HELD). Dorado at $2,500 ea leaves it ~$1,000 (its cushion) after
insurance/util clear, then July income refills it — safe. **Skill updated: `safe` now reserves ALL
outflows before next income incl. the next-month mortgage (timing per LLC), treats `safe` as a ceiling
not a target, and flags any account whose balance < its pre-income bills as a hold + bridge.**

> 🔭 Open: the deferred **"Cleared by bank" per-invoice checkbox** (auto-track pending vs cashed
> instead of the manual statement match) was NOT built — it needs an Apps Script column + redeploy.

---

## 📄 Moss Owner Packet PDF structure

Pages:
```
Page 1: Consolidated Summary (skipped during per-property parsing)
Page 2: 1959 S Kearney Way Apt
Page 3: KEARNEY, 1959             ← header style; normalized to "1959 S Kearney Way"
Page 4: KENTON, 1443              ← normalized to "1443 S Kenton St"
Page 5: KENTON, 1453              ← normalized to "1453 S Kenton St"
```

> ⚠️ **This 5-page layout applies from the Jul 2025 statement onward.** Before then,
> the 1959 apartment was rented and paid directly to the owner by **Zelle**, so it was
> **NOT on AppFolio**: Jan–Jun 2025 packets have **4 pages / 3 properties** (no apt page;
> the house "KEARNEY, 1959" sits on page 2). A new tenant moved in with the Jul 2025
> statement and the apt joined AppFolio (summary then reads "4 properties"). The 6 missing
> Zelle months (Jan–Jun 2025, $1,850 net each) are added manually by
> `automation/add_apt_zelle.py` — they are not parseable from any PDF.

Each property page has a "Property Cash Summary" block with:
- Beginning Balance / Cash In / Cash Out / Management Fees / Owner Disbursements / Ending Cash Balance

Plus a Transactions table listing rent receipts, supplies, mgmt fee deductions, ACH owner disbursement.

**`run_moss.py` extracts**: Owner Disbursement + Management Fee per property page.
Disbursement is **already net** of mgmt fees and supplies, so we do NOT double-count
those in the dashboard's Net Cashflow formula.

---

## 🏘️ Properties (canonical names written to sheet)

### Niron (`run.py`)
Niron sheet History column "LLC":
- `Yale Townhomes, LLC`
- `5070 Donald, LLC`
- `Divando LLC`
- `Dorado LLC`

(See `LLC_MAP` in `run.py` for the AppFolio-name → internal-name mapping.)

#### Divando LLC — full per-property list (15 AppFolio pages + 3 manual)
The Divando Owner Packet PDF is **per-property** (one page each; page 1 = consolidated
summary). `run.py` currently saves only ONE consolidated Divando total — per-property
rows are a planned addition. AppFolio code → address → annual insurance:

| AppFolio code | Address | Insurance/yr |
|---|---|---|
| `13TH,15655` | 15655 E 13th Pl, Aurora CO 80011 | $3,529 |
| `13TH,15675` | 15675 E 13th Pl, Aurora CO 80011 | under 15655 policy (3-way $1,176.33/yr) |
| `43RD,14790` | 14790 E 43rd Ave, Denver CO 80239 | $2,642 |
| `BATES, 15559 LOWER` | 15559 E Bates Ave, Lower Unit, Aurora CO 80013 | shared $2,507 (1 policy w/ Upper) |
| `BATES, 15559 Upper` | 15559 E Bates Ave, A (top/upper), Aurora CO 80013 | shared $2,507 (1 policy w/ Lower) |
| `BLACK,4776` | 4776 Blackhawk Way, Denver CO 80239 | $3,320 |
| `BOSTO,1724` | 1724 Boston St, Aurora CO 80010 | $2,364 |
| `CROWN,5101A` | 5101 Crown Blvd, Unit A, Denver CO 80239 | shared $2,702 (1 policy w/ B) |
| `CROWN,5101B` | 5101 Crown Blvd, Unit B, Denver CO 80239 | shared $2,702 (1 policy w/ A) |
| `DEAR,5538` | 5538 Dearborn St, Denver CO 80239 | $2,610 |
| `HOLLY,3630` | 3630 Holly St, Denver CO 80207 | $2,693 |
| `IDALI,1310` | 1310 Idalia Ct, Aurora CO 80011 | under 15655 policy (3-way $1,176.33/yr) |
| `OAK,2332` | 2332 Oakland St, Aurora CO 80010 | $2,612 |
| `TUCSO,3225` | 3225 Tucson St, Aurora CO 80011 | $2,255 |
| `VIRG,11795` | 11795 E Virginia Dr, Aurora CO 80012 | $2,443 |

Plus 3 out-of-state manual (roll up under Divando; owned free & clear, NO
mortgage/insurance): `8222 Hare Ave`, `3899 Joest Rd`, `6580 Stockport Dr`.

**Divando fixed costs:**
- **Insurance** — authoritative source is the **Noble Insurance tab** of `index.html`
  (see below). Divando-owned policies total **$29,677/yr** ($34,630/yr full State Farm
  policy minus the 2 Dorado-owned units below).
- **Tax** — Divando is `isTaxAnnual` in `index.html`: Tax/12 shown (~$2,635/mo ≈
  $31,620/yr) but **paid lump-sum in April, NOT deducted from monthly net.**
- **Mortgage** — Divando actually carries **6 loans totaling ~$12,199.86/mo** (NOT the
  ~$2,334/mo the dashboard card shows — that figure is stale/understated). The monthly
  "AUTOMATIC TRANSFER FROM DDA" line in each loan CSV = the cash cost we subtract
  (= principal + interest). Split rule: **50/50 at building level, then 50/50 within a
  duplex** (matches insurance grouping). Per-property:
  - `13TH 0210` $2,352.90 → 15655 + 15675 E 13th Pl + 1310 Idalia (3-way **$784.30** ea)
  - `43RD BATES 0211` $1,718.36 → 14790 E 43rd **$859.18**; Bates Lower/Upper **$429.59** ea
  - `BLACK CROWN 0213` $2,014.78 → 4776 Blackhawk **$1,007.39**; Crown A/B **$503.70** ea
  - `HOLLY OAKLAND 0214` $2,107.42 → 3630 Holly + 2332 Oakland **$1,053.71** ea
  - `DEAR VIRGINIA 0212` $2,315.84 → 5538 Dearborn + 11795 Virginia **$1,157.92** ea
  - `TUCSON BOSTON 0215` $1,690.56 → 3225 Tucson + 1724 Boston **$845.28** ea
- **SBA loans** — the **$2,334/mo** the dashboard card shows as "Mortgage" is actually
  **6 SBA loan payments** ($48 + $731 + $64 + $273 + $487 + $731, drafted on the 1st of
  the month, seen on the Divando operating acct `3 Divando LLC 3442`). These are
  **general Divando business debt, NOT tied to any property** → keep as ONE LLC-level
  line; do NOT spread across the per-property table. **Total Divando monthly debt =
  $12,199.86 property mortgages + $2,334.00 SBA = $14,533.86/mo.** (The card currently
  counts only the $2,334 SBA portion and omits all property mortgages.)

#### 🛡️ Noble Insurance tab = authoritative per-property insurance source
The standalone Niron dashboard (`index.html`) has a **Noble Insurance** tab (2nd main
tab) with per-property insurance for ALL properties (Divando, Dorado, Yale, Donald).
**Read it from `index.html` before ever asking the user for insurance amounts.**
- Divando = State Farm, agent **Kevin Schult (303) 989-3847**, Dec 15 2025 → Dec 15 2026.
- Full policy = **$34,630/yr = $2,885.83/mo** across **13 SFR policies = 11 Divando-owned
  + 2 Dorado-owned**.
- The 2 Dorado-owned units sit on the Divando policy: **2397 Jamaica St** ($2,425) +
  **4641 Enid Way** ($2,528). Dorado credits **$138/mo** back to Divando. **Stop Dec 2026.**
- Two Divando AppFolio units **share one policy each**: 5101 Crown A+B ($2,702) and
  15559 Bates Lower+Upper ($2,507) → split per-unit for per-property net.
- The **15655 E 13th Pl policy ($3,529/yr) covers 3 units**: 15655 + 15675 E 13th Pl +
  1310 Idalia Ct → split 3-way = **$1,176.33/yr ($98.03/mo) each**. 15675 and Idalia
  have no separate policy line — they sit under the 15655 policy. (Resolved w/ user.)

### Moss (`run_moss.py`)
Moss sheet History column "LLC" stores **property names**, not LLC names:
- `1959 S Kearney Way`        ← mortgage $2,328.99, ins/12 $321.58
- `1959 S Kearney Way Apt`    ← no separate mortgage/insurance. Zelle-only (NOT on
  AppFolio) Jan–Jun 2025 → $1,850/mo manual via `add_apt_zelle.py`; on AppFolio from Jul 2025.
- `1443 S Kenton St`          ← mortgage $1,763.39, ins/12 $229.00
- `1453 S Kenton St`          ← mortgage $2,054.04, ins/12 $228.67
- `524 Galeras`               ← NOT on AppFolio. $2,300/mo plug May–Dec 2026.

These exact strings are referenced by the frontend's `propertyIdFromLlc()` regex in
`combined-portfolio/src/pages/MossPage.tsx` — **don't change them without updating both**.

Mortgage + insurance/12 defaults live in `PROPERTY_FIXED_COSTS` (top of `run_moss.py`).

---

## 🌴 Suncoast / MidSouth properties (manual entry, roll up under Divando)

Three out-of-state, mortgage-free, fully-owned properties are **NOT on AppFolio**
and are entered **manually each month** by the user through the dashboard:

| Property | Manager | Location |
|---|---|---|
| `8222 Hare Ave` | Suncoast Property Management | Jacksonville FL |
| `3899 Joest Rd` | Mid South Best Rentals | Memphis TN |
| `6580 Stockport Dr` | Mid South Best Rentals | Memphis TN |

**Key rules (do NOT re-ask the user):**

- All three **roll up under `Divando LLC`** on the dashboard. We deliberately did
  **NOT** create separate cards for them — they belong to Divando.
- The dashboard **sums every `Divando LLC` row** for a month into the single
  Divando card (`groupedSelected` in `index.html`). So a manual entry is added to
  the Divando totals automatically — the card's Disbursement and Net Cashflow both
  rise by the entered amount (e.g. May 2026: AppFolio $36,481.31 + Suncoast
  $1,125.40 = ~$37,606.71 shown). No separate total to maintain.
- It also appears as a normal row in the **History tab** of Google Sheets
  (LLC = `Divando LLC`, amount in Owner Disbursements, identified by the Source
  column `Manual Entry: <property>`). Search "Hare"/"Joest"/"Stockport" to find it.
- In the `History` tab they are written with **LLC = `Divando LLC`**, and the
  property name is kept in the **Source** column as `Manual Entry: <property>`
  (e.g. `Manual Entry: 8222 Hare Ave`). That Source string is how the 3 are told
  apart and how the duplicate-check works (`addStatementEntry` in `AppsScript.gs`).
- The user enters them via the dashboard's **📋 Add Monthly Statement** modal
  (`index.html`, `openStmtModal`/`submitStatement` → Apps Script `add_statement`).
- **Which dollar amount to enter:** the user enters **what actually hit the bank**
  (the deposited amount), NOT the statement's stated NOI/Owner Draw, because the
  two can differ (e.g. May 2026 Suncoast: statement said $1,205.75 but only
  $1,125.40 was deposited — an $80 gap).
- No mortgage, no insurance on these → `net_cashflow == NOI` entered.

**"Already added?" indicator:** the Add Monthly Statement modal reads
`PORTFOLIO_DATA.history` and, for the selected month, marks each property with
`✅ already added` (and disables it) or `⬜ not yet`, plus an "X of 3 entered"
line. So the user does **NOT** need to open Google Sheets to check what's done —
`refreshStmtStatus()` in `index.html`. (Server still blocks true duplicates.)

> ❓ **OPEN QUESTION (resolve from the `Moss-Investments-Niron-combined` repo):**
> Does the "Niron Master Portfolio" tab inside the **Moss combined db** read LIVE
> from the Niron sheet (`GOOGLE_SHEET_ID`)? All Niron work — entries, features,
> changes, the 4 LLCs, Suncoast, MidSouth — is done on THIS standalone Niron db
> only. The Moss combined db's Niron tab should only DISPLAY that data (read-only).
> If it reads the Niron sheet live, everything reflects automatically. If not,
> that's the gap to fix. No features or modals need to be rebuilt in the Moss db —
> it just needs to show what's here.

> 🧠 **Memory rule (STRICT):** after EVERY change — code, dashboard, numbers, user
> preferences, decisions, workflow steps, anything — update THIS file **before** opening
> the PR. The user should NEVER have to re-explain prior work. If it happened in a
> session and it's not in `CLAUDE.md`, it will be forgotten. When in doubt, write it
> down here. This includes:
> - All automation scripts (what they do, what they parse, what they write)
> - All dashboard sections (how they work, what data they read)
> - All bank-verified numbers (mortgage, insurance, fixed costs)
> - All user decisions (split rules, what to include/exclude, layout choices)
> - All user preferences (PR default, tone, formatting, copy-button rule)
> - All "going live" steps for any new feature
> - All known issues, open questions, and next steps

---

## 🔄 How a monthly run works (high-level)

1. GitHub Actions wakes up at cron time
2. Installs deps (`pip install playwright pdfplumber ...` + `playwright install chromium`)
3. Loads `APPFOLIO_COOKIES` secret → injects into Playwright context
4. Navigates to Laureate login URL
   - If cookies still valid → already logged in (no 2FA prompt)
   - If cookies expired → falls back to email+password login (will trigger 2FA on first run — that's why `keepalive.py` exists)
5. Goes to Statements page, finds the relevant card(s)
6. Downloads most recent Owner Packet (.pdf or .zip)
7. Extracts PDF → parses → builds row(s) per property
8. Calls `already_recorded()` against sheet's History tab to skip duplicates
9. Reads `Settings!B3` ("Require Approval Before Saving") → routes to:
   - `Pending Review` tab if YES → user must click 📊 Tools → Approve & Save
   - `History` tab directly if NO
10. Saves updated cookies back to `APPFOLIO_COOKIES` secret via `gliech/create-github-secret-action`
11. (Niron only) Calls Apps Script `?action=notify` to send "data ready for review" email

---

## 🧪 Common operations

### Manually trigger a Moss run
1. Go to `https://github.com/moscoron-collab/Niron-Master-Portfolio/actions`
2. Click **Monthly AppFolio Data Pull — Moss** in the left sidebar
3. Click **Run workflow** dropdown (top right) → green **Run workflow** button
4. Wait ~45-90 seconds for it to complete
5. Click into the run → check the **"Run automation"** step output

### Debug a failed run
1. Open the failed workflow run
2. Click into the **"Run automation"** step
3. Read the printed log — look for:
   - `KeyError` → missing secret
   - `Timed out waiting for cards` → AppFolio login failed (cookies expired AND 2FA blocked)
   - `Could not extract disbursement from PDF` → Laureate changed PDF format
   - `Page.fill: Timeout ... waiting for input[name='user[email]']` → **valid cookies caused a
     client-side redirect off the login page before `fill()` ran.** FIXED (PR #28) in
     `run_yale/donald.py` + `backfill_yale/donald.py`: `login()` now navigates to the
     **STATEMENTS** page first and only falls back to the login page if AppFolio redirects
     there. If you see this in `run.py`/`run_moss.py`/Divando, apply the same fix.
   - `WARNING: No card found for 'X'` → LLC name in `LLC_MAP` doesn't match AppFolio
4. The fix is almost always:
   - Update `LLC_MAP` (Niron) or `PROPERTY_NAME_MAP` (Moss) if AppFolio renamed something
   - Update regex in `_parse_amount` / `_find_amount` if PDF format changed
   - Re-run `keepalive.py` workflow manually if cookies died (and have user log in once to clear 2FA, then re-run keepalive)

### Locally test a Python change (without running on GitHub)
```bash
cd "C:/Users/Owner/Dropbox/PC/Desktop/Niron-Master-Portfolio"
# Set env vars in a .env file or PowerShell session
python automation/run_moss.py
```

### Backfill historical months
- Use `backfill.yml` (Niron) or `backfill_moss.yml` (Moss) workflows
- Manual trigger only — `workflow_dispatch` with `months` input

---

## 🧮 Formula written to the sheet

```
net_cashflow = disbursement − mortgage − tax_mo − ins_mo − maintenance
```

For Moss:
- `disbursement` = parsed from PDF (already net of mgmt fees and supplies)
- `mortgage` = `PROPERTY_FIXED_COSTS[property]["mortgage"]`
- `tax_mo` = 0 (escrow)
- `ins_mo` = `PROPERTY_FIXED_COSTS[property]["ins_mo"]`
- `maintenance` = 0 (do NOT add supplies — already deducted by Laureate)

For Niron: same formula but values come from `Settings` tab (`get_fixed_costs`) and maintenance comes from `Maintenance Log` tab (`get_maintenance`).

---

## ⛔ Don't re-ask the user

- Where the dashboard frontend lives → `combined-portfolio` repo, see that CLAUDE.md
- Who manages the properties → Laureate, Ltd. (both Niron and Moss)
- Whether AppFolio 2FA can be auto-solved → No; `keepalive.py` prevents it by refreshing cookies before they expire
- The 5 Moss property names and their costs → Listed above
- Whether to add the Cabo plug → Yes, already wired in `run_moss.py` for May-Dec 2026
- That Moss disbursements are net of mgmt fees + supplies → Yes, established
- Whether to use the same `APPFOLIO_COOKIES` secret for both Niron and Moss → Yes, single account

---

## 💬 Chatbot ("Ask Claude") — how it works

The floating **💬** button in the dashboard opens a chat panel (bottom-right). It calls
`AppsScript.gs → handleChatWithHistory()`, which builds a context via
`buildPortfolioContext()`, appends the embedded `dashboardKnowledge()` block + the Noble
Insurance text (`extractNobleContext()` from the frontend), and sends it all as a
**prompt-cached** system prompt + full conversation history to the Claude API
(`claude-sonnet-4-6`, `max_tokens: 4096`).

### ⚠️ DUPLICATE-FUNCTION FOOTGUN — edit the LAST copy
`AppsScript.gs` has **3** `buildPortfolioContext()` defs (~lines 715, 892, 1220) and a
dead `handleChatRequest()` (older single-shot handler, haiku). **Apps Script runs the
LAST `buildPortfolioContext` (~line 1220), which returns a formatted TEXT string `ctx`.**
The other two are dead. **PR #35's bug:** it added the Property Detail read to the MIDDLE
(dead) copy (line ~892, returns JSON) — so the chatbot never actually received any
per-unit data, and "highest income for Crown?" fell back to LLC-level Divando totals.
**Fixed (this PR):** per-unit Property Detail is now built into the LIVE (last) copy. When
editing chat context, ALWAYS edit the **last** `buildPortfolioContext` + `handleChatWithHistory`.

### What the live context contains (4 labeled sections)
1. **PORTFOLIO** — LLC-level **History** (monthly cashflow), pre-computed **annual totals**
   (all-LLC + per-LLC), **Loans**, **Distributions**, **Maintenance Log**.
2. **PROPERTY DETAIL** (per-UNIT, from the **Property Detail** tab — Divando/Yale/Donald):
   - a **PER-UNIT SUMMARY** (highest Cash-In month + amount, total Cash-In, total
     Disbursement, latest month's status) so "highest/best/total" questions are reliable, plus
   - the **full PER-UNIT MONTHLY ROWS** (newest first: Cash In, Rent, Disburse, Mortgage,
     Ins/mo, Status) so any specific month/trend is answerable.
3. **DASHBOARD REFERENCE KNOWLEDGE** (`dashboardKnowledge()`) — embedded authoritative facts
   NOT all in the sheet: net-cashflow formula, Divando $14,533.86/mo debt ($12,199.86
   property loans + $2,334 SBA), Yale Lument $7,279.08 + Acuity $1,037.55 + SBA $225,
   Donald CBRE $13,708 + Westfield $1,210.84 + SBA $444, tax rules, manual-entry rules, and
   how every dashboard section works. **Keep these numbers in sync with `index.html` +
   CLAUDE.md when they change** (they are hardcoded, not read from a sheet).
4. **INSURANCE** — Noble Insurance tab content (injected from the frontend).

### Rules baked into the system prompt
- **"Income" for a unit = its Cash In** (matches the dashboard's Income column).
- A property name can map to **multiple units** (Crown = "5101 Crown Blvd Unit A" + "Unit B";
  Yale = 5 units; Donald = 8 units) → the model is told to **SUM the units per month** before
  comparing months when asked about a whole property.
- **NIRON only** — the model is told it has NO Moss data and must not discuss/guess Moss.

### Prompt caching (cheap follow-ups)
`system` is sent as `[{type:'text', text:..., cache_control:{type:'ephemeral'}}]`, so the
large data+knowledge block is cached and multi-turn follow-ups in the same ~5-min window are
fast and cheap. Cache invalidates when the data, Noble text, or active tab changes.

### What it CANNOT answer
- Moss data (completely separate sheet, never sent to this chatbot)
- Months with no data yet (backfill not yet run)
- Dorado per-property (no `run_dorado.py` yet — only LLC-level totals)

### Chat persistence
History is stored in `localStorage` (key `niron_chat_history_v2`) — persists across
page refreshes. "New chat" button clears it. The whole `chatHistory` array is sent each
turn, so follow-up questions keep full conversational context.

### 🚀 Going live (REQUIRED — the repo file is NOT auto-deployed)
`automation/AppsScript.gs` is only a copy. To make chatbot changes take effect:
1. Open the dashboard's Google Sheet → **Extensions → Apps Script**.
2. Replace the script with the new `automation/AppsScript.gs` contents (or paste the changed
   functions: `buildPortfolioContext` (last copy), `handleChatWithHistory`, `dashboardKnowledge`).
3. **Deploy → Manage deployments → Edit → New version → Deploy** (the web app URL stays the same).
4. Hard-refresh the dashboard and ask a per-unit question to confirm.

---

## 📝 Known limitations / future improvements

- **Maintenance for Moss**: currently always 0 in `run_moss.py`. The PDF transactions table contains Supplies entries that COULD be parsed as maintenance, but they're already netted out of the disbursement so we leave them at 0. If the user wants to track them as a separate informational column, parse the transactions table (not the summary block).
- **Cabo plug end date**: hardcoded `2026-12-01` in `CABO_PLUG_THROUGH`. User said "till end of 2026" — extend or remove when 2027 rolls around.
- **Tax/12 not parsed**: Owner Packet doesn't break out monthly tax (paid by escrow). Stays at 0.
- **No notification email for Moss yet** — `run.py` calls Apps Script notification, `run_moss.py` doesn't (since approval is set to NO in the user's Moss sheet). Add `trigger_email_notification()` if user flips to YES.

---

_If something here is wrong or outdated, update it instead of working around it._
