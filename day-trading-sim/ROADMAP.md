# Roadmap & Agent Handoff

Context document for any future session/agent continuing this project.
Read `README.md` first for what exists; this file is what to build next
and the rules to build it by.

## Current state (v1)

- `sim.py`: synthetic minute-bar market (regime-switching momentum,
  vol clustering, intraday U-shape, gaps, jumps) + EMA(6/24) momentum
  bot with vol-scaled trailing stops, 1% risk/trade, 2x max leverage,
  flat by close. Costs ~1.5bp/side on every fill.
- Evaluation: 20 seeded worlds x 250 days vs buy-and-hold and a
  coin-flip baseline (identical mechanics, random direction).
- v1 results: bot positive 20/20 worlds (mean +108%/yr), coin-flip
  trader -63% — the gap is the value of the signal.

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

1. **Walk-forward optimization** — split each world into train/test
   windows, grid-search bot params on train, report test-only results.
   Proves the edge isn't overfit to hand-tuned constants.
2. **Options layer** — the big one:
   - Black-Scholes pricer + synthetic IV surface (put skew, term
     structure); IV level mean-reverts and spikes with realized vol.
   - Chain generation: strikes around spot, weekly + monthly expiries.
   - Realistic option spreads (5-50x wider than stock in bp terms) —
     expect naive strategies to die here; that's the point.
   - Regime-mapped strategy: trend regime → long calls/puts (convexity,
     theta drag); chop regime → short straddles / iron condors (theta
     harvest, tail risk). Manage delta/gamma/vega limits, not just
     direction.
   - Baselines: shares-only bot (v1) on same paths, plus
     direction-randomized options bot.
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
