#!/usr/bin/env python3
"""Data-driven validation of the day trading strategy (paper money).

The tests a quant desk would actually run before believing a backtest:

1. Walk-forward optimization — grid-search bot parameters on the first
   125 days of each world (train), then trade the *frozen* best
   parameters on the unseen last 125 days (test). If test returns
   collapse versus train, the edge was overfit.
2. Statistical significance — per-world t-statistics on daily returns
   (positions are flat overnight, so days are close to independent),
   plus a pooled bootstrap confidence interval for the mean daily
   return.
3. Parameter robustness — the train-period return surface over the
   whole grid. A real edge is a plateau (profitable across the
   neighborhood); a fragile one is a spike at one magic setting.
4. Cost stress — rerun the default bot at 1x / 2x / 4x trading costs.
   Real edges die in friction; this measures how fast.

Same honesty rules as everywhere else in this project: 20 independent
seeded worlds, full distributions, no cherry-picking.
"""

import numpy as np

from sim import Market, MomentumBot

N_WORLDS = 20
N_DAYS = 250
SPLIT = 125          # train: days [0, SPLIT), test: [SPLIT, N_DAYS)

GRID = [(z, m) for z in (0.8, 1.1, 1.4) for m in (2.0, 3.0, 4.0)]
DEFAULT = (MomentumBot.ENTRY_Z, MomentumBot.STOP_VOL_MULT)


def gen_days(seed, n=N_DAYS):
    market = Market(np.random.default_rng(seed))
    return [market.generate_day()[0] for _ in range(n)]


def run_bot(days, entry_z=None, stop_mult=None, cost_mult=1.0):
    bot = MomentumBot(entry_z=entry_z, stop_mult=stop_mult,
                      cost_per_side=None if cost_mult == 1.0
                      else MomentumBot(0).cost * cost_mult)
    curve = [bot.equity]
    for prices in days:
        bot.trade_day(prices)
        curve.append(bot.equity)
    curve = np.array(curve)
    daily = curve[1:] / curve[:-1] - 1
    return (curve[-1] / curve[0] - 1) * 100, daily


def walk_forward(seed):
    days = gen_days(seed)
    train, test = days[:SPLIT], days[SPLIT:]

    train_rets = {p: run_bot(train, *p)[0] for p in GRID}
    best = max(train_rets, key=train_rets.get)
    test_tuned, daily_tuned = run_bot(test, *best)
    test_default, _ = run_bot(test, *DEFAULT)
    return {
        'seed': seed, 'best': best,
        'train_best': train_rets[best],
        'test_tuned': test_tuned,
        'test_default': test_default,
        'daily_tuned': daily_tuned,
        'train_grid': train_rets,
    }


def t_stat(daily):
    return daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily))


def bootstrap_ci(daily, n_boot=5000, seed=0):
    """95% CI for mean daily return (iid bootstrap; the bot is flat
    overnight so daily P&L has no carried positions)."""
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(daily, len(daily)).mean() for _ in range(n_boot)])
    return np.percentile(means, [2.5, 97.5])


def main():
    print(f"=== Strategy validation: {N_WORLDS} worlds, "
          f"train days 1-{SPLIT}, test days {SPLIT + 1}-{N_DAYS} ===\n")

    results = [walk_forward(seed) for seed in range(1, N_WORLDS + 1)]

    # ---- 1. walk-forward table
    print("1) WALK-FORWARD (tuned on train, frozen on unseen test)")
    print(f"{'seed':>4} {'best (z, stop)':>15} {'train %':>8} "
          f"{'test tuned %':>13} {'test default %':>15}")
    for r in results:
        print(f"{r['seed']:>4} {str(r['best']):>15} {r['train_best']:>8.1f} "
              f"{r['test_tuned']:>13.1f} {r['test_default']:>15.1f}")

    tuned = np.array([r['test_tuned'] for r in results])
    default = np.array([r['test_default'] for r in results])
    train = np.array([r['train_best'] for r in results])
    print(f"\n   train(best) mean {train.mean():+.1f}%  ->  test(tuned) mean "
          f"{tuned.mean():+.1f}%  |  test(default) mean {default.mean():+.1f}%")
    print(f"   test profitable: tuned {(tuned > 0).sum()}/{N_WORLDS}, "
          f"default {(default > 0).sum()}/{N_WORLDS}")
    print(f"   tuned beats default out-of-sample in "
          f"{(tuned > default).sum()}/{N_WORLDS} worlds")

    # ---- 2. significance
    print("\n2) STATISTICAL SIGNIFICANCE (test period, tuned params)")
    tstats = np.array([t_stat(r['daily_tuned']) for r in results])
    print(f"   per-world t-stat on daily returns: mean {tstats.mean():.2f}, "
          f"min {tstats.min():.2f}; significant at 5% (t>1.98) in "
          f"{(tstats > 1.98).sum()}/{N_WORLDS} worlds")
    pooled = np.concatenate([r['daily_tuned'] for r in results])
    lo, hi = bootstrap_ci(pooled)
    print(f"   pooled mean daily return {pooled.mean() * 100:+.3f}%  "
          f"(95% bootstrap CI [{lo * 100:+.3f}%, {hi * 100:+.3f}%], "
          f"n={len(pooled)} days)")

    # ---- 3. robustness surface
    print("\n3) PARAMETER ROBUSTNESS (mean train return %, all worlds)")
    print(f"{'':>10}" + "".join(f"stop={m:<6}" for m in (2.0, 3.0, 4.0)))
    surface = np.zeros((3, 3))
    for i, z in enumerate((0.8, 1.1, 1.4)):
        row = f"   z={z:<5}"
        for j, m in enumerate((2.0, 3.0, 4.0)):
            v = np.mean([r['train_grid'][(z, m)] for r in results])
            surface[i, j] = v
            row += f"{v:>9.1f} "
        print(row)
    print("   (a plateau of positives = robust edge; "
          "a single hot cell = overfitting bait)")

    # ---- 4. cost stress
    print("\n4) COST STRESS (default params, full 250 days)")
    cost_rows = []
    for mult in (1.0, 2.0, 4.0):
        rets = np.array([run_bot(gen_days(seed), cost_mult=mult)[0]
                         for seed in range(1, N_WORLDS + 1)])
        cost_rows.append((mult, rets))
        print(f"   {mult:.0f}x costs: mean {rets.mean():+7.1f}%  "
              f"median {np.median(rets):+7.1f}%  worst {rets.min():+7.1f}%  "
              f"profitable {(rets > 0).sum()}/{N_WORLDS}")

    plot(results, surface, cost_rows)


def plot(results, surface, cost_rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.6))

    train = [r['train_best'] for r in results]
    tuned = [r['test_tuned'] for r in results]
    ax1.scatter(train, tuned, color='tab:blue')
    lim = max(max(train), max(tuned)) * 1.1
    ax1.plot([0, lim], [0, lim], 'k--', lw=0.8, label='train = test')
    ax1.axhline(0, color='r', lw=0.8)
    ax1.set_xlabel("train return % (best params)")
    ax1.set_ylabel("unseen test return % (frozen params)")
    ax1.set_title("Walk-forward: does tuning survive out-of-sample?")
    ax1.legend()

    im = ax2.imshow(surface, cmap='RdYlGn', vmin=-abs(surface).max(),
                    vmax=abs(surface).max())
    ax2.set_xticks(range(3), [f"stop={m}" for m in (2.0, 3.0, 4.0)])
    ax2.set_yticks(range(3), [f"z={z}" for z in (0.8, 1.1, 1.4)])
    for i in range(3):
        for j in range(3):
            ax2.text(j, i, f"{surface[i, j]:.0f}%", ha='center', va='center')
    ax2.set_title("Mean return across parameter grid")
    fig.colorbar(im, ax=ax2, shrink=0.8)

    mults = [m for m, _ in cost_rows]
    means = [r.mean() for _, r in cost_rows]
    mins = [r.min() for _, r in cost_rows]
    ax3.bar([f"{m:.0f}x" for m in mults], means, color='tab:blue', label='mean')
    ax3.plot([f"{m:.0f}x" for m in mults], mins, 'rv-', label='worst world')
    ax3.axhline(0, color='k', lw=0.8)
    ax3.set_xlabel("trading cost multiplier")
    ax3.set_ylabel("return %")
    ax3.set_title("Edge vs friction")
    ax3.legend()

    fig.tight_layout()
    fig.savefig('day-trading-sim/validation.png', dpi=110)
    print("\nChart written to day-trading-sim/validation.png")


if __name__ == '__main__':
    main()
