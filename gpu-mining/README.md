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

## This server's actual tariff (Ontario ULO, Essex Powerlines)

From the energy plan (03_The_Energy_Plan): four OEB rate bands, with
Ultra-Low Overnight **11pm–7am every day at $0.039/kWh** (~11–15¢ CAD
all-in after delivery charges and the Ontario Electricity Rebate),
versus $0.391 on-peak (~47–52¢ all-in). The server runs 24/7
regardless, so its baseline draw is sunk cost — only the A40's
incremental ~220W while mining counts.

Two constraints beyond price:

- **Powerwall caps vs economics**: the A40 replaces the RTX 8000 as the
  server's only GPU, so baseline (~400–500W) plus a 220W power-capped
  A40 actually fits under the 750W mid-peak and 900W weekend caps
  (on-peak 525W remains off-limits). But the *rates* close those
  windows anyway: at ~15.5¢ USD/kWh all-in mid-peak, 220W of mining
  costs ~$0.034/hr against ~$0.025/hr of gross revenue — a guaranteed
  loss. Weekends are roughly breakeven. **ULO (11pm–7am) is the only
  window where mining nets positive**, which is what the timers encode.
- **The A40 is also JARVIS's GPU — and ULO is JARVIS's heavy-compute
  window.** Training, fine-tuning, and batch inference want the same
  card at the same hours. Mining is the residual workload, not the
  priority: the busy-GPU guard means the miner won't start over a
  running JARVIS job, and the orchestrator should `systemctl stop
  gpu-miner.service` before launching overnight heavy work (and may
  simply not restart it — a fine outcome, since JARVIS compute is
  worth more than $0.03/night). The optional Home Assistant gate
  (`input_select.jarvis_power_band == ulo_unlimited`) keeps the miner
  obeying the energy plan's source of truth, not just the clock.

Their numbers through the calculator (USD, ~0.73 CAD→USD, all-in ULO
≈ $0.095/kWh, card idle treated as sunk):

```
python3 profitability.py --gross 0.60 --watts 220 --idle-watts 0 \
    --offpeak-rate 0.095 --peak-rate 0.18 --offpeak-hours 8
```

→ roughly **+$0.03/day (~$12/yr)** mining ULO-only at today's
~$0.60/day gross. Hosting the card ~30% utilization nets ~$1.50/day
(~$550/yr) — but note marketplace hosting sits awkwardly with the
Powerwall caps: renters expect availability during your weekday
4–9pm forbidden window, and daily forced downtime hurts host
reliability scores. Local AI inference in the ULO window (the JARVIS
plan itself) is arguably the A40's best yield of all.

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

## Dashboard feed (`gpu_status.sh`)

Feeds the GPU panel in `SAVANT_Dashboard_v2.html`. Emits one JSON line:

```
{"generated":"…","workload":"miner|jarvis|idle","gpus":[{"name":"NVIDIA A40",
 "util":37,"memUsed":18432,"memTotal":46068,"temp":71,"power":214,"powerLimit":220}]}
```

Wire it in n8n: **Webhook** (POST `/webhook/savant-gpu`) → **Execute
Command** (`/usr/local/bin/gpu_status.sh`) → **Respond to Webhook**
(stdout as `application/json`) — the same pattern as `savant-health`.
Workload is `miner` when `gpu-miner.service` is active, `jarvis` when
the card is >10% busy otherwise, else `idle`. The dashboard polls every
30s and falls back to an "awaiting A40" snapshot when unreachable.

## Practical notes for the A40

- Passively cooled (no fans of its own) — it relies entirely on server
  chassis airflow. Watch `offpeak-miner.sh status` temps during the
  first nights; sustained mining at >80°C will throttle.
- Driver: standard datacenter driver works; `nvidia-smi -pl` needs no
  reboot. ECC can stay on (small hashrate cost) or be disabled with
  `nvidia-smi -e 0` (reboot required).
- Taxes: mined coins are generally income at receipt — keep pool
  payout records.
