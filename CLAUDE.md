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
- **Expected steady state:** the chip sits at amber (not green) only because of the 2 insurance
  override-vs-sheet drifts (Divando + Yale); those clear when insurance moves into the sheet
  (#11). This is correct behaviour, not a bug.
- Verified with a synthetic-DOM harness: 22 pass / 0 fail / 3 expected warns on correct data;
  catches an injected wrong KPI as a FAIL.

> Self-audit is pure frontend (`index.html`) — no Apps Script change, goes live on merge.

---

## 🩺 Operational Health tiles (Jun 5 2026, PR #46)

A second row of 4 tiles sits **just below the top KPI row** in `renderAll` (mirrors the
health-check row the user built on the Moss combined db's Niron tab). Same `summary-card`
theme; they react to the month dropdown like everything else. Pure frontend.
- **Occupancy** (`kpi-occ`) — occupied/total units for the selected month, from
  `buildPropertyRecords` filtered to `source !== 'Manual'` (the 3 out-of-state manual entries
  have no real vacancy signal; **Dorado has no per-unit data so it is not in the denominator**).
  Color: green 100, gold ≥90, red <90. Sublabel shows `X/Y units · Month`.
- **Vacant Units** — count + the vacant unit name(s) (e.g. `2993 W Yale Ave`). Gold if >0.
- **Repairs · This Month** (`kpi-rep-month`, red) — sum + count of Maintenance-log invoices for
  the selected month. Verified = `$11,615.00 / 4` for May 2026.
- **Repairs · YTD** (`kpi-rep-ytd`) — sum + count for Jan→selected-month of the year.
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
much each has taken out, YTD and lifetime.
- 4 tiles: **Lifetime You** (`kpi-life-you`), **Lifetime Nir** (`kpi-life-nir`),
  **Lifetime Total** (`kpi-life-total`), and a dual **YTD You / YTD Nir** tile.
- A **per-year table** (Year | You | Nir | Total) with an "All time" total row — handy at tax time.
- Self-audit recomputes the 3 lifetime tiles.

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

### ✅ BUILT — Bank-CSV importer + "True Cash — Bank-Verified" section (Jun 7 2026)
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
**derived** (`taxStatus` in `index.html`): Escrow (paid_by contains "escrow") · Paid (paid ≥ due) ·
Partial (0 < paid < due) · Outstanding (paid 0). **Outstanding $ excludes escrow** (lender pays).
Validated against the Excel: Divando outstanding = Crown `$1,328.82` + 15655 13th `$2,459.00` =
**`$3,787.82`**; Dorado = 41st `$2,944.56` + Enid `$1,087.20` = **`$4,031.76`** (matches the
sheet's "2026 3/25 due Dorado 4031.76" line). Sold 2116 4th Ave kept as a `[SOLD]` $0 row.

### Dashboard (`index.html`, pure frontend)
`renderTaxSection()` (called from `initialRender` + on `switchMainTab('tax')`) renders into
`#tax-content`: an outstanding banner (yellow $ owed, split per LLC), a 3-tile KPI strip (Tax Due ·
Paid · Outstanding), then a table grouped by LLC (Divando → Dorado → Donald/Yale escrow) with
Property · County · Parcel · Due · Paid · Balance · Status badge · Paid Date · Prior yrs chip ·
💳 Pay link · ✏️ edit / 🗑 delete. Edit/Add uses the **`tax-modal`** (`openTaxModal`/`submitTax`/
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
  page (`…/Treasury/Property-Taxes/Pay-Property-Taxes`, user-confirmed) with a secondary
  `TAX_COUNTY_ALT.denver` "↳ Make a Payment" line (`…/Government/Make-a-Payment`), Arapahoe
  `arapahoeco.gov/.../treasurer/tax_search.php`, Adams `adcotax.com/.../loginPOST.jsp?guest=true` (guest
  search, skips login). Duval/Memphis deep links still work for a human, so they're kept.
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
- **Parcel chip now shows a county "kind" label** (`TAX_COUNTY_KIND`): Denver `Schedule`, Arapahoe
  `PIN`, Adams `Acct`, Duval/Memphis `Parcel` — because Arapahoe has a **PIN and a different AIN**, so
  the user must know which number to enter. The label is display-only; the click still copies just the
  number. 15655 E 13th's value `031319692` is the **PIN** (the AIN `197505203015` is a different number).

> ⚠️ **Cannot write the live sheet from the agent box** — the Apps Script `/exec` endpoint is "Host not
> in allowlist" (sandbox blocks `script.google.com`), and the county sites block scraping. So dollar-
> amount / paid-status corrections must be done by the user via the ✏️ Edit modal (or directly in the
> sheet). User-reported current amounts owed (Jun 8 2026, to be entered via ✏️): 15655 E 13th **$2,509.18**,
> Dorado 1460 W 41st **$3,035.64**, Dorado 4641 Enid **$1,120.81**; and **Crown** must read **Outstanding**
> (set Amount Paid 0 + clear Paid Date) — it was showing fully paid.

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
- **Paid By** dropdown: `LLC Debit Card` / `Sent to CPA`. **Defaults to blank "-- choose --"**
  (user picked option A — forces a conscious pick so an invoice can't silently skip the CPA list).
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
