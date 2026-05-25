# Nutrition Concierge — v5.0 (patched, deployable)

Drop-in upgrade. Replace `index.html` and `manifest.json` in the GitHub repo; PWA reloads in ~30 seconds. No Google Cloud Console reauth required.

## What's in v5

- **Food library** — ~75 pre-seeded foods keyed to your repertoire: venison stew, NY strip, free-run eggs, Grana Padano, Parmigiano Reggiano, sourdough, rainbow trout, Liberté Greek yogurt, oranges, kiwis, plus standard staples. All macros stored per 100 g so portions scale cleanly.
- **Search-first food picker** — `+ ADD FOOD` opens an autofocused search. Results rank by text match then by your usage history. Most-used foods float to the top over time.
- **Portion adjustment** — pick a food, set grams via ±25 g buttons, quick-portion presets, or direct entry. Macros recalculate live.
- **AI meal scan** — point camera at a plate, sends to Claude Sonnet 4 with vision, returns identified foods with estimated grams. Each flows through portion-adjust so you can correct before logging. ~1¢ per scan.
- **MFP import** — Settings → IMPORT MFP HISTORY. Upload a MyFitnessPal CSV/JSON export (the real one, not the Printable Diary PDF). Claude extracts foods, you review and select. Dedups against existing entries.
- **Manual entry** — for anything the library doesn't have. Enter name, brand, reference portion, and macros for that portion; the app back-calculates per-100g.

## What changed from the previous v5 draft

Two bugs patched, both required for the build to work at all:

1. **`CLIENT_ID`** — restored to the real Google OAuth client (`256298678690-…`). The previous draft had a fabricated ID that would fail sign-in immediately.
2. **Folder lookup** — `drive.file` scope can only see files the app itself created, so searching for "Health Concierge" by name would silently create a new empty folder and orphan your existing v4 data. Replaced with hardcoded `DRIVE_FOLDER_ID` for `04 - Personal / Health Concierge`, plus a `KNOWN_DATA_FILE_ID` direct-fetch fallback so your existing `dashboard-data.json` from v4 is found reliably.

Net effect: v5 reads your existing v4 file, migrates it from schema v1 → v2 (adds the `foods` array, preserves logs/grocery/pantry intact), and writes the migrated version back on first load.

## Schema migration

v4 data (schema v1) auto-migrates to v2 on first load. Old log entries (no `foodId`, no `grams`) coexist with new ones — they just won't be editable via portion-adjust, only deletable.

## Deployment

1. Replace `index.html` in the GitHub repo
2. Replace `manifest.json` in the GitHub repo
3. Commit, push, wait ~30 seconds for GitHub Pages rebuild
4. On phone: pull-to-refresh the PWA, or remove and re-add to home screen if it caches stale

## MFP import path (when Cowork export lands)

The Printable Diary PDF in Drive is numeric-only (food names stripped during print rendering) so it's not usable as-is. The right path:

- **If you use Cowork to extract**: drop the extracted CSV/JSON in `04 - Personal / Health Concierge /`. Settings → IMPORT MFP HISTORY → pick the file. Ideal shape: `food_name, brand, grams, calories, protein, carbs, fat`. Looser shapes work too — the importer normalizes.
- **If you go back to MFP directly**: myfitnesspal.com → Settings → Account Settings → Download Personal Data Archive → Request Data. CSV arrives by email within 24 hours; food names preserved.

## Cost notes

API calls use your existing key in localStorage. Pantry scan ~1¢, meal scan ~1¢, MFP import 5–15¢ one-time depending on size. Drive sync and the food library are free.
