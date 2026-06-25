# Fresh-Eyes Review — 11-Selector Trading Programme Operating Document

Reviewed: the as-implemented doc dated 2026-06-09 (Drive file
`1-NscDgsi9ThKtqSjQfusc47hxqiJ0nR6`). Goal: every hole, prioritized,
with concrete fixes. Honest verdict first.

**Verdict:** the governance engineering is genuinely strong — tiered
approvals with a fail-closed deny gate, append-only idempotent close
markers, verbatim board rulings, cadence gating, kill-switch, second
commit gate. Most hobby systems have none of this. The holes are not in
the plumbing; they are in the *trading content* (the rules guarantee
losses at the current hit rate and nothing forces a strategy review),
in *loop closure* (monitors that observe but demonstrably don't bite),
and in a handful of *integrity/race* details that will eventually
corrupt the ledger or double-execute. Fix priority is in that order.

---

## A. CRITICAL — the desk is structurally losing and nothing stops it

**A1. The risk/reward math requires a ~67% win rate; the desk is at
15.38%.** Stop at 2× net credit means a stopped trade loses ~1× credit;
profit target 50% wins 0.5× credit. Breakeven win rate = 2/3, before
slippage. Standard short-premium programs target 70–80% by selling
~30-delta in high IVR — so the parameters are defensible *only if
selection and timing work*. At 15.38% the book bleeds by design:
realized −$7,815 on $40,000 (−19.5%). The doc surfaces this ("we fix
the data, not the test") but no rule anywhere says *what happens when
the data says the strategy is broken*.
**Fix:** add a fund-level circuit breaker as a standing invariant in
`rules.yaml`: e.g. halt all new short-premium entries when (a) drawdown
from starting balance exceeds 15%, or (b) rolling-20-trade win rate
< 50%, until a Board-approved strategy review memo lifts the halt. A
desk that can't stop itself isn't risk-managed, however good its gates.

**A2. No post-trade analysis loop.** `learning.py` and `competency.py`
exist in the module list but the operating doc never describes a retro:
no per-trade thesis-vs-outcome post-mortem, no attribution by strategy
(CSP vs BPS vs IC), by Selector, by IVR band, by DTE at entry, no
stop-whipsaw analysis (how many stopped trades would have expired
profitable? at 2× credit on 30–45 DTE premium, transient touches are
common — this single analysis may explain most of the 15% win rate).
**Fix:** auto-generate a monthly Performance Review memo from the
Closed Positions ledger (the data is already structured for it) and
make it a standing Board agenda item. Without attribution, every rule
change is a guess.

**A3. The long-term monitoring loop demonstrably isn't biting.**
Evidence from the desk's own positions feed (snapshot 2026-06-05):
NVDA −75.9%, NKE −52.2%, UNH −24.6% — all showing `layer2: CLEAN`,
`boardFlag: NO`, and the book shows `flagged: 0`. A −75% position with
no flag means the thesis-status / 200DMA / holding_score machinery is
either not running against these rows, not writing flags, or its
output is being filed and ignored. Rule 23-D (no auto stops, Board
directive only) is a defensible philosophy — but only if the advisory
loop reliably *produces* directives to consider. Right now the doc
describes the loop (`long_term_manager`, 10:00 daily) and the data
contradicts it. **Fix:** reconcile — run `long_term_manager` against
the live Monitor tab and trace why NVDA/NKE carry no flag; add a
weekly assertion ("any position < −25% must carry a non-CLEAN thesis
status or a filed review memo") to the compliance layer.

**A4. No success criteria for the programme.** What is this desk
trying to beat? There is no benchmark (SPY total return on the same
$40k), no target Sharpe/max-drawdown, no definition of "the experiment
worked." Combined with the Section-24 No-Idleness Standard — which
manufactures pressure to always have candidates and positions — the
incentive structure pushes activity, not returns. World-class desks
treat standing down as a position. **Fix:** define programme KPIs
(vs-SPY excess return, max drawdown, win rate by track) in the doc;
soften Section 24 to require watching candidates only, never filed
proposals; report KPI deltas in the Friday weekly review.

---

## B. Correctness & integrity holes (will bite eventually)

**B1. Fund accounting contradiction.** §3 says "simulated **$40,000
fund per Selector**" (×11 ×2 tracks = $880k); §7's ledger header says
Starting $40,000 → Current $32,185 for the whole options book, and the
$2,000 position cap is described as "5%" — of the *shared* $40k. The
sheet's Size % columns compound the confusion (values near 20% that
reconcile with neither denominator). **Fix:** pick one model (the
evidence says: one $40k fund per *track*, shared across Selectors),
correct §3, and document the denominator of every percentage column on
every tab. Sizing math with an ambiguous denominator is how a 5% cap
quietly becomes 20%.

**B2. Running-balance cascade is fragile by design.** `execute_close`
appends a row with a running balance. Any manual row insert/delete/
reorder in Closed Positions silently corrupts every downstream balance,
and nothing detects it. **Fix:** make Current Balance a formula over
the P&L column (sum, not cascade), or add a daily compliance check
that recomputes the cascade and alerts on mismatch.

**B3. Idempotency registry is destroyed by archiving.**
`handled_keys()` builds the [VEGA-HANDLED] registry *from the live
doc*, and the archive cron moves resolved blocks out after >1 week.
After archiving, a key vanishes from the registry — so a re-parse of
any item with a recurring key (`ticker + context`; tickers recur
constantly) can re-route and double-execute. The AG close marker
limits the blast radius for closes, but entries have no equivalent
row-level guard described. **Fix:** persist handled keys to a state
file (like `board_cadence_state.json`) that archiving cannot touch,
and include the ISO week or memo date in the key.

**B4. Concurrent writers, no locking.** The Board doc is written by
`escalate()` (webhook), `board-response` (Vega), the archive cron, and
Sir's manual edits; the sheet by crons, skills, and GOOGLEFINANCE
recalcs. No ETag/read-verify-write or single-writer queue is
described anywhere. Google Docs API appends during a manual edit can
interleave mid-block — which then breaks `board_reader`'s anchor
parsing. **Fix:** route all programmatic doc writes through one
serialized writer (n8n queue), and have `board_reader` checksum each
parsed block and quarantine malformed ones instead of classifying
them.

**B5. Archive-window contradiction (doc says 30 days, cron says
>1 week)** is flagged in the doc but unresolved. Resolve it — B3 makes
this window load-bearing, not cosmetic.

**B6. `desk.py` docstring still says REPORT-ONLY while the desk is
ARMED.** The doc itself admits this. A future maintainer (or a future
LLM session — likelier) will read the docstring and trust it. Fix the
docstring; docs that contradict live behavior in a *safety-relevant
direction* are worse than no docs.

**B7. DESK_COMMIT coverage is unclear by the doc's own admission**
("it is *not* read inside desk.py itself"). So the second commit gate
protects the two board crons but *not* Vega-invoked skill paths while
armed. Produce a one-page write-path × gate matrix: for each real
write (entry, close, trim, board append, mark-handled, drive copy),
which of {approval tier, armed mode, DESK_COMMIT, AH/AI, read-back,
L3 confirmation} actually applies. The doc gestures at this in §7/§8
but never lays the matrix flat — and the matrix is the security model.

---

## C. Trading-design holes (beyond A)

**C1. Vol gate layers 2–3 are unfalsifiable.** Layer 1 has a number
(≥3 vol points); Layer 2 "skew + term structure" and Layer 3 "macro
regime" have no stated thresholds. If they're LLM judgment calls,
they're non-reproducible and will drift run to run. Also define the
Layer-1 metric precisely: the companion orientation doc describes Vol
Edge as "IVR at Entry minus 20-day historical vol" — IV *Rank* (0–100
percentile) minus an HV *level* (annualized %) is mathematically
incoherent. The honest metric is IV minus realized vol, in vol points.
**Fix:** numeric criteria per layer, logged with every entry, so
post-trade analysis (A2) can test whether the gates carry alpha.

**C2. No standing earnings/event rule.** PANW got an ad-hoc
post-earnings gate; nothing prevents the next short-premium entry from
sitting across an earnings print. Standard desk rule: no short premium
through earnings within the DTE window; mandatory check of the
earnings calendar at proposal time. Same for ex-dividend dates on CSPs
(early-assignment risk) — VICI's dividend-cut clause exists; generalize
it.

**C3. Stop checking is once daily at 09:30 plus a noon n8n pass.**
Overnight gaps blow through stops (CRWD −$1,200 looks like exactly
this). For a paper desk that wants institutional fidelity, either
(a) accept gap risk explicitly in the rules ("stops are
next-check-after-breach, gaps included") so P&L expectations are
honest, or (b) check more frequently intraday. Also document fill
simulation: paper fills at the stop trigger price with zero slippage
flatter results — options spreads are wide; add a slippage haircut
(e.g. fill at trigger ± half the quoted spread).

**C4. No portfolio-level risk aggregation.** Caps exist per position
and per Selector, plus the AI-cluster cap — but nothing aggregates
net delta/vega across the 12 possible short-premium positions or
stress-tests the book against a −5% SPY day. Three CSPs in correlated
names is one trade wearing three hats. **Fix:** a nightly portfolio
risk line in the Morning Brief: total notional at risk, net delta,
worst-case loss if every stop gaps 2×.

**C5. Approval-to-activation drift.** Approvals live 60 days (23-A),
entries target 30–45 DTE, and activation can wait for Monday's cron.
An approval based on IVR 35 can activate weeks later at IVR 18. The
read-back covers *price* bands; add IVR/vol-edge revalidation at
activation time (auto-return to pipeline if the edge is gone).

---

## D. Ops, security, resilience

**D1. Unauthenticated LAN webhooks can write to the Board doc.**
`savant-desk-escalate` performs the Board File Write half; anything on
the LAN can POST to it. The provenance guard covers *content* sources,
not *callers*. **Fix:** shared-secret header on every n8n webhook the
desk honors, validated in the workflow.

**D2. No dead-man switch on the cron heartbeats.** The estate has
already had silent failures (the tracker records a memory-bridge stall
with 361 silent errors, and 9 Google-auth workflows silently dead
after an env wipe). `.status` files exist — nothing watches them.
**Fix:** one n8n workflow: if any `<job>.status` is older than its
expected cadence, page. This converts every future silent failure into
a loud one. Highest ops ROI in this review.

**D3. No restore runbook.** Daily backup exists (23:30 Drive copy);
restoring it is undocumented. Write the 10-line runbook: which file,
how to verify integrity (B2's recompute), how to re-point, how to
reconcile trades executed since backup. Do one restore drill.

**D4. No kill-switch / shadow-mode drill.** The kill-switch is
documented (delete `policy/.armed`) but apparently never exercised,
and armed mode was *discovered* during doc-writing rather than
surfaced. **Fix:** (a) show effective mode (armed/shadow) in the
Morning Brief and on the SAVANT dashboard every day; (b) alert on any
mode *change*; (c) give `.armed` an expiry — re-arm monthly by
explicit choice, so armed is never a forgotten default. Quarterly:
flip to shadow, verify writes actually preview, flip back.

**D5. Market-calendar blindness.** Crons run weekdays regardless of
exchange holidays — monitors will read stale Friday data on a holiday
Monday and may act on it. Gate the market-hours jobs on an exchange
calendar.

**D6. Data-feed fragility.** Position Monitor mark-to-market rides
GOOGLEFINANCE (delayed, returns #N/A under load — which poisons P&L%
and the dashboard); Alpha Vantage free tier is heavily rate-limited
for 11 sectors' worth of IVR pulls. Define staleness detection
(timestamp column + compliance check) and the fail-mode: **missing
IVR must fail-closed for entries** (no data, no trade), never default
to pass.

**D7. Cross-turn provenance laundering through the pipeline.** The
known gap in the injection pipeline ("cross-turn hardening pending")
maps exactly onto the desk: poisoned web content → scout writes a
Watching row (GREEN write, armed) → days later the pipeline files a
proposal built on that row → Board approves text it cannot verify.
**Fix:** carry a provenance field on Watching/Analysis rows; proposals
must cite primary sources; the board memo template gets a "data
provenance" line so Sir can see what the thesis stands on.

---

## E. Document-quality fixes (the doc itself)

1. **Add the write-path × gate matrix** (B7) — one table, this is the
   doc's biggest single missing artifact.
2. **Add a lifecycle diagram** — §4 is excellent prose begging to be
   one flowchart (scout → pipeline → board → router → gates →
   activation → monitor → close → free-selector loop).
3. **Add an incident-response section** — first 30 minutes for: ledger
   corruption, double-execution, runaway armed writes, Cerebro down.
   Today the doc explains how everything works and nothing about what
   to do when it doesn't.
4. **Fix the contradictions in place:** fund-per-Selector vs shared
   fund (B1); 30-day vs 1-week archive (B5); REPORT-ONLY docstring
   note (B6); "Iron Condors in scope" vs strategy lists that omit them.
5. **Version the doc** — it claims to be the single source of truth
   but has no version number, change log, or review cadence. Add a
   header block (version, date, author of change) and a standing
   monthly review cron that diffs doc claims against live state — this
   session alone found three places where reality had moved.
6. **Glossary** — AH/AI, AG, 23-A/B/D/F, 22-B/C, BD-01, S14/S18,
   Option A. The rule-number system is fine for you; the glossary makes
   the doc survivable for any other reader (including future sessions).

---

## Top 10, in order

1. Fund-level circuit breaker (A1) — the desk must be able to halt
   itself.
2. Dead-man switch on cron heartbeats (D2) — cheapest, biggest ops win.
3. Reconcile the long-term flag pipeline against NVDA/NKE (A3) — the
   loop is provably not closing.
4. Monthly performance-attribution memo from the ledger (A2),
   including stop-whipsaw analysis of every stopped trade.
5. Persist [VEGA-HANDLED] keys outside the doc (B3) — double-execution
   risk.
6. Fix fund-accounting language + percentage denominators (B1).
7. Write-path × gate matrix in the doc (B7) + fix desk.py docstring
   (B6).
8. Mode visibility + .armed expiry + quarterly kill-switch drill (D4).
9. Webhook auth (D1) and balance-recompute integrity check (B2).
10. Standing earnings rule + numeric vol-gate criteria + IVR
    revalidation at activation (C1/C2/C5).

Everything in sections A–C changes what the programme *learns*;
everything in B/D changes whether you can *trust* what it records.
World-class is when both are true at once.
