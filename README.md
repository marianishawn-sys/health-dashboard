# Nutrition Concierge — v7.14.1

Single-file React PWA. No build step. Edit `index.html`, push, GitHub Pages rebuilds in ~30 seconds.

**Live:** https://marianishawn-sys.github.io/health-dashboard/

---

## v7 — Closed-Loop Inventory + Recipes + Grocery System

### M1 · v7.0.0 — Ingredient Registry + Pantry Inventory
- **Ingredient registry** (`ingredients[]`) — canonical items with `id`, `name`, `defaultUnit`, `category`. All pantry entries and recipe ingredients reference registry by `itemId`.
- **Schema v4 migration** — idempotent. Preserves existing pantry items, name-matches to seed registry, merges 26 seed inventory entries for first-time installs.
- **25 seeded ingredients** — Freezer, Fridge, and Pantry staples (strip loin, chicken, eggs, EVOO, etc.)
- **New Pantry tab UI** — grouped by Freezer / Fridge / Pantry. Two tracking modes:
  - **Count** — inline ±stepper. Border turns 🟡 at ≤ par level, 🔴 at 0.
  - **State** — have / low / out pill toggles.
- **Expiry tracking** — per-item date picker + N/A checkbox. Items expiring within 3 days → yellow; expired → red.
- **"Never flag"** — items like sourdough starter get no status colour.
- **Show Flagged** toggle — surfaces all at-risk items.
- **Pantry scan + manual add** — AI scan links to registry; manual add creates registry entry + pantry item.
- **Unit conversion helpers** — `toBaseUnit`/`fromBaseUnit` for weight/volume/count families.

### M2 · v7.1.0 — Grocery List Revamp
- **groceryList schema** replaces old `grocery`. Each item has `source: "manual"|"low"|"plan"|"coach"`.
- **NEEDS RESTOCKING section** — auto-derived from 🟡/🔴 pantry items; shows OUT/LOW badge; "+ LIST" button adds to shopping list as `source:"low"`.
- **Shopping list** — checkboxes, optional qty+unit, source badges (LOW/PLAN/COACH).
- **Done section** — checked-off items at 55% opacity.
- **DONE SHOPPING** — clears all checked items.
- **Migration** — `migrateGroceryList` renames old `grocery` → `groceryList` with `source:"manual"`.

### M3 · v7.2.0 — Recipe Library
- **RECIPES tab** added between GROCERY and PANTRY.
- **Recipe schema** — `{ id, name, servings, ingredients[{itemId, quantity, unit}], instructions, createdAt }`.
- **Recipe editor** — modal with ingredient search (live dropdown from registry), per-row qty+unit, instructions.
- **Collapse/expand** recipe cards showing ingredient count and servings.
- **AI Recipe Parser** — paste free-text recipe → Claude extracts name/servings/ingredients/instructions, fuzzy-matches to ingredient registry, creates new registry entries for unknowns, opens editor for review.

### M4 · v7.3.0 — Meal Plan Builder
- **MEAL PLAN section** embedded in Grocery tab (collapsible).
- **7-day rolling calendar** — each day has a searchable recipe picker and adjustable servings count.
- **BUILD SHOPPING LIST** — demand calculation:
  1. Sums ingredient quantities across all planned meals (scaled by servings ratio).
  2. Subtracts pantry count-tracked stock (same unit family only).
  3. State-tracked items: `"have"` = sufficient; `"low"`/`"out"` = left in NEEDS RESTOCKING.
  4. Replaces all previous `source:"plan"` grocery entries with fresh shortfall list.

### v7.14.1 — Scanned items use the label's serving size (not 100g)
- When a nutrition label/barcode is scanned, the label's **serving size** becomes the default portion in both the pantry and the Today food list.
- **MealScan** (Today tab): prompt reads `servingG` + `servingUnit` from a visible label; the food it builds defaults `PortionAdjust` to "1 serving (Xg)" instead of the plate-estimate/100g. No label → unchanged (visible-grams estimate).
- **PantryScan**: `servingG` is now always required and explicitly read from the Nutrition Facts serving size (e.g. "Per 40g" → 40), not left null.
- `addFoodToPantry` carries `servingUnit` through when a scanned food is added.
- **Data sweep (2026-06-23):** all 89 pantry items + 3 loggable library ingredients backfilled with real serving sizes (count units like apple/patty/drumstick where natural); fixed 3 broken servings (grated Grana Padano 1064g→5g, coleslaw 400→85, pickles 500→30). Then a **curated macro backfill** gave 34 common recipe ingredients real macros + servings (sour cream, heavy cream, tomato paste, ghee, kidney beans, pecans, chia, etc.) — searchable foods went ~90→124. The remaining ~477 macro-less recipe ingredients (duplicates + junk fragments) were left invisible-in-search on purpose. Backups: `dashboard-data.backup-2026-06-23T*.json` in the Health Concierge folder.

### v7.14.0 — Pantry decrements on diary log + macro lookup on manual add
- Logging a **pantry-sourced food from the Today tab** now decrements that pantry item's stock (count-tracked items), matching the Pantry tab's "Add to Diary". Pantry-derived foods carry `pantryItemId`; older logged copies are detected by their `ing_`-prefixed id. `gramsPerUnit` hoisted to module scope (shared by `PantryTab` + `useFood`).
- Manual **"Add to pantry"** has a **🔎 LOOK UP MACROS** button — reuses macros from the food library/ingredients if known, else an AI lookup — and saves `per100g` + serving size onto the new item.

### v7.13.1 — HOTFIX: pin CDN versions (Babel 8 broke everything)
- The head loaded `@babel/standalone` (and React) **unpinned**, so unpkg auto-served the just-released **Babel 8.0.0**, whose in-browser transform throws "Cannot use import statement outside a module" → React never mounts → **blank dark page on all devices at once**. No code change caused it.
- Pinned to **react@18.3.1, react-dom@18.3.1, @babel/standalone@7.26.4**. **Never unpin** — an upstream release otherwise blanks the app with no warning.

### v7.13.0 — Coach can drive groceries + deals
- Two new coach drop-box file types in `ingestCoachFiles`: **`coach-grocery.json`** (adds shopping-list items tagged `source:"coach"`, links to ingredient by exact name, dedupes unchecked coach items) and **`coach-deals.json`** (replaces the Deals tab "Active Deals" list with `{store,item,price,note,expires}` entries + `updatedAt`).
- **Deals tab is now data-driven** (`DealsTab` renders `data.deals`); the static placeholder only shows when no deals are loaded.
- Added the **Orchestrator brief** (`HEALTH-CONCIERGE-ORCHESTRATOR-BRIEF.md` in the Health Concierge folder) and copy-paste **templates** (`coach-templates/`). Corrected the documented coach folder (Health Concierge folder, not `macro-log`).

### v7.12.0 — Add to Diary from each recipe
- Expanded recipe cards get an **ADD TO DIARY** panel: date picker, meal selector (Bre/Lun/Din/Sna), servings input, and a live "will log" macro preview.
- `addRecipeToDiary` logs `perServing × servings` to `data.logs[date][meal]` (displayQty/displayUnit = "N servings"), saves immediately, shows a green confirmation toast. Only shown for recipes that have `perServing`.

### v7.11.1 — Pantry scan captures macros
- The pantry-scan prompt only asked for name/category/quantity, so scanned items had **no per100g** (most of the pantry ended up macro-less). The prompt (single + bulk) now requires `per100g {cal,protein,carbs,fat,fibre}` plus optional `servingG`/`servingUnit` — read the Nutrition Facts panel if visible, else typical values. `max_tokens` 2000→4000.
- `handleScanResult` stores `per100g` (+ serving info) on new ingredients and backfills macros onto an existing matched ingredient that lacks them. Scan review shows the captured per-100g line.
- One-time data backfill: standard per-100g macros written to all 53 existing pantry items that were missing them (meats, dairy, produce, full condiment/sauce set), with natural serving units where obvious. Written to the Drive data file with a backup.

### v7.11.0 — Log by natural unit + token auto-refresh
- **Drive token auto-refresh:** the OAuth access token expires ~1h into a session; previously every save then failed silently (red ERROR, data loss). `driveFetch` now silently re-requests a token on 401 and retries once (`refreshToken` via the GIS callback). Fixes the recurring "didn't save" episodes.
- **PortionAdjust reworked** — **BY ‹UNIT› / BY WEIGHT** toggle:
  - Count mode logs 1/2/3 of a named unit. The unit + grams-per-unit are derived from `servingUnit`/`refPortion` (e.g. "Free-run eggs" 50 g → "large egg"), **editable inline** ("1 stick = 12 g") and **persisted to the food** (`servingG`/`servingUnit`/`refPortion`) so it's the default next time.
  - Defaults to count only when there's a real named unit; weight-natural foods (Skyr/honey) default to weight. Both always toggleable.
  - `useFood` gains an `opts` arg `{displayQty, displayUnit, servingDef, preferredUnit}`.
- **Clearable inputs:** portion fields are string state (`type=text inputMode=decimal`), clearable/retypable; clamp on blur, not per keystroke.
- **EditEntryModal:** count-unit entries (e.g. "large eggs") now edit in grams instead of mis-treating the count as grams.

### v7.10.2 — Scan/recipe matching fix (data corruption)
- Pantry-scan/recipe ingredient matching was fuzzy on first-word substring across all registry names → a scanned "Organic Medjool Dates" hijacked "Organic chicken drumsticks" quantity. Now **exact (case-insensitive) name match only** in the pantry scan, coach ingest, and AI recipe parser.

### v7.10.1 — Immediate pantry saves + toast
- Pantry scan/manual adds save immediately (`saveData(newData, immediate=true)`) with a green confirmation toast.

### v7.10.0 — API key syncs across devices
- The Anthropic API key now syncs through the Drive data file instead of being per-device localStorage only. Enter it once on any device → others adopt it on next load.
- `saveApiKey()` writes the key into `data.apiKey` (→ Drive); `loadData()` adopts `data.apiKey` from Drive, or bootstraps by pushing this device's localStorage key up if Drive has none yet.
- **Security tradeoff (intentional):** the key now lives in `dashboard-data.json` on Google Drive in plaintext — same trust boundary as the rest of the synced data. Scan/AI requests still send the key only to the Anthropic endpoint. (This relaxes the earlier "key never leaves the device" rule by explicit user choice.)
- A version string (`VERSION`) shows next to CONCIERGE in the header for fresh-build verification.

### v7.9.1–v7.9.2 — Clearer AI error messages
- Meal scan maps API failures to actionable text: 401 → re-paste key in Settings; 400+credit → low balance; 429 → rate limited; 404 → model unavailable; and "Failed to fetch" → network/extension/VPN block (not an auth error), with troubleshooting hints.

### v7.9.0 — Add scanned/library foods to the pantry
- **From a meal scan** (Diary → + ADD FOOD → 📷 SCAN MEAL → review): select items and tap **📦 ADD N TO PANTRY**. Shows "Added N to pantry ✓" / "Already in pantry".
- **From the food search list**: each previously-logged result has a 📦 button (turns ✓ once added) beside the 🗑 delete.
- `addFoodToPantry(foods)` creates/links an ingredient (with the food's `per100g` macros + serving size) and a count-tracked pantry entry (qty 1), skipping items already present. Threaded App → FoodPicker → MealScan.
- Note: editing a pantry item's macros already exists (item edit modal → MACROS PER 100g → SAVE CHANGES) and was left unchanged.

### v7.8.0 — Pantry "Add to Diary" with portion adjuster
- Tap a pantry item → **ADD TO DIARY**: pick a date + meal, then **SET PORTION →** opens the same portion adjuster used for normal foods (count steppers for egg/portion items, grams for the rest, with a live WILL-LOG macro preview).
- Confirming logs the food to the chosen day/meal **and** decrements pantry stock by the amount used (count-tracked items; stock decrement = logged grams ÷ grams-per-unit).
- Requires the item to have per-100g macros set (the modal prompts if missing).

### v7.7.2 — Food search reorder + delete
- Search result priority: **pantry items (🫙) → previously logged foods → pantry stubs → internet/AI fallback** (fallback only fires when nothing local matches).
- Each previously-logged result has a 🗑 button (with confirm) to remove it from `data.foods`, so duplicate entries stop appearing in future searches. Pantry rows stay managed in the Pantry tab.

### v7.7.1 — Version number in header
- `VERSION` constant shown next to CONCIERGE in the header, so a fresh build is instantly verifiable (cache vs code).

### v7.7.0 — Add to Diary from pantry (initial)
- First version of pantry → diary logging (inline quantity; superseded by the v7.8.0 portion adjuster).

### v7.6.1 — CSV import: no API key needed
- The in-app import hit a 401 on the AI ingredient lookup. Replaced the live Claude call with a built-in per-100g nutrition table (`PER_GRAM_MACRO_TABLE`, keyword-matched) covering every ingredient in the 9 "1g=1serv" bulk recipes (venison, beef, chicken, shrimp, tuna, avocado, sauces, dairy, produce, oils, flour, etc.).
- Import now runs fully offline/local — no internet, no API key — and the app saves recipes via its normal idempotent Drive write. Updated the import card copy accordingly.

### v7.6.0 — MFP Recipe CSV Import (rebuilt)
- **IMPORT MFP RECIPE CSV** rebuilt for the full ~90-recipe export. No Open Food Facts lookups for normal recipes — MFP already stores accurate per-serving macros on every row, so import is near-instant.
- **Serving labels parsed from recipe names** — `(1 Cup Servings)`, `(8 Oz Servings)`, `(2tbsp Servings)`, `(per gram)`, `(1/12 of Pie)`, etc. are stripped from the display name and stored as `recipe.servingLabel`. Name encoding artifacts (`�`, nbsp, curly quotes) are cleaned.
- **"1g=1serv" bulk recipes** (venison stew, taco meat, curries, etc.): MFP's per-serving macros round to ~0, so they are recomputed. Each non-trivial ingredient's per-100g macros are looked up via **one batched Claude call** (OFF is unreliable for whole foods like venison/shrimp), the batch total is summed by converting each ingredient quantity to grams, then divided by total grams. Serving is preserved as provided — **1 g = 1 serving** (`servings` = total grams) — with per-gram macros kept to 2–3 decimals so they are never 0. Requires an API key.
- **Ingredient quantity → grams** converter (`toGrams`) handles g/kg/ml/L/cup/tbsp/tsp/oz/lb plus count units (egg, clove, avocado, onion, etc.).
- Recipes that already exist (by cleaned name) are skipped. Removed the now-unused `fetchOFFSingle` helper.

### v7.5.5 — Auto internet search; AI fallback
- When local + pantry search is empty (3+ chars), Open Food Facts fires automatically (600 ms debounce). If it returns nothing, a **🤖 ASK AI** button appears for an exact lookup.

### v7.5.4 — AI food lookup
- 🤖 ASK AI button in the food picker — single Claude call returns per-100g macros for any food (fixes fresh-produce gaps in Open Food Facts).

### v7.5.3 — Internet food search fallback
- 🌐 internet search (Open Food Facts) when local results are empty.

### v7.5.2 — Count-mode portion adjuster
- Count-based pantry items (eggs, bacon strips, steaks, fillets, sausages, racks, potatoes) get a count stepper ("HOW MANY EGGS?", −1/+1, 1–4 presets); weight items keep grams. `servingUnit` added to seeds + backfilled.

### v7.5.1 — Heart & Soil macros
- Name-based backfill for Heart & Soil Whey Chocolate Sea Salt (per 100g: 372 cal / 58.1P / 30.2C / 2.3F / 2.3 fibre, 43 g serving).

### v7.5.0 — Pantry Macros Backfill
- All 24 seed pantry ingredients now carry `per100g` macros and `servingG` (standard serving size) directly in `SEED_INGREDIENTS`.
- `backfillIngredientMacros` migration runs on every load: for each stored ingredient matching a seed ID that lacks macros, copies `per100g` + `servingG` from seed data. Idempotent. Triggers a Drive save when changes are made.
- Serving sizes: strip loin 170g, chicken thigh/breast 150g, venison 170g, pickerel 150g, shrimp 85g, BBQ sausage 85g, turkey 150g, round roast 170g, beef ribs 280g, bison 113g, eggs 50g, bacon 28g, greek yogurt 170g, cottage cheese 113g, cheeses 30g, beef stock 240g, sweet potato 150g, EVOO 14g, pasta 85g, olives 30g, honey 21g.

### v7.4.9 — Serving Size Field for Pantry Items
- Pantry item edit modal: new **Serving size (g)** field below the macro grid. Saved as `ing.servingG`.
- FoodPicker: pantry foods with `servingG` open the portion adjuster pre-set to that serving instead of defaulting to 100g.

### v7.4.8 — Macros on Pantry Items
- Pantry item edit modal: new **MACROS PER 100g** section (Cal / Pro / Crb / Fat / Fib) — optional, persisted to `ing.per100g`.
- FoodPicker: pantry ingredients with macros show as full loggable results with a 🫙 PANTRY badge; those without show as stubs with a "Add macros to log" prompt.
- Logged pantry-ingredient foods are added to `data.foods` via the normal `useFood` pipeline.

### v7.4.7 — Pantry Items in Food Search
- Food picker now searches `data.ingredients` (pantry registry) alongside `data.foods`.
- Typing 2+ characters surfaces pantry items that have no food library entry as stub rows.
- Tapping a stub opens Manual Entry pre-filled with the ingredient name.
- `ManualEntry` gains `initialName` prop.

### v7.4.6 — Sticky Headers
- **App header** (`CONCIERGE / date / HIGH·LOW`) is now `position:sticky` — stays pinned across all tabs when scrolling.
- **Today tab** macro/fibre card + date nav pinned below the app header; meal log scrolls underneath.
- **Pantry tab** SCAN/BULK/ADD buttons, FLAGGED FIRST toggle, and INVENTORY label pinned; inventory items scroll underneath.

### v7.4.5 — Sticky Macro Card (Today Tab)
- Date nav + macro/fibre summary + MEALS section label are now a sticky block pinned to the top of the viewport on the Today tab. Meal entries scroll beneath them.

### v7.4.4 — Section Dividers + Fibre Auto-Fetch
- Section dividers replaced with labeled flex rows (`── MEALS ──` / `── INVENTORY ──`) — visible regardless of device rendering quirks.
- On session start, a background fetch populates fibre data from Open Food Facts for the top 10 most-used foods that are missing it. Combined with the retroactive fibre lookup in `sumLogged`, historical log entries now show fibre without re-logging.

### v7.4.3 — Date Fix + Fibre Retroactive Lookup
- **Date bug**: `isoToday()` was using `toISOString()` (UTC), causing the app to show tomorrow's empty log after ~7–8 PM. Fixed to use local year/month/day.
- **Fibre retroactive lookup**: `sumLogged` now accepts the food library as a third argument. For log entries where `fibre` is 0 but a `foodId` exists, fibre is computed on the fly from the current food library — fixing all historical entries without touching stored data.
- **Fibre in MealScan**: AI prompt updated to include `fibre` in the JSON spec; OFF re-fetch (`🔍`) now also returns fibre.

### v7.4.2 — Pantry Item Edit Modal + Fibre in Scan Review
- Tap any pantry item name to open a bottom-sheet edit modal (name, location, tracking mode, unit, par level). SAVE CHANGES updates both the ingredient registry and the pantry entry.
- MealScan review grid now shows a FIB/100g field (grid restructured to 3 columns × 2 rows).

### v7.4.1 — Pantry Quantity Editing Fixes
- **iOS decimal input** — Qty/par fields changed from `type="number"` to `type="text" inputMode="decimal"`; avoids WebKit controlled-input bug.
- **Larger stepper buttons** — −/+ buttons enlarged 28→34 px for easier mobile tap.
- **Tracking-type toggle** — Every pantry item now shows QTY / STATUS chips in its sub-row. Tap to switch any item between count mode (stepper) and status mode (HAVE/LOW/OUT) at any time.
- **Inline qty edit** — Tapping the quantity number opens a direct-edit field; shows a visible border so it reads as a button. "Done" key (iOS) closes it.
- **Null qty** displayed as 0 instead of blank for count items.
- **Add-form unit reset** — Unit field resets to "portions" after submitting the manual add form.

### M5 · v7.4.0 — Coach Ingest
- **Drive scope** upgraded `drive.file` → `drive` (one-time re-consent on next sign-in).
- **Drain-and-delete** pattern: on every load, searches Drive folder for `coach-*.json` files, ingests, deletes each.
- **Supported file types** (created by Claude.ai via Google Workspace MCP):

| File | Content |
|------|---------|
| `coach-additions.json` | `{ type:"additions", foods:[{name, brand, per100g:{cal,protein,carbs,fat,fibre}}] }` |
| `coach-recipes.json` | `{ type:"recipes", recipes:[{name, servings, ingredients:[{itemName, quantity, unit}], instructions}] }` |
| `coach-mealplan.json` | `{ type:"mealplan", entries:[{date, slot, recipeName, servings}] }` |
| `coach-grocery.json` _(v7.13)_ | `{ type:"grocery", items:[{name, quantity?, unit?}] }` → shopping list, source `coach` |
| `coach-deals.json` _(v7.13)_ | `{ type:"deals", updatedAt?, deals:[{store?, item, price?, note?, expires?}] }` → Deals tab |

- Files go in the **`04 - Personal / Health Concierge`** folder (with `dashboard-data.json`), not `macro-log`. Errors during ingest leave the file in place for retry on next load. Full contract: `HEALTH-CONCIERGE-ORCHESTRATOR-BRIEF.md`; templates: `health-dashboard/coach-templates/`.

---

## What was in v6.2.x

- **Internet macro search** — Open Food Facts search bar at the top of Manual Entry.
- **Fibre field** on Manual Entry — auto-populated from search results.
- **Meal scan: log all items** — batch-log 2+ items. Per-row 🔍 re-fetch button.
- **Fibre tracking** — `scaleMacros` carries fibre through. Divider on Today tab.
- **Fibre backfilled** into all 75 seeded foods.

## What was in v6.1.x

- **Edit + delete log entries** — tap entry → edit modal. 5-second undo toast.
- **Multi-unit input** — g / oz / lb. Unit preference per food.
- **Dual AI scan buttons** — 📷 CAMERA + 🖼️ UPLOAD.
- **Date picker fix**.

## What was in v6.0.0

- **Date navigation** on Daily Tracker — ◀/▶ + calendar picker. Future dates blocked.
- **Fibre bar** — 30 g/day target.
- **Notes field** on log entries.
- **P0 pantry + grocery fix** — v2→v3 migration.
- **CLAUDE_MODEL const**.

## What was in v5.0

- Food library (~75 seeded foods), search-first picker, portion adjustment, AI meal scan, AI pantry scan, MFP import, manual entry, Drive sync.

---

## Schema versions

| Version | When | Notes |
|---------|------|-------|
| v1 | original | bare logs/grocery/pantry |
| v2 | v5 | adds `foods` array |
| v3 | v6 | renames pantry/grocery fields; `schema_version: 3` |
| v4 | v7 M1 | adds `ingredients[]` registry; pantry entries get `itemId`, `trackingType`, `quantity`/`state`, `parLevel`, `expiry` |
| v4b | v7 M2 | renames `grocery` → `groceryList` with `source` field |

Migrations are idempotent and run automatically on load.

---

## Coach file format (for Claude.ai / the Health Concierge Orchestrator)

The coach drives the app by writing `coach-*.json` files into the Google Drive folder
**`04 - Personal / Health Concierge`** — the folder that contains `dashboard-data.json` (NOT the
`macro-log` subfolder). On every load the app **drains and deletes** them: reads each, merges into
`dashboard-data.json`, deletes the file. The coach **reads** `dashboard-data.json` to see pantry/logs/recipes/etc.

Five file types (each needs the correct top-level `"type"`); ingest order per load is additions → recipes → mealplan:

| File | `type` | Effect |
|------|--------|--------|
| `coach-additions.json` | `additions` | Add foods to library. `{ foods:[{name, brand?, per100g:{cal,protein,carbs,fat,fibre}}] }`. Skips existing names. |
| `coach-recipes.json` | `recipes` | Add recipes. `{ recipes:[{name, servings, ingredients:[{itemName, quantity, unit}], instructions}] }`. Ingredients matched to registry by exact name. Skips existing names. |
| `coach-mealplan.json` | `mealplan` | Schedule meals. `{ entries:[{date, slot, recipeName, servings}] }`. Resolves `recipeName`→recipe; skips unresolvable / exact dupes. |
| `coach-grocery.json` | `grocery` | Add shopping-list items (tagged COACH). `{ items:[{name, quantity?, unit?}] }`. Skips a coach item already on the list & unchecked. |
| `coach-deals.json` | `deals` | **Replace** the Deals tab list. `{ updatedAt?, deals:[{store?, item, price?, note?, expires?}] }`. |

Full contract: **`HEALTH-CONCIERGE-ORCHESTRATOR-BRIEF.md`** (in the Health Concierge folder).
Copy-paste templates: **`health-dashboard/coach-templates/`**.

> The pantry is read-only for the coach (managed in-app). Groceries are also built in-app from the
> meal plan minus pantry stock; `coach-grocery.json` is for extras the demand calc won't catch.

---

## Deployment

```bash
git add index.html README.md
git commit -m "vX.Y.Z: <summary>"
git push origin main
# GitHub Pages rebuilds in ~30 sec
```

On phone: hard-refresh the PWA (Ctrl+Shift+R desktop; clear site data on mobile if needed).

## Cost notes

API calls use the Anthropic key stored in `ant_api_key` (localStorage) and synced via `data.apiKey` in the Drive data file (v7.10.0). Meal scan ~1¢, pantry scan ~1¢, recipe parse ~0.5¢, MFP import 5–15¢ one-time. Drive sync, food library, Open Food Facts, and coach ingest are free.
