#!/usr/bin/env python3
"""Paper-money day trading simulator.

A synthetic intraday market with realistic structure (regime-switching
trends, volatility clustering, intraday U-shaped volatility, overnight
gaps, spreads/commissions/slippage) and a momentum day-trading bot that
trades it with strict risk management.

Honesty notes:
- No real money, no real market data (network-restricted environment).
- The market generator has genuine intraday momentum regimes, which is
  what gives any strategy a theoretical edge here; real markets have
  weaker, less stationary versions of this. A positive result here means
  "the bot exploits momentum efficiently net of costs", not "this would
  print money live".
- To avoid cherry-picking, the experiment runs many independent seeded
  worlds and reports the full distribution, alongside baselines.
"""

import numpy as np

MINUTES_PER_DAY = 390  # 9:30 - 16:00


# ---------------------------------------------------------------- market

class Market:
    """One tradeable instrument, minute bars, regime-switching drift."""

    # regimes: 0 = chop, 1 = uptrend, 2 = downtrend
    REGIME_DRIFT_BP = {0: 0.0, 1: 0.9, 2: -0.9}  # drift per minute, basis points
    AVG_REGIME_LEN = {0: 90, 1: 40, 2: 40}       # minutes

    def __init__(self, rng: np.random.Generator, start_price=100.0):
        self.rng = rng
        self.price = start_price
        self.base_minute_vol = 0.0005  # 5bp/min ~ 1%/day
        self.vol_state = 1.0           # volatility clustering factor

    def _intraday_vol_shape(self, t):
        """U-shape: busy open, quiet lunch, busy close."""
        x = t / MINUTES_PER_DAY
        return 0.75 + 1.1 * np.exp(-12 * x) + 0.9 * np.exp(-12 * (1 - x))

    def generate_day(self):
        """Return (prices, regimes) arrays of length MINUTES_PER_DAY."""
        rng = self.rng
        # overnight gap
        self.price *= 1 + rng.normal(0, 0.004)

        prices = np.empty(MINUTES_PER_DAY)
        regimes = np.empty(MINUTES_PER_DAY, dtype=int)
        regime = 0
        for t in range(MINUTES_PER_DAY):
            if rng.random() < 1.0 / self.AVG_REGIME_LEN[regime]:
                # leave current regime; from chop, pick a trend; from a
                # trend, usually fall back to chop
                if regime == 0:
                    regime = 1 if rng.random() < 0.5 else 2
                else:
                    regime = 0 if rng.random() < 0.8 else (3 - regime)
            # volatility clustering (slow mean-reverting log-vol)
            self.vol_state = np.clip(
                self.vol_state + 0.03 * (1.0 - self.vol_state) + rng.normal(0, 0.06),
                0.5, 3.0)
            vol = self.base_minute_vol * self.vol_state * self._intraday_vol_shape(t)
            drift = self.REGIME_DRIFT_BP[regime] * 1e-4
            ret = drift + vol * rng.standard_normal()
            # occasional news jump
            if rng.random() < 0.001:
                ret += rng.normal(0, 0.004)
            self.price *= 1 + ret
            prices[t] = self.price
            regimes[t] = regime
        return prices, regimes


# ---------------------------------------------------------------- costs

SPREAD_BP = 1.0        # half-spread paid each side, basis points
COMMISSION_BP = 0.2    # per side
SLIPPAGE_BP = 0.3      # per side

COST_PER_SIDE = (SPREAD_BP / 2 + COMMISSION_BP + SLIPPAGE_BP) * 1e-4


# ---------------------------------------------------------------- bot

class MomentumBot:
    """EMA-crossover momentum with vol filter and hard risk limits."""

    FAST, SLOW = 6, 24            # EMA spans in minutes
    ENTRY_Z = 1.1                 # trend strength threshold (in vol units)
    STOP_VOL_MULT = 3.0           # stop distance in minute-vol units
    RISK_PER_TRADE = 0.01         # fraction of equity risked per trade
    MAX_LEVERAGE = 2.0
    NO_ENTRY_AFTER = MINUTES_PER_DAY - 30   # don't open trades near close
    WARMUP = 30

    def __init__(self, equity=100_000.0, coin_flip_rng=None):
        """If coin_flip_rng is given, entry *direction* is randomized
        (identical entry timing, sizing, and exits) — the baseline that
        isolates whether the momentum signal itself adds value."""
        self.equity = equity
        self.trades = []          # per-trade pnl
        self.coin_flip_rng = coin_flip_rng

    def trade_day(self, prices):
        """Trade one day of minute closes. Returns day P&L."""
        eq_start = self.equity
        fast = slow = prices[0]
        af, aslow = 2 / (self.FAST + 1), 2 / (self.SLOW + 1)
        ema_vol = 0.0005 * prices[0]   # EMA of abs price change
        av = 2 / (30 + 1)

        pos = 0          # shares, signed
        entry_px = stop_px = 0.0
        day_events = []  # (minute, 'buy'/'sell'/'exit', price)

        for t in range(1, MINUTES_PER_DAY):
            px = prices[t]
            fast += af * (px - fast)
            slow += aslow * (px - slow)
            ema_vol += av * (abs(px - prices[t - 1]) - ema_vol)
            if t < self.WARMUP:
                continue

            signal = (fast - slow) / max(ema_vol, 1e-9)

            # --- manage open position
            if pos != 0:
                stop_hit = (pos > 0 and px <= stop_px) or (pos < 0 and px >= stop_px)
                signal_gone = (pos > 0 and signal < 0) or (pos < 0 and signal > 0)
                eod = t >= MINUTES_PER_DAY - 5
                if stop_hit or signal_gone or eod:
                    fill = px * (1 - np.sign(pos) * COST_PER_SIDE)
                    pnl = pos * (fill - entry_px)
                    self.equity += pnl
                    self.trades.append(pnl)
                    day_events.append((t, 'exit', px))
                    pos = 0
                else:
                    # trail the stop in our favor
                    trail = px - np.sign(pos) * self.STOP_VOL_MULT * ema_vol
                    stop_px = max(stop_px, trail) if pos > 0 else min(stop_px, trail)

            # --- look for entries
            if pos == 0 and t < self.NO_ENTRY_AFTER and abs(signal) > self.ENTRY_Z:
                if self.coin_flip_rng is not None:
                    direction = 1 if self.coin_flip_rng.random() < 0.5 else -1
                else:
                    direction = 1 if signal > 0 else -1
                stop_dist = self.STOP_VOL_MULT * ema_vol
                shares = (self.equity * self.RISK_PER_TRADE) / stop_dist
                shares = min(shares, self.equity * self.MAX_LEVERAGE / px)
                pos = direction * shares
                entry_px = px * (1 + direction * COST_PER_SIDE)
                stop_px = px - direction * stop_dist
                day_events.append((t, 'buy' if direction > 0 else 'sell', px))

        return self.equity - eq_start, day_events


# ---------------------------------------------------------------- baselines

def buy_and_hold(prices_by_day, equity=100_000.0):
    """Buy at first open, hold to the end (incl. overnight)."""
    first, last = prices_by_day[0][0], prices_by_day[-1][-1]
    return equity * last / first * (1 - 2 * COST_PER_SIDE)


def random_trader(prices_by_day, rng, equity=100_000.0):
    """Same entry timing, sizing and exits as the bot — but the trade
    direction is a coin flip. Any gap between the bot and this baseline
    is attributable to the momentum signal."""
    bot = MomentumBot(equity, coin_flip_rng=rng)
    for prices in prices_by_day:
        bot.trade_day(prices)
    return bot.equity


# ---------------------------------------------------------------- experiment

def run_world(seed, n_days=250):
    rng = np.random.default_rng(seed)
    market = Market(rng)
    days = [market.generate_day()[0] for _ in range(n_days)]

    bot = MomentumBot()
    daily_pnl, equity_curve = [], [bot.equity]
    sample_day = None
    for i, prices in enumerate(days):
        pnl, events = bot.trade_day(prices)
        daily_pnl.append(pnl)
        equity_curve.append(bot.equity)
        if sample_day is None and len(events) >= 4:
            sample_day = (i, prices, events)

    bh = buy_and_hold(days)
    rnd = random_trader(days, np.random.default_rng(seed + 10_000))

    daily = np.array(daily_pnl)
    curve = np.array(equity_curve)
    peak = np.maximum.accumulate(curve)
    max_dd = ((curve - peak) / peak).min()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    wins = np.array(bot.trades)

    return {
        'seed': seed,
        'final': bot.equity,
        'return_pct': (bot.equity / 100_000 - 1) * 100,
        'bh_return_pct': (bh / 100_000 - 1) * 100,
        'rnd_return_pct': (rnd / 100_000 - 1) * 100,
        'sharpe': sharpe,
        'max_dd_pct': max_dd * 100,
        'n_trades': len(wins),
        'win_rate': (wins > 0).mean() * 100 if len(wins) else 0.0,
        'curve': curve,
        'sample_day': sample_day,
    }


def main():
    n_worlds, n_days = 20, 250
    results = [run_world(seed, n_days) for seed in range(1, n_worlds + 1)]

    rets = np.array([r['return_pct'] for r in results])
    bh = np.array([r['bh_return_pct'] for r in results])
    rnd = np.array([r['rnd_return_pct'] for r in results])

    print(f"=== Day-trading paper sim: {n_worlds} worlds x {n_days} days, "
          f"$100k start, all costs included ===\n")
    print(f"{'seed':>4} {'bot %':>8} {'b&h %':>8} {'random %':>9} "
          f"{'sharpe':>7} {'maxDD %':>8} {'trades':>7} {'win %':>6}")
    for r in results:
        print(f"{r['seed']:>4} {r['return_pct']:>8.1f} {r['bh_return_pct']:>8.1f} "
              f"{r['rnd_return_pct']:>9.1f} {r['sharpe']:>7.2f} "
              f"{r['max_dd_pct']:>8.1f} {r['n_trades']:>7} {r['win_rate']:>6.1f}")

    print(f"\nBot     : mean {rets.mean():+.1f}%  median {np.median(rets):+.1f}%  "
          f"worst {rets.min():+.1f}%  profitable worlds {(rets > 0).sum()}/{n_worlds}")
    print(f"Buy&hold: mean {bh.mean():+.1f}%  median {np.median(bh):+.1f}%  "
          f"worst {bh.min():+.1f}%  profitable worlds {(bh > 0).sum()}/{n_worlds}")
    print(f"Random  : mean {rnd.mean():+.1f}%  median {np.median(rnd):+.1f}%  "
          f"worst {rnd.min():+.1f}%  profitable worlds {(rnd > 0).sum()}/{n_worlds}")

    plot(results)
    return results


def plot(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for r in results:
        ax1.plot(r['curve'] / 1000, lw=0.9, alpha=0.7)
    ax1.axhline(100, color='k', ls='--', lw=0.8)
    ax1.set_title(f"Equity curves, {len(results)} independent worlds (250 days each)")
    ax1.set_xlabel("trading day")
    ax1.set_ylabel("equity ($k)")

    sample = next(r['sample_day'] for r in results if r['sample_day'])
    day_idx, prices, events = sample
    ax2.plot(prices, color='gray', lw=1)
    style = {'buy': ('^', 'green'), 'sell': ('v', 'red'), 'exit': ('x', 'black')}
    seen = set()
    for t, kind, px in events:
        m, c = style[kind]
        ax2.scatter(t, px, marker=m, color=c, zorder=3, s=60,
                    label=kind if kind not in seen else None)
        seen.add(kind)
    ax2.legend()
    ax2.set_title(f"Sample day (day {day_idx + 1}, seed {results[0]['seed']}): bot entries/exits")
    ax2.set_xlabel("minute of session")
    ax2.set_ylabel("price ($)")

    fig.tight_layout()
    fig.savefig('day-trading-sim/results.png', dpi=110)
    print("\nChart written to day-trading-sim/results.png")


if __name__ == '__main__':
    main()
