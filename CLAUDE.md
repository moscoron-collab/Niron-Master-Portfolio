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
- **PR default (do NOT re-ask):** when work is committed/pushed and ready, **open the pull request automatically** (`mcp__github__create_pull_request`, base `main`). The user has standing approval — never ask "want me to open the PR?". Just open it and give the link.

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
- **AppsScript.gs** `getDashboardJson()` now serves `data.property_detail` from that tab.
  ⚠️ There are 3 identical `getDashboardJson()` defs — Apps Script uses the LAST one (the
  one with the richer `maintenance` fields + `properties` + `property_detail`). Edit that one.
- **index.html** renders a "Divando — Per-Property Monitor" section between Recent
  Maintenance and History: a Chart.js chart + a table (Property | Status | Income |
  Disbursement | Repairs | Net | YTD Net | Occ %).
  - **3 dropdowns**: Chart style (`PD_CHART` bars|lines) · **View** · Metric (`PD_METRIC`
    net|disbursement|cash_in|occupancy).
  - **View dropdown is merged** (`pdSetView`, value `r:N` for a range or `m:YYYY-MM-DD` for
    a single month): one `<select>` with an "Range" optgroup (3/6/9/12/All → `PD_RANGE`) and
    a "Single month" optgroup (every available month → `PD_MONTH`, sets `PD_RANGE=1`). Only
    ONE is ever selected so it's unambiguous. The old separate month-picker was removed.
  - A **plain-English caption** under the title states the current view, e.g.
    "Showing **Net Cashflow** · **Single month: Apr 2026** · Bars view".
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
| `BATES,15559 LOWER` | 15559 E Bates Ave, Lower, Aurora CO 80013 | shared $2,507 (1 policy w/ Upper) |
| `BATES,15559 UPPER` | 15559 E Bates Ave, Upper/A, Aurora CO 80013 | shared $2,507 (1 policy w/ Lower) |
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

## 📝 Known limitations / future improvements

- **Maintenance for Moss**: currently always 0 in `run_moss.py`. The PDF transactions table contains Supplies entries that COULD be parsed as maintenance, but they're already netted out of the disbursement so we leave them at 0. If the user wants to track them as a separate informational column, parse the transactions table (not the summary block).
- **Cabo plug end date**: hardcoded `2026-12-01` in `CABO_PLUG_THROUGH`. User said "till end of 2026" — extend or remove when 2027 rolls around.
- **Tax/12 not parsed**: Owner Packet doesn't break out monthly tax (paid by escrow). Stays at 0.
- **No notification email for Moss yet** — `run.py` calls Apps Script notification, `run_moss.py` doesn't (since approval is set to NO in the user's Moss sheet). Add `trigger_email_notification()` if user flips to YES.

---

_If something here is wrong or outdated, update it instead of working around it._
