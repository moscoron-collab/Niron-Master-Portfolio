# CLAUDE.md — Niron Master Portfolio (Python automation + standalone dashboard)

> Read this BEFORE asking the user about repo structure, automation, or AppFolio.
> See also: `combined-portfolio/CLAUDE.md` for the React dashboard side.

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

## 📄 Moss Owner Packet PDF structure

Pages:
```
Page 1: Consolidated Summary (skipped during per-property parsing)
Page 2: 1959 S Kearney Way Apt
Page 3: KEARNEY, 1959             ← header style; normalized to "1959 S Kearney Way"
Page 4: KENTON, 1443              ← normalized to "1443 S Kenton St"
Page 5: KENTON, 1453              ← normalized to "1453 S Kenton St"
```

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

### Moss (`run_moss.py`)
Moss sheet History column "LLC" stores **property names**, not LLC names:
- `1959 S Kearney Way`        ← mortgage $2,328.99, ins/12 $321.58
- `1959 S Kearney Way Apt`    ← no separate mortgage/insurance (shared with main)
- `1443 S Kenton St`          ← mortgage $1,763.39, ins/12 $229.00
- `1453 S Kenton St`          ← mortgage $2,054.04, ins/12 $228.67
- `524 Galeras`               ← NOT on AppFolio. $2,300/mo plug May–Dec 2026.

These exact strings are referenced by the frontend's `propertyIdFromLlc()` regex in
`combined-portfolio/src/pages/MossPage.tsx` — **don't change them without updating both**.

Mortgage + insurance/12 defaults live in `PROPERTY_FIXED_COSTS` (top of `run_moss.py`).

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
