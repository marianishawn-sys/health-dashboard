# Session Handoff — Cloud Session, 2026-06-10

For the main Claude Code session. Everything below is committed and
pushed to branch **`claude/day-trading-sim-1zir7q`** of
`marianishawn-sys/health-dashboard`. Pull it with:

```
git fetch origin claude/day-trading-sim-1zir7q
git checkout claude/day-trading-sim-1zir7q
```

## 1. What was built this session

### day-trading-sim/ — paper trading simulator (v1–v3)
- `sim.py` — synthetic minute-bar market (regime-switching momentum,
  vol clustering, intraday U-shape, gaps, jumps) + EMA(6/24) momentum
  shares bot. 1% risk/trade, vol-scaled trailing stops, 2x max
  leverage, flat by close, ~1.5bp/side costs. Result: +108%/yr mean,
  profitable in 20/20 seeded worlds; coin-flip ablation −63%.
- `options_sim.py` — Black-Scholes layer, synthetic IV surface (put
  skew + 15% variance risk premium), regime-mapped options bot: long
  ~5-day ATM calls/puts in trends, short delta-hedged same-day
  straddles when IV is rich. +77% mean, 20/20 worlds, both legs
  independently positive.
- `validate.py` — walk-forward optimization (train days 1–125, frozen
  params on unseen 126–250: +102% → +94%, tuned beats default 20/20),
  per-world t-stats (significant 17/20), pooled bootstrap CI,
  3×3 parameter robustness surface, cost stress (2x costs flips +108%
  to −68%).
- `README.md` (results + honest caveats) · `ROADMAP.md` (agent handoff:
  evaluation rules, prioritized roadmap, known pitfalls). **Rules that
  must survive any future change:** multi-seed distributions, signal-
  ablated baselines, costs on every fill, walk-forward for any tuning.

### gpu-mining/ — off-peak A40 mining kit (tuned to the real tariff)
- `offpeak-miner.sh` — prepare/run/cleanup/status; 220W power cap,
  busy-GPU guard, optional Home Assistant gate
  (`input_select.jarvis_power_band == ulo_unlimited`).
- `systemd/` — start 23:00 / stop 07:00 daily (Ontario ULO window —
  the only window where mining nets positive at the real rates).
- `gpu_status.sh` — emits GPU JSON for the dashboard panel; workload =
  miner (service active) / jarvis (>10% util) / idle. Wire in n8n:
  Webhook POST `/webhook/savant-gpu` → Execute Command → Respond.
- `profitability.py` — calculator. With the real tariff (ULO all-in
  ≈ $0.095 USD/kWh, server baseline sunk): ULO-only mining ≈
  **+$0.03/day**; hosting ≈ +$1.56/day. Mining = experiment, not income.
- **Context that changed mid-session:** the A40 REPLACES the RTX 8000
  (now the only GPU). Powerwall caps no longer block daytime mining —
  the rates do. Mining is the residual workload; JARVIS heavy compute
  owns ULO and should `systemctl stop gpu-miner.service` first.

### savant/SAVANT_Dashboard_v2.html — Command Console v2
Additive upgrade of the Drive original (original untouched):
- Command palette (Ctrl+K), boot sequence (once/session, click-skip,
  honors reduced-motion), live ticker tape synthesizing all feeds,
  keyboard shortcuts (R / F / 1-2-3 / “/”), FX kill-switch
  (localStorage), hidden-tab animation pause.
- **Bug fixed:** the original `band()` had wrong ULO windows. Now
  matches 03_The_Energy_Plan exactly (ULO 23–7 daily · weekend OFF
  7–23 · weekday MID 7–16 & 21–23 · ON 16–21) — unit-tested, 12 cases.
  Energy panel shows live countdown + Powerwall cap per band.
- **GPU panel** (right wing): CUDA util + VRAM bars, temp/power/cap,
  workload pill; temp thresholds 75/83°C (A40 is passively cooled);
  polls `/webhook/savant-gpu` every 30s; "awaiting A40" fallback.

## 2. Pending actions (need local/desktop hands)
1. Deploy dashboard: copy `savant/SAVANT_Dashboard_v2.html` into the
   SAVANT folder in G:\My Drive (next to neural-map.html /
   savant-orgmap.html so iframes resolve). A/B vs original, rename
   when satisfied.
2. When the A40 is installed: copy `gpu-mining/gpu_status.sh` and
   `offpeak-miner.sh` to `/usr/local/bin/` on Cerebro; build the
   3-node n8n webhook `/webhook/savant-gpu`; only configure the miner
   itself if the profitability numbers justify it (they barely do).
3. Update `03_The_Energy_Plan.docx` — still references the RTX 8000.
4. Optional: continue day-trading-sim roadmap (`ROADMAP.md` items 3–6).

## 3. Environment facts (do not re-derive)
- Ontario ULO four-band tariff (Essex Powerlines); Tesla Powerwall 3
  caps: ULO unlimited / mid 750W / weekend 900W / on-peak 525W.
- Server (Cerebro, 192.168.2.100) runs 24/7 — baseline power is sunk.
- A40 = only GPU, 48GB, 300W TDP, passively cooled (chassis airflow).
- Dashboard feeds: `/webhook/savant-health` (POST), positions.json →
  Google Sheet `1bp4nzNlyzqZqYOt5ks9Hdz0066ZZ3U1_0jpLWfqKqE8` →
  snapshot fallback; health.json; new `/webhook/savant-gpu`.

## 4. Companion document
`SELECTOR_PROGRAMME_REVIEW.md` (same branch) — fresh-eyes review of
"11-Selector Trading Programme — Complete Process and Operating
Document" with all identified holes, prioritized.
