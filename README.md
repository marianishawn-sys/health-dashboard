# Nutrition Concierge — v7.4.1

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

- Errors during ingest leave the file in place for retry on next load.

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

## Coach file format (for Claude.ai)

Place files in the Google Drive folder `macro-log` (same folder as `dashboard-data.json`). The dashboard reads and deletes them on next load.

**coach-additions.json** — add foods to the library:
```json
{
  "type": "additions",
  "foods": [
    {
      "name": "Grass-Fed Beef Tallow",
      "brand": "",
      "per100g": { "cal": 902, "protein": 0, "carbs": 0, "fat": 100, "fibre": 0 }
    }
  ]
}
```

**coach-recipes.json** — add recipes (ingredients by name, matched to registry):
```json
{
  "type": "recipes",
  "recipes": [
    {
      "name": "BBQ Strip Loin",
      "servings": 2,
      "ingredients": [
        { "itemName": "Strip Loin", "quantity": 400, "unit": "g" },
        { "itemName": "EVOO", "quantity": 20, "unit": "ml" }
      ],
      "instructions": "Season with salt. Grill 4 min/side."
    }
  ]
}
```

**coach-mealplan.json** — inject a week's meal plan (recipes resolved by name):
```json
{
  "type": "mealplan",
  "entries": [
    { "date": "2026-06-02", "slot": "dinner", "recipeName": "BBQ Strip Loin", "servings": 2 },
    { "date": "2026-06-03", "slot": "dinner", "recipeName": "Chicken Bowl", "servings": 4 }
  ]
}
```

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

API calls use `ant_api_key` in localStorage. Meal scan ~1¢, pantry scan ~1¢, recipe parse ~0.5¢, MFP import 5–15¢ one-time. Drive sync, food library, Open Food Facts, and coach ingest are free.
