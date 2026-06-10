# Off-Peak GPU Mining (NVIDIA A40)

Tooling to run a miner on an A40 only during off-peak electricity
hours, with power capping and a "don't fight other workloads" guard —
plus a calculator so the decision is made with arithmetic, not vibes.

## Read this first: the honest economics (June 2026)

- GPU mining post-Ethereum means altcoins: Kaspa-family (kHeavyHash),
  Ravencoin (KawPow), Ergo, Flux, Alephium. A top-end consumer card
  (RTX 4090) grosses roughly **$0.50–2.00/day**; an A40 is roughly
  RTX 3090-class for mining (Ampere GA102, but slower GDDR6 memory),
  so expect the **low end of that range or below**.
- Above roughly **$0.15/kWh most GPUs mine at a loss**; at $0.10/kWh
  profitability is about half of what it is at $0.06. Off-peak-only
  operation helps but also cuts revenue to the window's share of the
  day. Run `profitability.py` with your actual tariff before deciding.
- **The A40's real moat is its 48GB of VRAM, and miners don't pay for
  VRAM — AI renters do.** A40s go for ~$0.22–0.44/hr on GPU
  marketplaces (Vast.ai, RunPod). Even at modest utilization, hosting
  usually beats mining by an order of magnitude. The calculator
  compares both paths.

Check live numbers before installing anything: whattomine.com or
hashrate.no (use RTX 3090 as the A40 proxy), vast.ai/pricing for
rental rates.

## The calculator

```
python3 profitability.py --gross 0.60 --watts 220 \
    --offpeak-rate 0.08 --peak-rate 0.18 --offpeak-hours 9 \
    --rental 0.25 --rental-util 0.3
```

`--gross` is the 24/7 USD/day figure from whattomine for your card.
Output compares: mine 24/7, mine off-peak only, rent the card out —
plus the break-even electricity price.

## Off-peak scheduler (systemd)

`offpeak-miner.sh` prepares the card (persistence mode + power cap to
220W for efficiency), runs your miner, and restores the 300W default on
stop. It refuses to start if the GPU is already >10% busy, so it won't
trample a rental or AI job. Two systemd timers open and close the
window.

Install on the server (as root):

```
cp offpeak-miner.sh /usr/local/bin/ && chmod +x /usr/local/bin/offpeak-miner.sh
mkdir -p /etc/gpu-miner && cp gpu-miner.env.example /etc/gpu-miner/gpu-miner.env
# edit /etc/gpu-miner/gpu-miner.env: set MINER_CMD (wallet, pool)
cp systemd/* /etc/systemd/system/
# edit the two .timer files to match YOUR utility's off-peak hours
systemctl daemon-reload
systemctl enable --now gpu-miner-start.timer gpu-miner-stop.timer
```

Manual control / sanity checks:

```
systemctl start gpu-miner.service     # mine right now
systemctl stop gpu-miner.service      # stop and restore power limit
offpeak-miner.sh status               # utilization, power, temp, service state
```

Cron alternative (instead of the timers):

```
0 22 * * * systemctl start gpu-miner.service
0 7  * * * systemctl stop gpu-miner.service
```

## Miner software (not bundled — download yourself, verify checksums)

- **lolMiner** — broad algo coverage (KASPA, KAWPOW, AUTOLYKOS2), solid
  on Ampere datacenter cards.
- **SRBMiner-Multi / BzMiner** — alternatives worth benchmarking.
- **NiceHash** — auto-switches algorithms, pays BTC; simplest start,
  takes a fee.

Pin the miner to a specific pool region near you, use a worker name
(`WALLET.a40rig`), and benchmark 200/220/240W caps for an hour each —
the hashrate-per-watt curve, not max hashrate, is what decides profit.

## Practical notes for the A40

- Passively cooled (no fans of its own) — it relies entirely on server
  chassis airflow. Watch `offpeak-miner.sh status` temps during the
  first nights; sustained mining at >80°C will throttle.
- Driver: standard datacenter driver works; `nvidia-smi -pl` needs no
  reboot. ECC can stay on (small hashrate cost) or be disabled with
  `nvidia-smi -e 0` (reboot required).
- Taxes: mined coins are generally income at receipt — keep pool
  payout records.
