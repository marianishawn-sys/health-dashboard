#!/usr/bin/env python3
"""Options day trading on the synthetic market from sim.py (paper money).

Adds a Black-Scholes pricing layer with a synthetic implied-vol surface
and realistic option spreads, plus a regime-mapped options bot:

- trend regime (strong momentum signal): buy ~5-day ATM calls/puts —
  convex directional exposure, capped downside, small intraday theta.
- chop regime (quiet signal): sell a same-day ATM straddle and harvest
  the variance risk premium (implied vol is quoted ~15% above realized,
  mirroring the persistent premium in real index options).

Evaluated with the same honesty rules as v1: 20 seeded worlds x 250
days, full distribution, signal-ablated baseline (coin-flip direction
on the directional leg), v1 shares bot on the identical price paths,
and every fill pays the option's bid/ask spread.
"""

from math import erf, log, sqrt

import numpy as np

from sim import COST_PER_SIDE, MINUTES_PER_DAY, Market, MomentumBot, SignalTracker

# ------------------------------------------------------------- pricing

ANNUALIZE = sqrt(MINUTES_PER_DAY * 252)   # minute vol -> annual vol
VRP = 1.15            # implied quoted above realized (variance risk premium)
BASE_MINUTE_VOL = 0.0005


def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def bs_price(S, K, T, iv, is_call):
    """Black-Scholes, r = 0 (intraday horizons; rates are noise here)."""
    if T <= 1e-9 or iv <= 0:
        return max(S - K, 0.0) if is_call else max(K - S, 0.0)
    v = iv * sqrt(T)
    d1 = log(S / K) / v + 0.5 * v
    d2 = d1 - v
    call = S * norm_cdf(d1) - K * norm_cdf(d2)
    return call if is_call else call + K - S


class IVSurface:
    """Quoted implied vol: tracks the market's volatility state, carries
    a variance risk premium, and has a mild put skew."""

    def atm_iv(self, vol_state):
        return BASE_MINUTE_VOL * ANNUALIZE * (0.5 + 0.5 * vol_state) * VRP

    def iv(self, S, K, vol_state):
        skew = 1.0 - 0.8 * log(K / S)      # lower strikes -> richer vol
        return max(0.05, self.atm_iv(vol_state) * skew)


def half_spread(mid):
    """Option half-spread: $0.01 floor or 1.5% of premium — liquid-chain
    economics, still 5-20x wider than the stock in bp-of-notional terms."""
    return max(0.01, 0.015 * mid)


# ------------------------------------------------------------- bot

class OptionsBot:
    """Regime-mapped options day trader. One position at a time, always
    flat by the close, 1% of equity risked per trade."""

    ENTRY_Z = 1.3                 # momentum threshold for directional trades
    QUIET_Z = 0.45                # |signal| below this counts as chop
    STOP_FRAC = 0.40              # exit long option at -40% of premium
    STRADDLE_STOP = 2.00          # disaster stop only — the hedge does the work
    HEDGE_BAND = 0.25             # rehedge when |net delta| > 25% of max
    IV_RICH = 0.19                # only sell vol when quoted IV is above average,
                                  # so mean reversion works for the short, not against
    RISK_PER_TRADE = 0.01
    MAX_DELTA_NOTIONAL = 2.0      # |delta| * S * shares <= 2x equity
    DIR_EXPIRY_DAYS = 5           # directional: ~weekly option
    NO_ENTRY_AFTER = MINUTES_PER_DAY - 45
    EOD_FLATTEN = MINUTES_PER_DAY - 5
    WARMUP = 30
    QUIET_MINUTES = 10            # signal must be quiet this long to sell vol

    def __init__(self, equity=100_000.0, coin_flip_rng=None):
        """coin_flip_rng randomizes the *direction* of directional trades
        (call vs put) with identical timing/sizing/exits — the ablation
        baseline. The straddle leg has no direction, so it is unchanged."""
        self.equity = equity
        self.surface = IVSurface()
        self.coin_flip_rng = coin_flip_rng
        self.dir_trades, self.straddle_trades = [], []

    # --- marks

    def _dir_T(self, t):
        return (self.DIR_EXPIRY_DAYS - t / MINUTES_PER_DAY) / 252

    def _straddle_T(self, t):
        return max(1e-6, (MINUTES_PER_DAY + 30 - t) / MINUTES_PER_DAY) / 252

    def _dir_mid(self, S, K, t, vol_state, is_call):
        return bs_price(S, K, self._dir_T(t), self.surface.iv(S, K, vol_state), is_call)

    def _straddle_mid(self, S, K, t, vol_state):
        iv = self.surface.iv(S, K, vol_state)
        T = self._straddle_T(t)
        return bs_price(S, K, T, iv, True) + bs_price(S, K, T, iv, False)

    def _straddle_delta(self, S, K, t, vol_state):
        """Delta per straddle share: 2*N(d1) - 1."""
        iv = self.surface.iv(S, K, vol_state)
        v = iv * sqrt(self._straddle_T(t))
        d1 = log(S / K) / v + 0.5 * v
        return 2 * norm_cdf(d1) - 1

    # --- one day

    def trade_day(self, prices, vol_states):
        """Directional and straddle positions occupy independent slots —
        they are different exposures (delta vs gamma/theta) and a desk
        would run both books at once. Risk is still 1% per trade."""
        eq_start = self.equity
        tracker = SignalTracker(prices[0])
        dir_pos = None            # (is_call, K, n, entry_debit)
        strad_pos = None          # (K, n, entry_credit)
        quiet_run = 0
        sold_straddle_today = False

        for t in range(1, MINUTES_PER_DAY):
            S, vs = prices[t], vol_states[t]
            signal = tracker.update(S)
            quiet_run = quiet_run + 1 if abs(signal) < self.QUIET_Z else 0
            if t < self.WARMUP:
                continue

            # ---- manage directional position
            if dir_pos is not None:
                is_call, K, n, debit = dir_pos
                mid = self._dir_mid(S, K, t, vs, is_call)
                signal_gone = (is_call and signal < 0) or (not is_call and signal > 0)
                if (mid <= (1 - self.STOP_FRAC) * debit or signal_gone
                        or t >= self.EOD_FLATTEN):
                    fill = max(0.0, mid - half_spread(mid))
                    pnl = (fill - debit) * 100 * n
                    self.equity += pnl
                    self.dir_trades.append(pnl)
                    dir_pos = None

            # ---- manage straddle position (delta-hedged with shares)
            if strad_pos is not None:
                K, n, credit, hedge_sh, hedge_cash = strad_pos
                mid = self._straddle_mid(S, K, t, vs)
                if mid >= self.STRADDLE_STOP * credit or t >= self.EOD_FLATTEN:
                    fill = mid + 2 * half_spread(mid / 2)   # pay spread on both legs
                    hedge_cash += hedge_sh * S - abs(hedge_sh) * S * COST_PER_SIDE
                    pnl = (credit - fill) * 100 * n + hedge_cash
                    self.equity += pnl
                    self.straddle_trades.append(pnl)
                    strad_pos = None
                else:
                    # short straddle delta is -(2N(d1)-1); hold that many
                    # shares to neutralize, rebalancing inside a band
                    target = round(self._straddle_delta(S, K, t, vs) * n * 100)
                    if abs(target - hedge_sh) > self.HEDGE_BAND * n * 100:
                        d = target - hedge_sh
                        hedge_cash -= d * S + abs(d) * S * COST_PER_SIDE
                        strad_pos = (K, n, credit, target, hedge_cash)

            if t >= self.NO_ENTRY_AFTER:
                continue

            # ---- directional entry: ride the trend with a long option
            if dir_pos is None and abs(signal) > self.ENTRY_Z:
                if self.coin_flip_rng is not None:
                    is_call = self.coin_flip_rng.random() < 0.5
                else:
                    is_call = signal > 0
                K = round(S)
                mid = self._dir_mid(S, K, t, vs, is_call)
                debit = mid + half_spread(mid)
                risk = self.STOP_FRAC * debit * 100
                n = int(self.equity * self.RISK_PER_TRADE / max(risk, 1e-9))
                n = min(n, int(self.MAX_DELTA_NOTIONAL * self.equity / (0.5 * S * 100)))
                if n > 0:
                    dir_pos = (is_call, K, n, debit)

            # ---- vol entry: sell the day's straddle into quiet tape
            if (strad_pos is None and not sold_straddle_today
                    and quiet_run >= self.QUIET_MINUTES and 60 <= t <= 270
                    and self.surface.atm_iv(vs) > self.IV_RICH):
                K = round(S)
                mid = self._straddle_mid(S, K, t, vs)
                credit = mid - 2 * half_spread(mid / 2)
                risk = (self.STRADDLE_STOP - 1) * credit * 100
                n = int(self.equity * self.RISK_PER_TRADE / max(risk, 1e-9))
                n = min(n, int(1.5 * self.equity / (S * 100)))   # notional cap
                if n > 0 and credit > 0:
                    strad_pos = (K, n, credit, 0, 0.0)   # hedge starts flat (ATM)
                    sold_straddle_today = True

        return self.equity - eq_start


# ------------------------------------------------------------- experiment

def run_world(seed, n_days=250):
    rng = np.random.default_rng(seed)
    market = Market(rng)
    days = [market.generate_day() for _ in range(n_days)]   # (prices, regimes, vols)

    bot = OptionsBot()
    shares_bot = MomentumBot()
    rnd_bot = OptionsBot(coin_flip_rng=np.random.default_rng(seed + 10_000))

    curve = [bot.equity]
    dir_cum, strad_cum = [0.0], [0.0]
    for prices, _, vols in days:
        bot.trade_day(prices, vols)
        curve.append(bot.equity)
        dir_cum.append(sum(bot.dir_trades))
        strad_cum.append(sum(bot.straddle_trades))
        shares_bot.trade_day(prices)
        rnd_bot.trade_day(prices, vols)

    curve = np.array(curve)
    daily = np.diff(curve)
    peak = np.maximum.accumulate(curve)
    dirs, strads = np.array(bot.dir_trades), np.array(bot.straddle_trades)

    return {
        'seed': seed,
        'return_pct': (curve[-1] / curve[0] - 1) * 100,
        'shares_pct': (shares_bot.equity / 100_000 - 1) * 100,
        'rnd_pct': (rnd_bot.equity / 100_000 - 1) * 100,
        'sharpe': daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0,
        'max_dd_pct': ((curve - peak) / peak).min() * 100,
        'dir_pnl': dirs.sum(), 'n_dir': len(dirs),
        'dir_win': (dirs > 0).mean() * 100 if len(dirs) else 0,
        'strad_pnl': strads.sum(), 'n_strad': len(strads),
        'strad_win': (strads > 0).mean() * 100 if len(strads) else 0,
        'curve': curve, 'dir_cum': np.array(dir_cum), 'strad_cum': np.array(strad_cum),
    }


def main():
    n_worlds, n_days = 20, 250
    results = [run_world(seed, n_days) for seed in range(1, n_worlds + 1)]

    rets = np.array([r['return_pct'] for r in results])
    shares = np.array([r['shares_pct'] for r in results])
    rnd = np.array([r['rnd_pct'] for r in results])

    print(f"=== Options day trading sim: {n_worlds} worlds x {n_days} days, "
          f"$100k start, option spreads on every fill ===\n")
    print(f"{'seed':>4} {'options %':>10} {'shares %':>9} {'rnd-dir %':>10} "
          f"{'sharpe':>7} {'maxDD %':>8} {'dir pnl':>9} {'strad pnl':>10} "
          f"{'dirN':>5} {'strN':>5}")
    for r in results:
        print(f"{r['seed']:>4} {r['return_pct']:>10.1f} {r['shares_pct']:>9.1f} "
              f"{r['rnd_pct']:>10.1f} {r['sharpe']:>7.2f} {r['max_dd_pct']:>8.1f} "
              f"{r['dir_pnl']:>9.0f} {r['strad_pnl']:>10.0f} "
              f"{r['n_dir']:>5} {r['n_strad']:>5}")

    dir_tot = np.array([r['dir_pnl'] for r in results])
    strad_tot = np.array([r['strad_pnl'] for r in results])
    print(f"\nOptions bot : mean {rets.mean():+.1f}%  median {np.median(rets):+.1f}%  "
          f"worst {rets.min():+.1f}%  profitable worlds {(rets > 0).sum()}/{n_worlds}")
    print(f"Shares bot  : mean {shares.mean():+.1f}%  median {np.median(shares):+.1f}%  "
          f"worst {shares.min():+.1f}%  profitable worlds {(shares > 0).sum()}/{n_worlds}")
    print(f"Rnd-dir opts: mean {rnd.mean():+.1f}%  median {np.median(rnd):+.1f}%  "
          f"worst {rnd.min():+.1f}%  profitable worlds {(rnd > 0).sum()}/{n_worlds}")
    print(f"Leg P&L     : directional mean ${dir_tot.mean():,.0f} "
          f"(positive {(dir_tot > 0).sum()}/{n_worlds}), "
          f"straddles mean ${strad_tot.mean():,.0f} "
          f"(positive {(strad_tot > 0).sum()}/{n_worlds})")

    plot(results)


def plot(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for r in results:
        ax1.plot(r['curve'] / 1000, lw=0.9, alpha=0.7)
    ax1.axhline(100, color='k', ls='--', lw=0.8)
    ax1.set_title(f"Options bot equity, {len(results)} worlds (250 days each)")
    ax1.set_xlabel("trading day")
    ax1.set_ylabel("equity ($k)")

    r = results[0]
    ax2.plot(r['dir_cum'] / 1000, label='directional (long calls/puts)', color='tab:blue')
    ax2.plot(r['strad_cum'] / 1000, label='short straddles (theta)', color='tab:orange')
    ax2.axhline(0, color='k', ls='--', lw=0.8)
    ax2.legend()
    ax2.set_title(f"Cumulative P&L by leg (seed {r['seed']})")
    ax2.set_xlabel("trading day")
    ax2.set_ylabel("P&L ($k)")

    fig.tight_layout()
    fig.savefig('day-trading-sim/options_results.png', dpi=110)
    print("\nChart written to day-trading-sim/options_results.png")


if __name__ == '__main__':
    main()
