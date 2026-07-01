---
name: monthly-distribution
description: >-
  Month-end cash reconciliation + partner-distribution prep for the 4 Niron LLCs
  (Divando, Donald, Yale, Dorado). Use at the end of each month. Takes the 4 LLC
  bank-statement CSVs + the dashboard's Maintenance export CSV + each account's
  ending balance; reconciles which repair invoices have CLEARED the bank vs are
  still PENDING, computes how much is SAFE TO DISTRIBUTE per LLC (ending balance −
  cushion − pending repairs − upcoming bills − inter-account amounts owed), splits
  it per partner, drafts a short per-LLC text, and (once Ron approves) creates a
  Gmail DRAFT to Nir (cc Ron) so Nir can execute the distributions. READ-ONLY on the
  sheet/dashboard — the only write is a Gmail draft, never auto-sent. Trigger phrases:
  "month-end", "distributions", "what's safe to distribute", "reconcile the accounts",
  "prep the Nir text".
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
          − outflows_before_next_income(LLC)   # EVERYTHING that drafts before the ~22nd
                                                # deposit: next-month mortgage/SBA/insurance/
                                                # utilities that hit pre-22nd + pending &
                                                # upcoming repair checks. SEE TIMING NOTE.
          − inter_account_amounts_owed(LLC)     # overdraft-cover transfers IN, not repaid
if safe < 0 → safe = 0   (account is below its working balance → HOLD; may need a bridge)

per_partner = safe / (3 if Dorado else 2)
# THEN round each per-partner amount DOWN to the nearest $50 (user pref: clean
# round numbers, and rounding down never over-distributes). e.g. 1,133→1,100,
# 1,053→1,050, 938→900. Show the rounded figure as the headline; keep the exact
# one only if the user asks.
```

- **cushion(LLC)** (per-LLC buffers, user-chosen): **Divando $2,000 · Donald $1,500 ·
  Yale $1,500 · Dorado $1,000.** These are the defaults — **at run time, state the cushion
  you're applying per LLC and explicitly offer to change it** before finalizing (the user
  wants this lever every month). Also show what the numbers become at $0 cushion as a quick
  reference so they can see the trade-off.
- **outflows before next income (THE BIG ONE — this is what causes the overdrafts).** Reserve
  **everything that will draft before the next Laureate deposit (~the 22nd)** — and that INCLUDES
  **next month's mortgage/SBA/insurance/utilities if they draft before the 22nd**, not just this
  month's leftovers. The money is committed even though next month's income will replace it.
  ⏱️ **Mortgage draft timing per LLC (from the statements) is the crux:**
  - **Donald** CBRE drafts **~the 1st**, **Yale** Lument **~the 8th** → both hit **well before** the
    22nd income → **reserve the FULL mortgage** (this is why they overdraft).
  - **Divando** loans draft **~the 22nd = same day as income** → **do NOT reserve** the mortgage.
  - **Dorado** has **no mortgage** → almost nothing to reserve → its balance is mostly free.
  - SBA all ~1st (reserve). Insurance: Divando ~29th, Donald ~4th, Dorado ~7th all draft before the
    22nd (reserve); **Yale Acuity ~25th drafts AFTER the 22nd** (don't reserve). Utilities: reserve if
    the LLC's draft day is before the 22nd (quarterly ones only in Jan/Apr/Jul/Oct).
- **Balance < pre-income outflows ⇒ the account WILL overdraft no matter what → distribute $0, and
  flag it needs a bridge / time to rebuild a working balance.** (June: Yale's $6,651 balance was LESS
  than its $7,337 July mortgage → it overdraws ~the 8th regardless; hold it and pre-fund/bridge ~$2.7k.)
- **`safe` is a CEILING, not a target.** It's the MOST you can take without overdrafting before next
  income. You can take less (just the month's earnings) and let cash build. A mortgage-free account
  that has accumulated cash (e.g. Dorado at ~$9.9k) shows a high ceiling — taking the full amount draws
  down its buffer, which is a choice: **confirm no big bill (esp. property tax) is due first**, and
  offer the conservative "just this month's earnings" amount alongside the max.
- **known upcoming maintenance / mailed checks** — **ASK the user each run** whether any repair
  checks are due to draft **before next month's income lands** (owner funds arrive ~the 22nd;
  checks written early month hit first). Reserve those too. A big upcoming-check batch can zero out
  an otherwise-healthy account's distributable. (June→July example: Divando had ~$4,500 of early-July
  checks — Rolando/Holly ~$3,000 + Rigo the painter ~$1,500 — which consumed essentially all of its
  $4,138 June surplus → **Divando held to ~$0 for the month, its share deferred to July**.)
- **inter-account amounts owed** — only subtract a transfer that is **still UNREPAID at month-end**.
  Many bridges net out within the cycle: an owner wire IN (`REQUESTED BY: RONEN …` credit) paid back
  the same month (`REQUESTED BY: RON …` debit) is a **wash** — exclude both, it's NOT a drain. A sibling
  `TRANSFER FROM X#### …` that hasn't been returned IS owed back → subtract it from the borrower (the
  lender gets it back, so don't penalize the lender).
- **Co-owned pair shortcut:** Yale and Donald are **both Ron/Nir 50/50**, so a loan between them is just
  the owners' own money moving — for the decision they can be viewed as one combined Ron/Nir pool
  (`combined safe = both operating nets − both cushions`, ÷2). If one of the pair is physically short
  because its cash is parked in the other, just take its share from the sibling — same pockets.
- **Overdraft ≠ hold.** If an account paid overdraft fees, **distinguish a timing overdraft from a real
  shortfall.** A timing overdraft = early-month bills (mortgage/SBA, ~1st–8th) landing before the ~22nd
  Laureate owner-funds deposit; if an owner or sibling **wired a bridge that was repaid the same cycle**,
  the account is **square, not depleted** → distribute its operating net − cushion − reserves as normal.
  **Only recommend $0 (hold)** if operating net after cushion + reserves is genuinely ≤ 0, or the account
  carries an **unrepaid** loan that will drain it. (Do NOT repeat the June miss where Donald & Yale were
  wrongly held over a timing overdraft Ron had already covered and been repaid for.)

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

• Donald — $<repairs total> repairs (<status>). Safe to split ~$<safe> → $<each> each. <only add a note here if it's genuinely held, e.g. unrepaid loan>

• <add any account being held to $0 with a one-line reason, only if truly held>


• Yale — $<repairs total or "no repairs">. Safe to split ~$<safe> → $<each> each.

Heads up: <any reserved upcoming bill, e.g. Divando insurance ~$2,910 drafts ~the 29th — already held back>.
```

---

## Step 4 — Draft the email to Nir (Gmail draft, never auto-sent)

Nir has access to all 4 accounts and **manually executes the distributions** for Ron, Nir, and
Simon, so after the numbers are settled he needs the summary. Create a **Gmail draft** with
`mcp__Gmail__create_draft` — it lands in Ron's Drafts for him to review and hit **Send** (never
auto-send).

**Do this only AFTER Ron has reviewed and approved the Step 2/3 numbers** (confirm cushions +
any held account first). Then create the draft:
- `to`: `["nir.shay@shays.com"]`
- `cc`: `["moscoron@gmail.com"]`  ← Ron keeps a copy
- `subject`: `"<Month> Niron distributions — please execute"`
- `body`: a one-line opener + the **Step 3 Nir text** (the per-LLC block), e.g. start with
  `Hi Nir — here are this month's distributions to run (you handle Ron / Nir / Simon):`

After creating it, tell Ron: **"Draft is in your Gmail Drafts — review and hit Send."** Report the
draft ID. If the Gmail connector isn't authorized/available, say so and just output the text for
Ron to send manually — don't block the rest of the analysis on it.

⚠️ The `to`/`cc` fields need **plain email addresses only** (no "Name <email>" form). Do not put
account numbers, balances of other partners, or anything Nir shouldn't see beyond the distribution
figures in the email.

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

## Worked example — June 2026 (the actual decision; sanity check for the method)

All 4 accounts ran tight (mortgages/SBA draft ~1st–8th; Laureate owner funds land ~22nd →
early-month overdrafts), but the overdrafts were **timing only**: Ron wired bridges and was
**repaid the 23rd**, so all four are square. Cushions applied, Divando insurance (~29th) +
software (~28th) reserved, the Divando $744.47 debit-card buy treated as paid. **Decision:
distribute from all four.**

| LLC | Calc (flow-based, cushion on) | Safe | Each |
|---|---|---|---|
| **Divando** | 34,475 in − 12,200 mort − 2,334 SBA − 2,534 tax − 626 util − 7,444 repairs − 2,910 ins(res) − 289 software(res) − **2,000** cushion | **$4,138** | **$2,069** (Ron/Nir) |
| **Donald** | 22,218 in − 13,682 mort − 444 SBA − 1,211 ins − 45 fees − 3,070 repairs − **1,500** cushion | **$2,266** | **$1,133** (Ron/Nir) |
| **Yale** | 12,235 in − 7,337 mort − 225 SBA − 30 fees − 1,038 ins(res) − **1,500** cushion | **$2,106** | **$1,053** (Ron/Nir) |
| **Dorado** | 10,016 in − 453 ins − 4,156 tax − 268 util − 975 repairs(incl. $450 prior check) − 350 pending − **1,000** cushion | **$2,813** | **$938** (Ron/Nir/Simon) |

→ **Ron $5,193 · Nir $5,193 · Simon $938.**

Maintenance reconciliation that fed this: Divando $7,444 ($6,010 cleared incl. the $744.47
debit buy; pending = furnace $660 + garage $774); Dorado $875 ($525 cleared via `CHECK 3286` =
Rolando's two; $350 Walter pending; a $450 prior-month `CHECK 3285` also cleared); Donald
$3,070 all cleared (`CHECK 7256` $2,950 + `CHECK 7257` $120); Yale no repairs.

Inter-account in June (all washes / settled): Ron floated $5,000 into Yale + $1,500 into Donald
on the 12th and **both repaid him on the 23rd**; Yale also sent $3,000 to Donald on the 1st (if
not yet returned to Yale, take Yale's share from Donald — same owners); small overdraft-cover
loans to `X5369` ($600 Divando, $100 Yale).

> ⚠️ **Lesson:** the first pass wrongly **held Donald & Yale** ($0) over the overdrafts + the $3k.
> That was WRONG — the overdrafts were timing and Ron's bridge was already repaid, so the accounts
> are square. Never hold an account for a timing overdraft that's been covered + repaid.
> These figures are **flow-based + cushion-conservative**; with the 4 **ending balances** recompute
> exactly (Donald/Yale likely have a touch more room).

## Guardrails

- **Read-only on the data.** Never POST to the dashboard / Apps Script, never edit the sheet.
  The ONLY write is the Step 4 Gmail **draft** to Nir (cc Ron) — and only after Ron approves the
  numbers. Never auto-send it; leave it in Drafts for Ron to send.
- Reconcile by **exact amounts**; show every match so the user can audit it.
- Surface, don't hide: missing statements/balances, accounts that overdrafted, invoices
  marked Paid but not cashed, and any unmatched bank line.
- Splits are fixed: Dorado ÷3 (Ron/Nir/Simon), the other three ÷2 (Ron/Nir).
