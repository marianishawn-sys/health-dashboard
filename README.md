Nutrition Concierge — v4.0
Personal nutrition dashboard for sir. Drive-synced. AI-powered pantry scanning.
---
What's New in v4
📷 Add Item to Pantry via Camera — point at any product, AI reads the label, identifies category, captures quantity. Tap confirm, done.
📦 Bulk Pantry Scan — one photo of an open freezer/fridge/pantry shelf, AI identifies every visible item, you select which to add. Designed for post-Costco unpacking and full-freezer inventories.
---
Files in This Repo
`index.html` — the dashboard application
`manifest.json` — PWA install metadata
`README.md` — this file
Drop both `index.html` and `manifest.json` in your GitHub repo. Replace any previous versions.
---
Deployment (if first time)
Step 1 — GitHub Repo
Create repo at https://github.com/new (any name, public is fine)
Upload `index.html` and `manifest.json`
Commit to `main`
Step 2 — Enable GitHub Pages
Repo → Settings → Pages
Source: Deploy from a branch, branch: `main`, folder: `/ (root)`
Save and wait ~60 seconds
Step 3 — Authorize URL in Google Cloud
https://console.cloud.google.com/apis/credentials
Click your OAuth Client ID
Authorized JavaScript origins → add `https://YOUR_USERNAME.github.io` (domain only, no path, no trailing slash)
Save. Wait 5 minutes.
Step 4 — First Sign-In on Pixel
Chrome → your GitHub Pages URL
SIGN IN WITH GOOGLE
If unverified-app warning appears: Advanced → Go to [app] (unsafe). Normal for personal apps.
Grant Drive access
Step 5 — Install to Home Screen
Chrome ⋮ menu → Add to Home screen
Now opens as standalone app
---
Setting Up AI Pantry Scan (One-Time)
The pantry scan needs an Anthropic API key. Without it, the dashboard works fine for everything else, but the 📷 ADD ITEM and 📦 BULK SCAN buttons will redirect you to Settings to add one.
Get the API Key
Go to https://console.anthropic.com
Sign in (use any email — separate from your Claude subscription)
Settings → API Keys → Create Key
Copy the full key starting with `sk-ant-...`
Add Credit
https://console.anthropic.com/settings/billing → Add credit
$5 minimum. This will last for hundreds of pantry scans. Real-world cost: a fully detailed bulk freezer scan runs about 1–2 cents.
Enter Key in Dashboard
Open the dashboard → tap ⋯ (top right)
AI Scan section → paste key → SAVE KEY
Key is stored only on your phone (localStorage). Never synced to Drive. Cleared if you tap CLEAR or sign out.
---
How Scanning Works
Single Item (📷 ADD ITEM)
Camera opens with framing guide
Aim at one product, snap
AI returns: name, category (FREEZER/FRIDGE/PANTRY), quantity, expiry date if visible
Edit any field, tap ADD TO PANTRY
Bulk Scan (📦 BULK SCAN)
Open the freezer, fridge, or pantry shelf
Take one wide photo of the contents
AI returns a list of all visible items, categorized
You see them all in an editable list with checkboxes
Deselect anything wrong, edit any field, tap ADD N ITEMS
Confidence Indicators
HIGH — clear visibility, unambiguous identification
MEDIUM — visible but partially obscured or generic
LOW — best guess, double-check before confirming
---
Data Storage
Pantry, grocery, food logs: in `04 - Personal / Health Concierge / dashboard-data.json` on your Drive. Sir's coach reads this in any Claude conversation.
Anthropic API key: localStorage on the phone only. Never leaves the device. Never goes to Drive.
---
Privacy & Security
The Anthropic API key is sensitive — anyone with it can spend money on your account. It lives only in your phone's local storage, accessible only to this app. It's never transmitted to anyone except api.anthropic.com.
The app uses Google's `drive.file` scope: only files this app creates can be accessed. It cannot read your other Drive files.
The data file in Drive is visible to anyone you share that folder with, and is readable by Anthropic via the Claude conversation. For a coaching dashboard, this is the point.
---
Future Add-ons (when ready)
AI food scan for meal logging (point at restaurant plate, log macros)
Multi-day analytics view
Recipe library expansion
Voice input for grocery list
Expiry date alerts based on scanned items
