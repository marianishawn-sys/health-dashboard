# Nutrition Concierge — v6.2.0

Single-file React PWA. No build step. Edit `index.html`, push, GitHub Pages rebuilds in ~30 seconds.

**Live:** https://marianishawn-sys.github.io/health-dashboard/

## What's in v6.2.0

- **Internet macro search** — Open Food Facts search bar at the top of Manual Entry. Type a food name, tap 🔍 (or press Enter), see up to 5 results with macros per 100g. Tap a result to auto-fill all fields. Results cached in localStorage. Free, no API key.
- **Fibre field on Manual Entry** — optional fibre (g) input alongside the 4 macro fields. Auto-populated from search results.

## What was in v6.1.x

- **Edit + delete log entries** — tap any logged entry to open an edit modal. Adjust grams/unit, update macros proportionally. Delete with 5-second undo toast.
- **Multi-unit input** — log and edit in g / oz / lb. Unit preference remembered per food. Display quantity stored on log entries.
- **Dual AI scan buttons** — 📷 CAMERA (rear lens, `capture=environment`) and 🖼️ UPLOAD (photo library) on both Meal Scan and Pantry Scan.
- **Date picker fix** — calendar button now opens native date picker via `showPicker()` with `.click()` fallback.

## What was in v6.0.0

- **Date navigation on Daily Tracker** — ◀ / date / ▶ row at the top of the Today tab. Tap the date to open a native calendar picker. ← / → arrow keys work on desktop. Future dates are blocked. Badge shows TODAY / YESTERDAY / —N DAYS AGO. All view, add, and delete operations apply to the selected date.
- **Fibre bar** — 5th macro bar below the 4 rings. Target: 30 g/day. Red < 20 g · Gold 20–29 g · Green ≥ 30 g.
- **Notes field** — optional textarea in the portion-adjust flow. Notes display in italic under each log entry.
- **P0 pantry + grocery fix** — idempotent v2 → v3 schema migration renames the old fields (`cat → category`, `item → name`, `qty → quantity`, `checked → done`). Runs on load and persists to Drive.
- **CLAUDE_MODEL const** — model string extracted to a single constant; all 3 AI call sites use it.

## What was in v5.0

- **Food library** — ~75 pre-seeded foods keyed to sir's repertoire, plus standard staples. All macros stored per 100 g so portions scale cleanly.
- **Search-first food picker** — autofocused search; results rank by text match then usage history.
- **Portion adjustment** — ±25 g buttons, quick-portion presets, direct entry. Macros recalculate live.
- **AI meal scan** — photograph a plate → Claude vision → identified foods with estimated grams. ~1¢/scan.
- **AI pantry scan** — single-item or bulk-shelf mode. Adds items directly to pantry.
- **MFP import** — Settings → Import MFP History. Upload PDF export; Claude extracts foods and dedupes.
- **Manual entry** — name, brand, reference portion, macros; app back-calculates per 100 g.
- **Drive sync** — OAuth, bi-directional, debounced 1.2 s save.

## Schema versions

| Version | When | Notes |
|---------|------|-------|
| v1 | original | bare logs/grocery/pantry |
| v2 | v5 | adds `foods` array |
| v3 | v6 | renames pantry/grocery fields; adds `schema_version: 3` |

Migrations are idempotent and run automatically on load.

## Deployment

```bash
git add index.html README.md
git commit -m "vX.Y.Z: <summary>"
git push origin main
# GitHub Pages rebuilds in ~30 sec
```

On phone: hard-refresh the PWA, or remove and re-add to home screen if it serves stale cache.

## Phases remaining

- **Phase 2** — Recipe Builder (log-once / save-to-library / save-to-library+Drive)
- **Phase 3** — Weight log, 7-day rolling average, 30-day sparkline
- **Phase 4** — Share Day (plain text + Web Share API)
- **Phase 5** — Polish: swipe-to-delete, toast for missing API key, Today quick-jump

## Cost notes

API calls use the key stored in localStorage (`ant_api_key`). Pantry scan ~1¢, meal scan ~1¢, MFP import 5–15¢ one-time. Drive sync, food library, and Open Food Facts search are free.
