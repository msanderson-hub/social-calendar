# Social Calendar Tab — Handoff Package

> Drop this into a Flask dashboard (or run `standalone_app.py` by itself) to get the
> iConnections Social Calendar tab: weekly / monthly calendar, post queue, and a
> detail modal per post. **Ships with dummy data so you can run it offline with
> zero setup.**

**Built for:** Molly Sanderson (iConnections marketing) — vibe coding contest submission
**Source repo:** `/Users/kellyoc/.openclaw/workspace/dashboard/`
**Snapshot date:** 2026-05-10
**Module size:** ~4,100 lines (`social_calendar.py`) — fully self-contained Flask blueprint

## ⚡ TL;DR for the receiving bot (Claude)

```bash
pip install -r requirements.txt
python standalone_app.py
# → open http://127.0.0.1:8989/
```

That's it. No API keys, no `.env`, no Monday.com. 22 realistic in-memory posts.
Clicking status pills and saving platform URLs updates the data live — the UI
reflects changes immediately. Restart the server to reset.

---

## 1. What's in this package

| File | What it is |
|---|---|
| `social_calendar.py` | The whole thing. Flask blueprint + embedded HTML + embedded JS. |
| `dummy_data.py` | **22 realistic in-memory posts** spanning GAMI26, GANY26, F4C26, Coffee & Connections, Platform/Product, Podcast, etc. Edit this file to change the demo content. |
| `dummy_patch.py` | Monkey-patches the Monday.com fetch + writeback functions so everything runs offline. Live in-memory updates (Option 2). |
| `_envloader.py` | Tiny stdlib-only `.env` loader. Auto-loads on import. |
| `.env.example` | Template for env vars (only needed if you switch to LIVE mode). |
| `standalone_app.py` | Minimal Flask app that mounts the tab. Defaults to **DUMMY mode**. |
| `requirements.txt` | `Flask` is the only hard dep. Everything else is stdlib. |
| `README.md` | This file. |

The module exports exactly three things into the host app:

```python
from social_calendar import (
    social_cal_bp,        # Flask Blueprint with all /api/social-calendar/* routes
    SOCIAL_CAL_TAB_HTML,  # str — the tab markup, with id="socialcal-view"
    SOCIAL_CAL_TAB_JS,    # str — the tab JavaScript (functions scInit, scRefresh, ...)
)
```

That's the entire integration surface.

---

## 2. Quick start

### Dummy mode (default — recommended for the contest)

```bash
cd social-calendar-package
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python standalone_app.py
# → open http://127.0.0.1:8989/
```

No API keys, no internet, no `.env`. Just runs. You'll see a banner at the top:

> 🎨 **Dummy data mode** — 22 in-memory posts. Clicks on status toggles and link
> fields update live, but reset on restart. No Monday.com calls.

### Live mode (if you want real Monday.com data)

```bash
cp .env.example .env       # fill in MONDAY_API_KEY (only required field)
DUMMY=0 python standalone_app.py
```

With a valid `MONDAY_API_KEY`, you'll get the real posts from the
**2026 Social Media** (`8806769351`) and **2025 Social Media** (`8158522933`) boards.

---

## 3. Embedding inside an existing Flask dashboard

This is exactly how the iC marketing dashboard wires it up (`dashboard/app.py`).
Three plug points:

### 3a. Import + register the blueprint

```python
# In your main app.py
from flask import Flask

try:
    from social_calendar import social_cal_bp, SOCIAL_CAL_TAB_HTML, SOCIAL_CAL_TAB_JS
    HAS_SOCIAL_CAL = True
except Exception as e:
    print(f"Social calendar module load error: {e}")
    HAS_SOCIAL_CAL = False

app = Flask(__name__)
if HAS_SOCIAL_CAL:
    app.register_blueprint(social_cal_bp)
```

### 3b. Drop the HTML into your tab container

The HTML is one `<div id="socialcal-view" style="display:none">…</div>`. Place it
wherever you want the tab body to render:

```python
page_html = f"""
<!doctype html>
…
<button onclick="switchMainTab('socialcal')">📅 Social Calendar</button>
…
{SOCIAL_CAL_TAB_HTML if HAS_SOCIAL_CAL else ''}
…
"""
```

### 3c. Append the JS to your page (or include via `<script>`)

```python
page_html += f"<script>{SOCIAL_CAL_TAB_JS if HAS_SOCIAL_CAL else ''}</script>"
```

### 3d. Implement the one host hook the JS expects: `switchMainTab(tab)`

The embedded JS calls `scInit()` once when the tab is first shown. The dashboard
already has a multi-tab switcher; minimum viable version:

```js
function switchMainTab(tab) {
  document.getElementById('socialcal-view').style.display =
    (tab === 'socialcal') ? '' : 'none';
  if (tab === 'socialcal' && typeof scInit === 'function') {
    scInit();   // lazy-init on first show
  }
}
```

That's it — no other host JS is required.

---

## 4. CSS variables the tab depends on

The HTML/JS uses `var(--…)` custom properties for colors. If your dashboard already
defines these (any decent dark theme will), you're done. Otherwise paste this into
your stylesheet:

```css
:root {
  --bg:       #070714;
  --surface:  #10102a;
  --surface2: #16163a;
  --surface3: #1c1c45;
  --border:   #2a2a5a;
  --text:     #e8e8ff;
  --muted:    #888;
  --purple:   #7c6fff;
  --teal:     #5eead4;
  --pink:     #f472b6;
  --green:    #4ade80;
  --yellow:   #facc15;
  --orange:   #fb923c;
}
.tab { padding: 8px 18px; border-radius: 7px; cursor: pointer; font-size: 0.85rem;
       font-weight: 500; color: var(--muted); border: none; background: transparent; }
.tab.active { background: var(--purple); color: #fff; }
.loading { display: flex; align-items: center; justify-content: center;
           gap: 12px; color: var(--muted); padding: 60px; }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border);
           border-top-color: var(--purple); border-radius: 50%;
           animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
```

The `standalone_app.py` in this package already includes these.

---

## 5. Environment variables

Copy `.env.example` → `.env` and fill in. Only `MONDAY_API_KEY` is required;
everything else is optional and gates a specific feature.

| Var | Required? | What it does |
|---|---|---|
| `MONDAY_API_KEY` | **Yes** | Pulls posts from the 2025 + 2026 Social Media boards. |
| `OPENAI_API_KEY` | No | Enables image vision (speaker headshots) + caption generation if feature flags are on. |
| `SPROUT_API_KEY` | No | Lets the "find post link" feature look up posted URLs in Sprout Social. |
| `SPROUT_CUSTOMER_ID` | No | Defaults to `2625468` (iConnections). |
| `YT_API_KEY` / `YOUTUBE_API_KEY` | No | Lets "find post link" look up YouTube uploads/shorts. |
| `YT_CHANNEL_ID` / `YOUTUBE_CHANNEL_ID` | No | Defaults to `UCY6TEokyfC4sw--JMLoojDg` (iConnections). |
| `SLACK_BOT_TOKEN` | No | If AI captions are re-enabled, posts the request to a Slack DM. |
| `SLACK_NICK_DM_CHANNEL` | No | Slack user/DM ID to ping. Default `U0801RGF87P` (Molly). |
| `OPENCLAW_GATEWAY_URL` | No | Default `http://127.0.0.1:18789`. Only used by AI caption refine. |
| `OPENCLAW_GATEWAY_TOKEN` | No | Auth for the OpenClaw gateway when AI captions are on. |
| `REFINE_MODEL` | No | Default `openai/gpt-4o-mini`. |

### Feature flags (top of `social_calendar.py`, lines 18-30)

```python
FEATURE_AI_CAPTIONS        = False  # /generate-caption, /refine-caption, /ask-nick
FEATURE_AUTO_FIND_LINKS    = False  # auto-find post links on "Posted" status flip
FEATURE_WRITE_LINKS_TO_MONDAY = False  # write found URLs back to Monday link columns
```

All three are **disabled by default** per Molly's call on 2026-05-04 (Slack thread
`1777123665.829359` in `#all-marketing-nick`). The code is intentionally left in place;
flip a flag back to `True` to re-enable a feature if it's wanted.

---

## 6. Monday.com — boards + columns

Two boards drive everything. They have different column IDs because they were created
in different years. The mapping lives in the `BOARDS` dict at the top of
`social_calendar.py` (line 35).

```python
BOARDS = {
    "8806769351": {  # 2026 Social Media (PRIMARY)
        "name": "2026 Social Media",
        "col": {
            "date":          "date",
            "status":        "color_mm2r88k9",
            "post_type":     "status3",
            "files":         "file_mm2rmc91",
            "linkedin":      "check",
            "instagram":     "boolean",
            "twitter":       "boolean3",
            "tiktok":        "boolean_mm2gnkk4",
            "yt_full":       "boolean_mm2rznsa",
            "yt_shorts":     "boolean_mm2r54zj",
            "inapp_feed":    "boolean_mm2gz2wv",
            "notes":         "text_mknthjgy",
            # … plus the per-platform link columns
        },
    },
    "8158522933": {  # 2025 Social Media (HISTORICAL)
        "name": "2025 Social Media",
        # ... same shape, different column IDs ...
    },
}
```

If a column ID changes in Monday (rename ≠ ID change, but rebuild = ID change),
edit just this dict. The rest of the module reads through `BOARDS[board_id]["col"]`.

The **2024 board** (`6201942073`) uses a status column `status3` named `Event` to
tag posts by event; 2025+ boards organize by **group** instead. The module only
reads from 2025 + 2026 boards by default.

---

## 7. API surface (what the JS calls)

All routes are namespaced under `/api/social-calendar/`. Mostly internal to the tab;
listed here so you can hook up tests, monitoring, or alternate frontends.

| Method | Route | Purpose |
|---|---|---|
| `GET`  | `/api/social-calendar/items` | All posts across both boards (cached). Main feed. |
| `GET`  | `/api/social-calendar/item/<item_id>` | Detail for one post (modal). |
| `GET`  | `/api/social-calendar/sync-version` | Cheap "has anything changed?" check for polling. |
| `POST` | `/api/social-calendar/webhook` | Monday.com webhook receiver (invalidates cache). |
| `POST` | `/api/social-calendar/update-status` | Toggle a post's status column (e.g. → Posted). |
| `POST` | `/api/social-calendar/update-link` | Write a found URL back to a Monday link column. |
| `POST` | `/api/social-calendar/find-links` | Trigger "find link" lookup for one post. |
| `POST` | `/api/social-calendar/suggest-links` | Bulk lookup for posts in a date range. |
| `GET`  | `/api/social-calendar/asset/<asset_id>` | Stream a Monday file attachment through the dashboard. |
| `POST` | `/api/social-calendar/analyze-image` | OpenAI Vision call on a post asset. (Feature-flagged.) |
| `POST` | `/api/social-calendar/analyze-speaker-image` | Same, but extracts speaker name + title for headshot cards. |
| `GET`  | `/api/social-calendar/vision-status` | Returns `{"enabled": bool}` for the OpenAI key check. |
| `POST` | `/api/social-calendar/generate-caption` | Draft a caption (disabled by default). |
| `POST` | `/api/social-calendar/refine-caption` | Refine with OpenClaw gateway round-trip (disabled). |
| `POST` | `/api/social-calendar/ask-nick` | Queue caption request to Nick via Slack (disabled). |
| `GET`  | `/api/social-calendar/ask-nick-status/<request_id>` | Poll for Nick's reply (disabled). |

---

## 8. JS surface (functions the JS exposes on `window`)

If you're embedding from React/Vue or want to drive the tab programmatically, these
are the entry points (all prefixed `sc…`):

- `scInit()` — first-show init. Idempotent.
- `scRefresh()` — force-reload from `/api/social-calendar/items`.
- `scApplyFilters()` — re-apply the group / type / status filters.
- `scSwitchCalView('weekly' | 'monthly')`
- `scNavPrev()` / `scNavNext()` / `scNavToday()` / `scJumpToDate()`
- `scUpcomingPrev()` / `scUpcomingNext()` / `scUpcomingThisWeek()`
- `scOpenModal(itemId)` / `scCloseModal()`

Internal caches: `scItems`, `scFilteredItems`, `scCaptionCache`, `scImageDataCache`.

---

## 9. Dummy mode — how it works (for the receiving bot)

This is the contest-friendly mode. Everything in the tab works without Monday.com.

### What's faked

`dummy_patch.py` swaps these functions on the `social_calendar` module:

| Function / route | Real behavior | Dummy behavior |
|---|---|---|
| `get_cached_items(force)` | Monday GraphQL fetch + parse_item per row | Returns the in-memory `dummy_data.ITEMS` list, sorted by date |
| `get_board_groups(force)` | Monday GraphQL fetch | Returns `dummy_data.list_groups()` |
| `fetch_all_items()` | Monday GraphQL fetch | Returns `[]` (not used by the tab in dummy mode) |
| `monday_query(q)` / `monday_mutate(q)` | HTTPS to api.monday.com | No-op safety net; returns `{"data": None, "_dummy": True}` |
| `POST /update-status` | Calls Monday mutation | **Updates the in-memory item's `status` + `status_color`** |
| `POST /update-link` | Calls Monday mutation | **Updates the in-memory item's `platform_links[platform]`** |
| `GET /sync-version` | Cache-based version int | Bumps every time a dummy mutation succeeds |
| `GET /item/<id>` | Monday GraphQL fetch + parse | Returns the in-memory item directly |
| `GET /asset/<id>` | Proxies bytes from a fresh Monday signed URL | 302 redirect to a `placehold.co` placeholder URL |

The shape of every payload matches LIVE mode exactly, so the frontend JS
doesn't know it's running against a fake backend. Responses also include a
`"_dummy": true` field for debug/inspection.

### What's in the dummy dataset

22 posts across 9 groups and 2 boards:

- **Global Alts Miami 2026** (GAMI26) — 6 posts (speaker, panel, milestones, sponsor, etc.)
- **Global Alts New York 2026** (GANY26) — 3 posts (announcement, speaker reveal, testimonial)
- **Funds 4 Food 2026** (F4C26) — 2 posts (milestone, networking)
- **Coffee & Connections** — 2 posts (NYC + Chicago)
- **Platform & Product** — 3 posts (product launch, case study, teaser)
- **Media & Podcasts** — 3 posts (Bloomberg, blog, TikTok trend)
- **Holidays** — 1 post (Memorial Day)
- **Global Alts Miami 2025** + **Global Alts Asia 2025** — 2 historical posts to show board mixing

All 5 statuses are represented (`Posted` / `Scheduled` / `Working on it` / `For Scheduling` / `Need Content`). Most posts span future dates relative to today so the calendar always feels current.

### Editing the demo data

Open `dummy_data.py` and edit the `ITEMS = [ ... ]` list at the bottom. Each call
to `_make(idx, name, group_name, post_type, platforms, status=..., date_offset=..., notes=..., links=..., with_asset=...)` builds one post. Re-run the server to see changes.

- `date_offset` is days from today (negative = past, positive = future).
- `links` is a dict of `{platform_name: url}` for already-posted items.
- `with_asset=True` attaches a placeholder image asset that renders in the modal.

### Switching modes at runtime

```bash
python standalone_app.py        # DUMMY (default)
DUMMY=0 python standalone_app.py  # LIVE (needs MONDAY_API_KEY)
```

Or in your own host app, just don't import `dummy_patch`.

---

## 10. Caching + polling behavior

- The `/items` endpoint caches the Monday GraphQL response in-process for ~60 s.
- The frontend polls `/sync-version` every 30 s; if the version bumped, it re-fetches
  `/items`. This is the cheap "did anyone edit Monday?" check.
- The `/webhook` route is wired to invalidate the cache the instant Monday fires a
  board event (configure the webhook in Monday → Integrations → Webhooks pointing at
  `https://<your-host>/api/social-calendar/webhook`).
- No DB. All state lives in Monday.com.

---

## 11. AI caption flow (disabled, but here's how it works if re-enabled)

When `FEATURE_AI_CAPTIONS = True`:

1. Frontend modal calls `POST /generate-caption` with the post + analyzed asset.
2. Module writes a request file to `/tmp/iconnections-nick-queue/<request_id>.json`.
3. It also pings Slack DM `SLACK_NICK_DM_CHANNEL` with a `🤖 Caption refine request`
   message so the Nick agent (OpenClaw) sees it.
4. Frontend polls `GET /ask-nick-status/<request_id>` every 5 s for up to 3 min.
5. Nick's caption lands at `/tmp/iconnections-nick-results/<request_id>.json` as
   `{"caption": "..."}` and the modal auto-fills.

**Caption rules** (enforced by Nick, not by the module): max 5 hashtags,
`#iConnections` first, plus the MFA partner tag on event posts:
- LinkedIn → `@MFA`
- Twitter / X → `@MFAupdates`
- Instagram → `@mfa_alts`

**No OpenAI API key is used for captions** — Molly explicitly excluded it.

---

## 12. Re-implementation cheatsheet (for the receiving bot)

If the goal is to recreate this tab in a different codebase (Next.js, FastAPI,
whatever), here's the minimum spec to match feature parity:

**Data model (per post, what the UI needs):**
- `id` (Monday item id)
- `name` (post title)
- `date` (ISO `YYYY-MM-DD`)
- `status` (one of: `Working on it`, `Scheduled`, `For Scheduling`, `Posted`, `Need Content`, `null`)
- `post_type` (Monday status3 label — e.g. `Educational`, `Event`, `Promotion`)
- `group` (Monday group title — typically the event or month)
- `platforms`: `{linkedin, instagram, twitter, tiktok, yt_full, yt_shorts, inapp_feed}` → bool
- `links`: `{linkedin_url, instagram_url, twitter_url, tiktok_url, yt_full_url, yt_shorts_url}`
- `notes` (free-text from Monday)
- `assets`: list of `{asset_id, name, url, mime}` (Monday file column)
- `board_id` (so the writer knows which column-ID set to use on writeback)

**Views:**
1. **Weekly calendar** — 7-day grid, posts grouped by day. Default landing view.
2. **Monthly calendar** — 5-6 week grid, dense layout, click-through to detail modal.
3. **Post queue** — chronological list of upcoming posts with platform icons + status pills, paginated by week.
4. **Detail modal** — full post info, asset preview, status toggle, link-finder buttons, "open in Monday" link.

**Filters (top bar):**
- Group dropdown (auto-populated from data)
- Type dropdown (auto-populated from `post_type`)
- Status dropdown (fixed list above)

**Writebacks to Monday:**
- Status change → `POST /update-status`
- Per-platform URL (after a post goes live) → `POST /update-link`

**Polling:**
- 30 s `sync-version` check, 60 s cache TTL on `items`.

---

## 13. Known quirks / gotchas

- **Monday GraphQL is paginated at 500 items per page.** The module handles cursor
  iteration; if you reimplement, don't forget `next_cursor`.
- **File assets need the dashboard proxy.** Monday file URLs are signed + short-lived;
  the `/api/social-calendar/asset/<asset_id>` route refreshes them server-side. Don't
  expose raw Monday `public_url` values to the frontend.
- **`board_id` matters for every writeback.** Two posts can have identical column
  shapes but live on different boards with different column IDs. Always thread
  `board_id` through writebacks.
- **Caption refine uses the OpenClaw gateway by design.** It is *not* a direct
  OpenAI call. If you don't have an OpenClaw gateway running locally, leave
  `FEATURE_AI_CAPTIONS = False`.
- **The dashboard's `switchMainTab` is the only host JS contract.** If you don't
  provide it, the tab never initializes.

---

## 14. Provenance + how to update

- Source path: `/Users/kellyoc/.openclaw/workspace/dashboard/social_calendar.py`
- Started: ~April 2026
- Snapshot: 2026-05-10 (1,810 lines of Python, ~80 lines of HTML, ~2,000 lines of JS, all inside the single .py file)
- To pull a fresh copy: just re-copy `social_calendar.py` and `_envloader.py` from
  the source repo. No build step.

Questions on the iC side go to Kelly Altomare (Slack `U0AK47NEPJN` — wait that's
Juliana; Kelly is the workspace owner. Molly Sanderson is `U0801RGF87P`.)

---

Built by Nick ⚡ for Molly. Have fun. 📅
