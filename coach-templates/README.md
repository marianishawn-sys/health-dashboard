# Coach drop-box templates

These are **reference templates** for the files the Health Concierge Orchestrator (Claude.ai)
writes to drive the app. They are inert here — the app never reads this folder.

## How to use one
1. Copy a template's **contents**.
2. Create a file with the **same `coach-*.json` name** directly in the Drive folder
   **`My Drive / 04 - Personal / Health Concierge`** (the folder that contains `dashboard-data.json`).
3. Edit the values. Keep the top-level `"type"` field exactly as shown.
4. On the next app open, the app ingests the file, merges it into `dashboard-data.json`, and **deletes** it.

> ⚠️ Do **not** put these templates (or any `coach-*.json`) loose in the Health Concierge folder
> unless you mean for the app to ingest and delete them.

| File | `type` | Effect | Dedupe / replace |
|------|--------|--------|------------------|
| `coach-additions.json` | `additions` | Adds foods to the food library | Skips a food whose name already exists |
| `coach-recipes.json`   | `recipes`   | Adds recipes (+ creates missing ingredients) | Skips a recipe whose name already exists |
| `coach-mealplan.json`  | `mealplan`  | Schedules meals (resolves `recipeName` → recipe) | Skips an exact date+slot+recipe duplicate; ignores unresolvable recipes |
| `coach-grocery.json`   | `grocery`   | Adds items to the shopping list (`source:"coach"`) | Skips a coach item already on the list and not checked off |
| `coach-deals.json`     | `deals`     | **Replaces** the Deals tab "Active Deals" list | Full replace each time |

Ingest order within one load: **additions → recipes → mealplan** (so a recipe and a meal plan
referencing it can arrive together). Grocery and deals are independent.

See `HEALTH-CONCIERGE-ORCHESTRATOR-BRIEF.md` (in the Health Concierge folder) for the full contract.
