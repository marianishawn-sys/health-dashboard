# Day Trading Simulator (paper money only)

A self-contained experiment answering the question: *can a bot day trade
with a positive outcome?* — honestly, with baselines, and without
cherry-picking.

## What it does

`sim.py` builds a synthetic intraday market with realistic structure:

- 390 one-minute bars per session (9:30–16:00), overnight gaps
- regime-switching drift (chop / uptrend / downtrend) — genuine but weak
  intraday momentum, ~0.9bp/min drift vs ~5bp/min noise
- volatility clustering plus the intraday U-shape (busy open/close)
- occasional news jumps
- trading costs on every fill: half-spread, commission, slippage
  (~1.5bp per side)

A momentum bot trades it: EMA(6/24) crossover scaled by realized vol,
entries only when trend strength clears a threshold, 1%-of-equity risk
per trade, vol-scaled trailing stops, max 2x leverage, no entries in the
last 30 minutes, always flat by the close.

## Keeping it honest

- **20 independent seeded worlds × 250 trading days each** — the full
  distribution is reported, not a lucky run.
- **Buy & hold baseline** on the same price paths.
- **Coin-flip baseline**: identical entry timing, sizing, stops and
  exits, but the trade *direction* is random. The gap between the bot
  and this baseline is exactly the value of the signal.

## Results

| | mean return | median | worst world | profitable worlds |
|---|---|---|---|---|
| Momentum bot | +107.6% | +92.9% | +20.0% | 20/20 |
| Buy & hold | +7.2% | +5.3% | −33.7% | 12/20 |
| Coin-flip trader | −63.2% | −67.6% | −79.8% | 0/20 |

Sharpe 0.6–3.9 across worlds, max drawdown −9% to −26%, ~4,700 trades
per world, ~35% win rate (classic trend-following: many small losses,
fewer large wins).

![results](results.png)

## The honest caveat

The bot wins because the simulated market contains real (if weak)
momentum, and the bot extracts it efficiently net of costs while the
coin-flip trader is ground to dust by the same costs. Real markets have
weaker, non-stationary, heavily-competed versions of these patterns —
this is a demonstration of disciplined strategy mechanics, not evidence
that day trading real money is a good idea. (It usually isn't.)

## Run it

```
pip install numpy matplotlib
python3 sim.py
```
