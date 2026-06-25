# SAVANT Dashboard v2 — Change Directions for the Main Code Session

What was done to `SAVANT_Dashboard.html` in the cloud session of
2026-06-10, in enough detail to maintain, extend, or re-apply the
changes. The modified file is **`savant/SAVANT_Dashboard_v2.html`** on
branch `claude/day-trading-sim-1zir7q` of
`marianishawn-sys/health-dashboard`.

## Source and deployment

- **Base file:** `SAVANT_Dashboard.html` from Google Drive (the
  87,707-byte version, modified 2026-06-09). The original was **not
  touched** — v2 is a separate file so they can be A/B'd.
- **Deploy:** copy `savant/SAVANT_Dashboard_v2.html` into the SAVANT
  folder in `G:\My Drive` (the folder containing `neural-map.html`,
  `savant-orgmap.html`, `avatars3d.html`, `SAVANT_Cost_Dashboard.html`,
  `SAVANT_Health_Dashboard.html`, `SAVANT_Architecture.html`). All
  iframe/src and chip links are **relative**, so it must sit next to
  its siblings. Rename over the original only after eyeballing it.
- All changes are **additive**: every original element id, feed
  function, tab, and sort behavior is preserved. Both `<script>`
  blocks pass `node --check`.

## 1. Bug fix — energy band schedule (the one functional correction)

The original `band()` was wrong vs the real tariff: it had OFF 7–11,
MID 11–17 (weekdays), ON 17–19. The actual Ontario ULO schedule (per
`03_The_Energy_Plan`) is:

| Band | Window |
|---|---|
| ULO | 11pm–7am every day |
| OFF | 7am–11pm Sat/Sun |
| MID | 7am–4pm and 9–11pm weekdays |
| ON  | 4–9pm weekdays |

`band(d)` was rewritten to that table (it now takes an optional Date
arg for testability) and was verified with a 12-case unit test
covering every boundary and weekend behavior. Two new helpers:

- `BAND_CAP` — maps band → Powerwall household cap
  (`ULO: no cap / OFF: 900 W / MID: 750 W / ON: 525 W`).
- `bandNext()` — walks forward minute-by-minute (max 24h) to find the
  next band change.

The Energy panel gained `<div id="ebNext">` under the band strip
showing e.g. `MID · 750 W cap · 2h 14m → ON (525 W cap)`. The
`renderEnergy` polling interval was changed **600000 → 60000 ms** so
the countdown stays live.

## 2. GPU — A40 panel (new, right wing, below Energy)

Markup: `<div class="panel" id="gpuPanel">` with ids `gpuState`
(workload pill), `gpuUtil`/`gpuUtilBar`, `gpuMem`/`gpuMemBar`,
`gpuTemp`, `gpuPow`, `gpuCap`, `gpuFeed`. New CSS classes
`.gbars/.gbar` (the two horizontal bars).

Logic (`GPU_CFG`, `GPU_SNAPSHOT`, `renderGpu`, `loadGpu`):
- **Feed:** POST `{}` to `http://192.168.2.100:5678/webhook/savant-gpu`
  (same fetch pattern as the savant-health webhook), 5s timeout,
  polled every **30s** and on every manual refresh (`refreshAll` now
  calls `loadGpu`).
- **Fallback:** offline/unreachable → baked snapshot, pill shows
  `offline`, feed line shows "awaiting A40". Nothing errors before the
  card is installed.
- **Expected payload** (produced by `gpu-mining/gpu_status.sh` in the
  same repo branch; wire it in n8n as Webhook → Execute Command →
  Respond to Webhook):

```json
{"generated":"2026-06-10T14:03:00Z","workload":"miner|jarvis|idle",
 "gpus":[{"index":0,"name":"NVIDIA A40","util":37,"memUsed":18432,
 "memTotal":46068,"temp":71,"power":214,"powerLimit":220}]}
```

- **Temp thresholds tuned for the passively-cooled A40:** green <75°C,
  yellow 75–82°C, red ≥83°C (throttle zone); the util bar also turns
  red at ≥83°C. Workload pill colors: miner=amber, jarvis=green,
  idle=blue, offline=grey.

## 3. Live ticker tape (new, fixed bottom bar)

- Markup: `<div class="ticker">` with `#tape`; CSS `.ticker/.ti` and a
  70s `translateX(-50%)` marquee (content duplicated 2× for a seamless
  loop; pauses on hover). `.wrap` bottom padding 54 → 92px to clear it.
- Data flow: a global `TICK = {}` object + `updateTicker()` (defined
  just after `esc()`, so it exists before any renderer runs). Each
  existing renderer now deposits its facts and calls `updateTicker()`:
  - `render()` → `TICK.sys` (green/yellow/red counts, integrity %)
  - `renderEnergy()` → `TICK.e` (band, cap, countdown, next band)
  - `renderPositions()` → `TICK.pos` (fund value, G/L, top + lagging
    holding by P&L%)
  - `renderHealth()` → `TICK.h` (kcal vs target, protein vs floor)
  - `renderGpu()` → `TICK.gpu` (util, VRAM, temp, workload) — only
    when live
- To extend: set `TICK.whatever` anywhere and add one line to
  `updateTicker()`.

## 4. Command palette (new)

- Markup: `#pal` overlay with `#palIn` input and `#palList`.
- Open with **Ctrl/Cmd+K** (works even while typing in inputs) or `k`.
  Esc or click-outside closes. ↑↓ + Enter, or click.
- `ACTIONS` array (one place to add commands): refresh all; scroll to
  Neural Core / Org Map / Pulse / Positions / GPU panel; switch desk
  tabs 1-3; focus holdings search; toggle FX; open HA, Cost, Health,
  Architecture, Orchestrators, Org map, Source sheet, Health Concierge
  app. Filtering is substring match on the label.
- Anchor ids added for navigation: `#orgmapBand`, `#pulseBand`,
  `#positionsBand`, `#gpuPanel` (plus existing `#core`).

## 5. Boot sequence (new)

`#boot` full-screen overlay: reactor + SAVANT wordmark + five typed
status lines (one is live: current energy band + cap). ~1.6s total,
then fades and **removes itself from the DOM**. Plays once per browser
session (`sessionStorage.savantBoot`), click anywhere to skip, and is
**skipped entirely** under `prefers-reduced-motion`.

## 6. Keyboard shortcuts (new)

Ignored while typing in input/select/textarea (except Ctrl+K):
`R` refresh all · `F` FX toggle · `1/2/3` desk tabs (scrolls to the
Positions band) · `/` focus holdings search · `K`/Ctrl+K palette.

## 7. FX kill-switch + performance (new)

- `FX ON/OFF` chip in the HUD toolbar (`#fxBtn`, also `F` and a
  palette action). Off = hides starfield canvas, nebula, scanlines,
  grid floor, horizon via `body.fx-off` CSS. Persisted in
  `localStorage.savantFx`.
- The ambient canvas loop now **skips all drawing when
  `document.hidden` or FX is off** — the dashboard no longer burns GPU
  in a background tab.

## What was deliberately NOT changed

- All feed plumbing and fallback chains: savant-health webhook →
  baked SNAPSHOT; positions.json → Google Sheet gviz → POS_SNAPSHOT;
  health.json → HEALTH_SNAPSHOT. Same URLs, same parsing.
- The neural-map and org-map iframes, connector tracers, holdings
  table sort/filter/detail rows, options cards, pipeline pane, Pulse
  rings/bars, clock, sector colors.
- The original `SAVANT_Dashboard.html` in Drive.

## Verification done / still owed

- Done in-session: both script blocks parse (`node --check`); 12-case
  unit test on the new `band()`; all new element ids present.
- **Still owed (needs a browser/LAN):** visual once-over; confirm the
  savant-gpu webhook responds and the panel goes live; confirm no CORS
  surprise (it copies the savant-health fetch pattern exactly, so it
  should behave identically).
