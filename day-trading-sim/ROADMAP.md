# Roadmap & Agent Handoff

Context document for any future session/agent continuing this project.
Read `README.md` first for what exists; this file is what to build next
and the rules to build it by.

## Picking this up from another machine (e.g. desktop Claude Code)

```
git fetch origin claude/day-trading-sim-1zir7q
git checkout claude/day-trading-sim-1zir7q
```

Then tell the agent: "continue the day trading sim — read
day-trading-sim/ROADMAP.md". Everything needed is in this directory;
no prior conversation context is required.

## Current state (v3)

- `sim.py` (v1): synthetic minute-bar market (regime-switching momentum,
  vol clustering, intraday U-shape, gaps, jumps) + EMA(6/24) momentum
  bot (`SignalTracker` holds the shared signal) with vol-scaled trailing
  stops, 1% risk/trade, 2x max leverage, flat by close. Costs
  ~1.5bp/side on every fill. Bot positive 20/20 worlds (mean +108%/yr),
  coin-flip ablation -63%.
- `options_sim.py` (v2): Black-Scholes pricer, IV surface tracking the
  market vol state with put skew + 15% variance risk premium, option
  spreads on every fill. Regime-mapped bot: long ~5-day ATM calls/puts
  in trends; short same-day ATM straddles (delta-hedged, only when IV
  is rich) in chop. +77% mean, 20/20 worlds, both legs independently
  positive; direction-randomized ablation -59%.
- `validate.py` (v3): walk-forward optimization (train days 1-125 /
  test 126-250: +102% -> +94%, tuned beats default 20/20), per-world
  t-stats (significant 17/20), pooled bootstrap CI on daily returns,
  3x3 parameter robustness surface (smooth plateau), cost stress
  (1x: +108%, 2x: -68%, 4x: wiped out).

## Non-negotiable evaluation rules

Any new strategy or market feature must keep these, or results are noise:

1. Report the full distribution over many independent seeds — never a
   single run.
2. Always include a signal-ablated baseline (same mechanics, randomized
   decision) so cost drag and luck are separated from edge.
3. All fills pay spread + commission + slippage.
4. If parameters are tuned, tune on one span of days and report results
   on a held-out span (walk-forward). v1 does not do this yet — it is
   the highest-value improvement.
5. Keep the honest caveat in README: synthetic momentum is the source
   of the edge; this is not investment advice.

## Roadmap (rough priority order)

1. ~~**Walk-forward optimization**~~ — DONE in `validate.py`. Possible
   extension: rolling (anchored) windows instead of a single split, and
   widen the grid — the optimizer picked the grid edge (z=1.4, stop=4),
   so the true optimum may lie beyond it.
2. ~~**Options layer**~~ — DONE in `options_sim.py`. Possible
   extensions: iron condors / verticals (defined-risk premium selling),
   vega/gamma position limits, term-structure trades, pin risk near
   expiry, early assignment for American-style.
3. **Multi-instrument portfolio** — 3-5 correlated symbols, shared
   regime factor + idiosyncratic regimes, portfolio-level risk caps.
4. **Execution realism** — limit orders with fill probability vs
   crossing the spread; partial fills.
5. **Browser visualization** — this repo is a single-file-HTML project;
   a self-contained `sim.html` replaying a day with trades, equity, and
   greeks would match the house style. Port the generator to JS or
   pre-export JSON from Python.
6. **Real data adapter** — same bot interface fed from CSV/API minute
   bars, for environments whose network policy allows a data host.

## Practical notes for the next agent

- Branch: `claude/day-trading-sim-1zir7q`. Develop here unless told
  otherwise.
- Run: `pip install numpy matplotlib && python3 day-trading-sim/sim.py`
  (~20s). Regenerates `results.png`.
- Update README results table and `results.png` whenever behavior
  changes; keep this file's "Current state" section in sync.
- Known v1 pitfalls already hit once: don't make synthetic trends too
  strong (drift/noise per minute should stay well under ~0.25 or
  returns go absurd), and mirrored price paths do NOT work as a random
  baseline for momentum strategies (momentum is direction-symmetric) —
  randomize the decision, not the data.
- Known v2 pitfalls already hit once: naked short straddles lose even
  with a variance risk premium (the stop converts symmetric gamma noise
  into realized losses) — delta-hedge them; and selling vol into
  *quiet* tape means selling *cheap* vol that mean-reverts up against
  you — gate vol selling on rich implied (atm_iv > IV_RICH).
- `sim.py` is consumed by `options_sim.py` and `validate.py`. If you
  touch `Market.generate_day` or `MomentumBot`, rerun all three and
  confirm v1 numbers are unchanged (the RNG draw sequence must not
  shift, or every seeded result table in README changes).
