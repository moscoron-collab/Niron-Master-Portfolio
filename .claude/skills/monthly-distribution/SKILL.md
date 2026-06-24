---
name: monthly-distribution
description: >-
  Month-end cash reconciliation + partner-distribution prep for the 4 Niron LLCs
  (Divando, Donald, Yale, Dorado). Use at the end of each month. Takes the 4 LLC
  bank-statement CSVs + the dashboard's Maintenance export CSV + each account's
  ending balance; reconciles which repair invoices have CLEARED the bank vs are
  still PENDING, computes how much is SAFE TO DISTRIBUTE per LLC (ending balance −
  cushion − pending repairs − upcoming bills − inter-account amounts owed), splits
  it per partner, and drafts a short per-LLC text to send Nir. READ-ONLY — never
  writes to the sheet or dashboard. Trigger phrases: "month-end", "distributions",
  "what's safe to distribute", "reconcile the accounts", "prep the Nir text".
---

# Monthly Distribution Prep (Niron — 4 LLCs)

Reconcile each LLC's maintenance against its bank statement, work out what's
**safe to distribute** to the partners, and draft a short text for Nir.
**Read-only**: produce analysis + the Nir text. Never edit the Google Sheet or
dashboard. (Per CLAUDE.md the sandbox can't reach the sheet anyway.)

Splits: **Divando / Donald / Yale = Ron 50% + Nir 50%.** **Dorado = Ron + Nir +
Simon, ⅓ each** (Simon is Dorado-only).

---

## Inputs to ask the user for

1. **The 4 LLC bank-statement CSVs** for the month (columns: `Account Name,
   Processed Date, Description, Check Number, Credit or Debit, Amount`):
   - `3 Divando LLC 3442` → **Divando LLC** (÷2)
   - `1 Donald LLC 9364` → **5070 Donald, LLC** (÷2)
   - `2 Yale LLC 2321` → **Yale Townhomes, LLC** (÷2)
   - `4 Dorado LLC 2189` → **Dorado LLC** (÷3, + Simon)
2. **The dashboard's Maintenance export CSV** (the `⬇ Export` button → file
   `Niron_Maintenance_<month>_<date>.csv`, grouped by LLC, with `Paid By` + `Paid`).
   Set the dashboard's month dropdown to the month being closed before exporting.
3. **Each account's END-OF-MONTH BALANCE** (4 numbers). This is the basis for
   "safe to distribute" (user's chosen method). If the user didn't give them, **ask**.

If any of the 4 statements or balances is missing, **say so and skip that LLC**
(report it as "need statement/balance") rather than guessing.

---

## Step 1 — Reconcile maintenance (cleared vs pending), per LLC

For each LLC, take its invoices from the Maintenance export and match each one to a
line on that LLC's bank statement.

**Matching rules** (the CPA cuts **one check per vendor per LLC**):
- **Debit-card buys** — `DBT CRD …` / `DDA B/P …` lines → match an invoice whose
  `Paid By = Debit Card` by **exact amount**. The merchant on the bank line is the
  store (e.g. `SHERWIN-WILLIAMS`, `THE HOME DEPOT`), not the vendor name on the invoice.
- **Checks** — `CHECK ####` lines → match by amount. A single check usually equals
  the **sum of one vendor's `Sent to CPA` invoices** for that LLC, so **try per-vendor
  sums**, not just single invoices. (June example: Divando `CHECK 260` $2,650 = Rolando's
  5 jobs 1500+350+150+150+500; Dorado `CHECK 3286` $525 = Rolando's 175+350.)
- An invoice with **no matching bank line in the statement window** = **still to clear**.
- A `CHECK ####` dated **before** the invoices it could cover = a **prior-month** invoice
  (not in this export) — note it as "prior-month maintenance cleared this month"; it still
  reduced this month's cash.

**Output per LLC:** a small table of ✅ cleared invoices (with the matching bank line)
and 🟡 still-to-clear invoices, plus the two subtotals. **Flag loudly** any invoice the
sheet marks `Paid = Yes` that has **not** actually cleared the bank — that's the gap the
user cares about. (Exception: a `Debit Card` invoice dated in the last ~2 days of the
window may just not have posted yet — call it "posting, treat as paid" if the user says so.)

---

## Step 2 — Safe to distribute, per LLC (balance-based)

```
safe(LLC) = ending_balance(LLC)
          − cushion(LLC)
          − maintenance_still_to_clear(LLC)          # from Step 1
          − upcoming_recurring_bills_not_yet_drafted(LLC)   # see reference table
          − inter_account_amounts_owed(LLC)          # overdraft-cover transfers IN, not repaid
if safe < 0 → safe = 0   (and say the account can't distribute this month)

per_partner = safe / (3 if Dorado else 2)
```

- **cushion(LLC)** (per-LLC buffers, user-chosen): **Divando $2,000 · Donald $1,500 ·
  Yale $1,500 · Dorado $1,000.**
- **upcoming bills not yet drafted** — scan the statement for each recurring bill in the
  reference table below; if a bill is **absent** (or dated after the statement end), reserve
  its expected amount because it's still coming. Most common: **Divando insurance
  ~$2,909.98 drafts ~the 29th**, so it's not in a statement cut on/before the 24th–25th →
  reserve it. (Donald/Dorado/Yale insurance draft early, so they're usually already in.)
- **inter-account amounts owed** — if a statement shows a `TRANSFER FROM X#### …` **credit**
  that covered an overdraft (e.g. June: Donald received `$3,000` from Yale `X2321`), that LLC
  **owes it back** → subtract it. A `TRANSFER … TO X#### OVERDRAFT` **debit** means this LLC
  *lent* to a sibling (it's owed money — neutral, don't add it back as available).
- Also note (don't subtract) if the account **was overdrawn / paid overdraft fees** — that's a
  signal to distribute conservatively from it regardless of the formula.

---

## Step 3 — Output

1. **Maintenance reconciliation** — per-LLC ✅ cleared / 🟡 pending tables + the
   "marked Paid but not cashed" flag list.
2. **Safe-to-distribute table** — `LLC | ending balance | − cushion | − pending repairs |
   − upcoming bills | − owed to sibling | Safe | Ron | Nir | Simon`.
3. **The Nir text** — in a copyable code block, short and per-LLC (template below).

### Nir text template (keep it SMS-short)

```
<Month> distributions (bank-reconciled):

• Divando — $<repairs total> repairs ($<pending> still to clear). Safe to split ~$<safe> → $<each> each.

• Dorado — $<repairs total> repairs ($<pending> still to clear). Safe to split ~$<safe> → $<each> each (you/me/Simon).

• Donald — $<repairs total> repairs (<status>). <one-line note — e.g. skip / owes Yale / overdrawn>. Safe ~$<safe> → $<each> each.

• Yale — $<repairs total or "no repairs">. Safe to split ~$<safe> → $<each> each.

Heads up: <any reserved upcoming bill, e.g. Divando insurance ~$2,910 drafts ~the 29th — already held back>.
```

---

## Reference data (bank-verified — from CLAUDE.md / CASHPLAN_CONFIG)

Use these to (a) classify bank lines and (b) detect which recurring bills haven't drafted
yet. **Always prefer the actual amount on the statement** when the bill is present; use the
reference amount only to reserve a bill that is **missing** (still upcoming).

### Recurring fixed costs + typical draft day

| LLC | Mortgage | SBA | Insurance | Utilities | Other | Cushion |
|---|---|---|---|---|---|---|
| Divando | $12,199.86 — 6 `TRANSFER TO LOAN` (~15th) | $2,334.00 (1st) | State Farm **$2,909.98 (~29th)** | ~$685 (Xcel/Aurora Water/Compost/Google, ~15th) | ACE Cloud Hosting software $288.98 (~28th, Amex) | **$2,000** |
| Donald | CBRE ~$13,708 (1st) | $444.00 (1st) | Westfield $1,210.84 (~4th) | $336 **quarterly** (Jan/Apr/Jul/Oct, ~3rd) | — | **$1,500** |
| Yale | Lument $7,279.08 (~6th) | $225.00 (1st) | Acuity $1,037.55 (~25th) | $315 **quarterly** (Jan/Apr/Jul/Oct, ~15th) | — | **$1,500** |
| Dorado | **none (mortgage-free)** | none | National Indemnity $453.31 (~7th) | ~$454 **monthly** (Xcel/Denver Water/Compost, ~5th) | pays Divando $138/mo ins comp (TRANSFER, exclude) | **$1,000** |

### Bank-line classification

- **Income (credit, into the LLC):** `LAUREATE … OWNERFUNDS` (the big monthly owner deposit);
  for Divando also `SUNCOAST … WEB PMTS` (Hare) + `MID SOUTH … WEB PMTS` (Joest/Stockport).
- **Distributions — EXCLUDE from expenses, track per partner:** `BILL PAID-RONEN` = Ron ·
  `BILL PAID-SIMON HAVIV` = Simon · `TRANSFER … TO X9562` = Nir (X9562 = Nir's personal acct).
- **Inter-account transfers — EXCLUDE (zero-sum):** any `TRANSFER` involving `DDA ACCT` or an
  own account: `X3442` (Divando), `X9364` (Donald), `X2321` (Yale), `X2189` (Dorado), `X5369`,
  `X0422`. (But see Step 2 — an unrepaid overdraft-cover transfer IN is *owed back*.)
- **Mortgage:** `TRANSFER TO LOAN` / `CBRE LOAN` / `LUMENT`. **SBA:** `SBA LOAN`.
- **Insurance:** `STATE FARM` / `ACUITY` / `WESTFIELD` / `NATIONAL INDEMNITY`.
- **Property tax:** `CITY AND COUNTY` / `… TAXPYMT` / `ARAPAHOE … TAXPYMT` / `CO TAX`.
- **Utilities:** `XCEL` / `DNVRWTR` / `DENVER WATER` / `… COMPOST` / `CITY OF AURORA` / `GOOGLE`.
- **Maintenance (repairs):** `CHECK ####` / `DBT CRD` / `DDA B/P` / `AMEX` / `BILL PAID-<other>`.
- **Bank fees:** `OVERDRAFT FEE` / `CONTINUOUS OVERDRAFT FEE`.
- Anything unmatched → call it "other" and list it so nothing is silently dropped.

---

## Worked example — June 2026 (sanity check for the method)

With the per-LLC cushions, reserving Divando's ~29th insurance, treating the Divando
$744.47 debit-card buy as paid, and netting Donald's $3,000 owed to Yale:

- **Divando** — repairs $7,444.33 ($6,010 cleared incl. the $744.47; $1,434.47 pending =
  furnace $660 + garage $774). Reserved insurance $2,909.98. (Flow-based safe ≈ **$6,427 →
  $3,213 each**; redo from the ending balance when provided.)
- **Dorado** — repairs $875 ($525 cleared via `CHECK 3286`; $350 Walter pending). Safe ≈
  **$3,813 → $1,271 each** (÷3).
- **Donald** — repairs $3,070 all cleared (`CHECK 7256` $2,950 + `CHECK 7257` $120), **but
  overdrawn early month + owes Yale $3,000** → only ~$766 free → **recommend skip/minimal**.
- **Yale** — no repairs; statement still needed for its number.

> The June figures above were computed **flow-based** (income − costs) because ending
> balances weren't provided yet. The skill's chosen method is **ending-balance based** — when
> the user gives the 4 balances, recompute with the Step-2 formula and prefer those numbers.

## Guardrails

- **Read-only.** Never POST to the dashboard / Apps Script, never edit the sheet.
- Reconcile by **exact amounts**; show every match so the user can audit it.
- Surface, don't hide: missing statements/balances, accounts that overdrafted, invoices
  marked Paid but not cashed, and any unmatched bank line.
- Splits are fixed: Dorado ÷3 (Ron/Nir/Simon), the other three ÷2 (Ron/Nir).
