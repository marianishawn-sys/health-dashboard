# Nutrition Concierge — v7.0.0

Single-file React PWA. No build step. Edit `index.html`, push, GitHub Pages rebuilds in ~30 seconds.

**Live:** https://marianishawn-sys.github.io/health-dashboard/

## What's in v7.0.x — Closed-loop Inventory System

### M1 (v7.0.0) — Ingredient Registry + Pantry Inventory
- **Ingredient registry** (`ingredients[]`) — canonical items with `id`, `name`, `defaultUnit`, `category`. All pantry entries and (future) recipe ingredients reference registry by `itemId` — no free-text name matching at runtime.
- **Schema v4 migration** — idempotent, runs on load. Preserves existing pantry items, name-matches to seed registry, merges 26 seed inventory entries for first-time installs.
- **25 seeded ingredients** — Freezer (strip loin, chicken thigh, chicken breast, venison, pickerel, shrimp, BBQ sausage, turkey breast, round roast, beef ribs, ground bison), Fridge (eggs, bacon, Greek yogurt, cottage cheese, Grana Padano, Friulano, cheddar, mozzarella, beef stock, sweet potato), Pantry (EVOO, pasta, olives, honey, sourdough starter).
- **New pantry UI** — grouped by Freezer / Fridge / Pantry. Two tracking modes:
  - **Count** — inline ±stepper with unit. Border turns 🟡 yellow when ≤ par level, 🔴 red at 0.
  - **State** — have / low / out pill toggles. Border reflects state.
- **Expiry tracking** — per-item date picker with N/A checkbox. Items expiring within 3 days show yellow border; expired items show red border.
- **"Never flag" items** — e.g. sourdough starter gets no status colour, no expiry prompt.
- **Show flagged** toggle — surfaces all 🟡/🔴 items regardless of scroll position.
- **Pantry scan + manual add** — AI scan links to registry by name match; manual add creates registry entry + pantry item in one step.
- **Unit conversion helpers** — `toBaseUnit`/`fromBaseUnit` for weight/volume/count families (used in M4 demand calc).

## Roadmap

- **M2** — Grocery list revamp: auto-adds 🟡/🔴 items, source badges (low/plan/coach/manual), "Done shopping" flow
- **M3** — Recipe library: structured recipes referencing ingredient registry, AI text parser
- **M4** — Meal plan builder in Grocery tab, demand calculation, shortfall auto-added to grocery list
- **M5** — Coach ingest (drain-and-delete from Drive), upgrade Drive scope to `drive`

## What was in v6.2.x

- **Internet macro search** — Open Food Facts search bar at the top of Manual Entry. Type a food name, tap 🔍 (or press Enter), see up to 5 results with macros per 100g. Tap a result to auto-fill all fields. Results cached in localStorage. Free, no API key.
- **Fibre field on Manual Entry** — optional fibre (g) input alongside the 4 macro fields. Auto-populated from search results.
- **Meal scan: log all items** — 2+ selected items are batch-logged at scanned grams in one tap. Single item still goes to Adjust Portion. Each scan row has a 🔍 button to re-fetch macros from Open Food Facts after correcting the name.
- **Fibre tracking fixed** — `scaleMacros` now carries fibre through to log entries. Divider added between macro summary and meal sections on Today tab.
- **Fibre backfilled into food library** — all 75 pre-seeded foods now have accurate `per100g.fibre` values (USDA/CFIA data). Auto-migration runs on load and persists to Drive — no action required.

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
| v4 | v7 M1 | adds `ingredients[]` registry; pantry entries get `itemId`, `trackingType`, `quantity`/`state`, `parLevel`, `expiry`, `expiryNA` |

Migrations are idempotent and run automatically on load.

## Deployment

```bash
git add index.html README.md
git commit -m "vX.Y.Z: <summary>"
git push origin main
# GitHub Pages rebuilds in ~30 sec
```

On phone: hard-refresh the PWA, or remove and re-add to home screen if it serves stale cache.

## Cost notes

API calls use the key stored in localStorage (`ant_api_key`). Pantry scan ~1¢, meal scan ~1¢, MFP import 5–15¢ one-time. Drive sync, food library, and Open Food Facts search are free.
