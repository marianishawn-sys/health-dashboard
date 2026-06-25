#!/usr/bin/env python3
"""GPU yield calculator: off-peak mining vs 24/7 vs renting the card out.

No live data (run it anywhere): you supply today's gross mining revenue
for your card (look it up on whattomine.com or hashrate.no — for an
A40, the RTX 3090 is the closest listed proxy) and your electricity
tariff, it does the arithmetic people usually skip.

Example:
    python3 profitability.py --gross 0.60 --watts 220 \
        --offpeak-rate 0.08 --peak-rate 0.18 --offpeak-hours 9 \
        --rental 0.25 --rental-util 0.3
"""

import argparse


def fmt(x):
    return f"${x:+,.2f}/day  (${x * 365:+,.0f}/yr)"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--gross', type=float, default=0.60,
                   help='gross mining revenue, USD/day at 24/7 (whattomine)')
    p.add_argument('--watts', type=float, default=220,
                   help='wall power while mining, W (power-limited A40 ~220)')
    p.add_argument('--idle-watts', type=float, default=15,
                   help='card idle draw when not mining, W')
    p.add_argument('--offpeak-rate', type=float, default=0.08,
                   help='off-peak electricity, USD/kWh')
    p.add_argument('--peak-rate', type=float, default=0.18,
                   help='peak electricity, USD/kWh')
    p.add_argument('--offpeak-hours', type=float, default=9,
                   help='length of off-peak window, hours/day')
    p.add_argument('--rental', type=float, default=0.25,
                   help='achievable marketplace rate when rented, USD/hr')
    p.add_argument('--rental-util', type=float, default=0.30,
                   help='expected rented fraction of the day (0-1)')
    a = p.parse_args()

    kw, idle_kw = a.watts / 1000, a.idle_watts / 1000
    peak_hours = 24 - a.offpeak_hours

    # mining 24/7
    gross_247 = a.gross
    energy_247 = kw * (a.offpeak_hours * a.offpeak_rate + peak_hours * a.peak_rate)
    net_247 = gross_247 - energy_247

    # mining off-peak only (revenue scales with uptime)
    gross_op = a.gross * a.offpeak_hours / 24
    energy_op = (kw * a.offpeak_hours * a.offpeak_rate
                 + idle_kw * peak_hours * a.peak_rate)
    net_op = gross_op - energy_op

    # renting the card out (rented hours spread across the tariff day;
    # assume full power while rented, idle otherwise)
    rent_hours = 24 * a.rental_util
    gross_rent = rent_hours * a.rental
    blended_rate = (a.offpeak_hours * a.offpeak_rate
                    + peak_hours * a.peak_rate) / 24
    energy_rent = (kw * rent_hours + idle_kw * (24 - rent_hours)) * blended_rate
    net_rent = gross_rent - energy_rent

    # break-even electricity price for 24/7 mining
    breakeven = a.gross / (kw * 24)

    print(f"GPU yield comparison ({a.watts:.0f}W mining, "
          f"off-peak {a.offpeak_hours:.0f}h @ ${a.offpeak_rate}/kWh, "
          f"peak @ ${a.peak_rate}/kWh)\n")
    print(f"  mine 24/7        : gross ${gross_247:.2f}  energy ${energy_247:.2f}"
          f"  ->  net {fmt(net_247)}")
    print(f"  mine off-peak    : gross ${gross_op:.2f}  energy ${energy_op:.2f}"
          f"  ->  net {fmt(net_op)}")
    print(f"  rent out (host)  : gross ${gross_rent:.2f}  energy ${energy_rent:.2f}"
          f"  ->  net {fmt(net_rent)}"
          f"   [{a.rental_util:.0%} util @ ${a.rental}/hr]")
    print(f"\n  mining breaks even 24/7 below ${breakeven:.3f}/kWh")
    if net_op < net_rent:
        print("  -> at these inputs, hosting beats off-peak mining "
              f"by ${net_rent - net_op:.2f}/day")


if __name__ == '__main__':
    main()
