#!/usr/bin/env python3
"""
Social Media Calendar Module for iConnections Marketing Dashboard
Pulls from Monday.com 2026 Social Media board, renders calendar views,
upcoming post schedule, and AI caption generation.
"""

import os, json, time, threading, urllib.request, urllib.parse, hashlib, base64
import _envloader  # noqa: F401  # Loads .env into os.environ
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request

social_cal_bp = Blueprint('social_cal', __name__)

# ─── Feature Flags ────────────────────────────────────────────────────────────
# Disabled per Molly Sanderson on 2026-05-04 (Slack thread 1777123665.829359 in
# #all-marketing-nick). Do NOT re-enable any of these without an explicit ask
# from Molly or Kelly. Code is intentionally left in place so it can be turned
# back on by flipping the flag — do not delete the underlying logic.
FEATURE_AI_CAPTIONS = False         # /generate-caption, /refine-caption, /ask-nick(-status)
FEATURE_AUTO_FIND_LINKS = False     # auto-find post links when an item is marked Posted, plus /find-links
FEATURE_WRITE_LINKS_TO_MONDAY = False  # writing found URLs into Monday link columns

# ─── Vision API Config (for speaker image analysis) ───────────────────────────
# Set OPENAI_API_KEY env var to enable automatic speaker detail extraction from images
# Uses GPT-4o-mini vision (cheapest option, ~$0.001 per image)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ─── Monday.com Config ────────────────────────────────────────────────────────
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "")

# ─── Multi-Board Support ──────────────────────────────────────────────────────
# Each board has its own column IDs since they differ between years

BOARDS = {
    "8806769351": {
        "name": "2026 Social Media",
        "col": {
            "date": "date",
            "status": "color_mm2r88k9",
            "post_type": "status3",
            "files": "file_mm2rmc91",
            "linkedin": "check",
            "instagram": "boolean",
            "twitter": "boolean3",
            "tiktok": "boolean_mm2gnkk4",
            "yt_full": "boolean_mm2rznsa",
            "yt_shorts": "boolean_mm2r54zj",
            "inapp_feed": "boolean_mm2gz2wv",
            "notes": "text_mknthjgy",
        },
        "link_cols": {
            "LinkedIn": "link",
            "Instagram": "link_mm2rqd00",
            "Twitter": "link_mm2r2t3q",
            "TikTok": "link_mm2r19y8",
            "YT Full": "link_mm2rspr8",
            "YT Short": "link_mm2rw59n",
        },
        "platform_cols": {
            "check": "LinkedIn",
            "boolean": "Instagram",
            "boolean3": "Twitter",
            "boolean_mm2gnkk4": "TikTok",
            "boolean_mm2rznsa": "YT Full Length",
            "boolean_mm2r54zj": "YT Shorts",
            "boolean_mm2gz2wv": "In-app Feed",
        },
    },
    "8158522933": {
        "name": "2025 Social Media",
        "col": {
            "date": "date",
            "status": "color_mm2rhej2",
            "post_type": "status3",
            "files": None,  # 2025 board has no files column
            "linkedin": "check",
            "instagram": "boolean",
            "twitter": "boolean3",
            "tiktok": "boolean_mkzsgj9e",
            "yt_full": "boolean_mm2r41mx",
            "yt_shorts": "boolean_mm2r34dh",
            "inapp_feed": "boolean_mkvxbz1y",
            "notes": "text_mknthjgy",
        },
        "link_cols": {
            "LinkedIn": "link",
            "Instagram": "link_mm2ra6fw",
            "Twitter": "link_mm2rnjwd",
            "TikTok": "link_mm2r4pj4",
            "YT Full": "link_mm2rnq3r",
            "YT Short": "link_mm2ryqyy",
        },
        "platform_cols": {
            "check": "LinkedIn",
            "boolean": "Instagram",
            "boolean3": "Twitter",
            "boolean_mkzsgj9e": "TikTok",
            "boolean_mm2r41mx": "YT Full Length",
            "boolean_mm2r34dh": "YT Shorts",
            "boolean_mkvxbz1y": "In-app Feed",
        },
    },
}

# Default board for backward compat
SOCIAL_BOARD_ID = "8806769351"

# Legacy references — COL and PLATFORM_COLS now come from BOARDS[board_id]
COL = BOARDS[SOCIAL_BOARD_ID]["col"]
PLATFORM_COLS = BOARDS[SOCIAL_BOARD_ID]["platform_cols"]

# Status labels and colors (from board settings_str)
STATUS_LABELS = {
    "0": {"label": "Working on it", "color": "#fdab3d"},
    "1": {"label": "Posted", "color": "#00c875"},
    "2": {"label": "Need Content", "color": "#df2f4a"},
    "3": {"label": "Scheduled", "color": "#579bfc"},
    "4": {"label": "For Scheduling", "color": "#faa1f1"},
}

# Post Type labels and colors (from board settings_str)
POST_TYPE_LABELS = {
    "0": {"label": "Meetups", "color": "#bca58a"},
    "1": {"label": "Product", "color": "#7e3b8a"},
    "2": {"label": "Case Study", "color": "#a9bee8"},
    "3": {"label": "Testimonial", "color": "#bda8f9"},
    "4": {"label": "Product Launch", "color": "#784bd1"},
    "6": {"label": "Partner Event", "color": "#175a63"},
    "7": {"label": "Video", "color": "#ff7575"},
    "8": {"label": "Sponsor", "color": "#74afcc"},
    "9": {"label": "Speaker", "color": "#4eccc6"},
    "10": {"label": "Report", "color": "#e484bd"},
    "11": {"label": "Press Release", "color": "#ffadad"},
    "12": {"label": "Milestones", "color": "#579bfc"},
    "13": {"label": "Networking Event", "color": "#ff5ac4"},
    "14": {"label": "Post Miami Campaign", "color": "#401694"},
    "15": {"label": "Testimonials", "color": "#a1e3f6"},
    "16": {"label": "Post GAMI25 Content", "color": "#66ccff"},
    "17": {"label": "Coffee & Connections", "color": "#757575"},
    "18": {"label": "Current Events", "color": "#9d99b9"},
    "19": {"label": "Panel", "color": "#00c875"},
    "101": {"label": "Media", "color": "#7f5347"},
    "102": {"label": "Podcast", "color": "#037f4c"},
    "103": {"label": "Research", "color": "#9cd326"},
}

# Post type color lookup by label name (merged from all boards)
POST_TYPE_COLORS_BY_NAME = {
    # From 2026 board
    "Meetups": "#bca58a", "Product": "#7e3b8a", "Case Study": "#a9bee8",
    "Testimonial": "#bda8f9", "Product Launch": "#784bd1", "Partner Event": "#175a63",
    "Video": "#ff7575", "Sponsor": "#74afcc", "Speaker": "#4eccc6",
    "Report": "#e484bd", "Press Release": "#ffadad", "Milestones": "#579bfc",
    "Networking Event": "#ff5ac4", "Post Miami Campaign": "#401694",
    "Testimonials": "#a1e3f6", "Post GAMI25 Content": "#66ccff",
    "Coffee & Connections": "#757575", "Current Events": "#9d99b9",
    "Panel": "#00c875", "Media": "#7f5347", "Podcast": "#037f4c",
    "Research": "#9cd326",
    # Additional from 2025 board
    "Announcement": "#333333", "Blog Post": "#216edf", "Board Members": "#faa1f1",
    "Cocktails & Connections": "#ffcb00", "Content Social Clips": "#9d50dd",
    "Countdown": "#225091", "F4C": "#5559df", "FOMO": "#fdab3d",
    "Funny": "#007eb5", "Funny Videos": "#9cd326", "Holiday": "#7f5347",
    "IRN": "#ff007f", "Investment Newsletter": "#df2f4a",
    "Onsite Content": "#563e3e", "Partnerships": "#cab641",
    "Past speaker clips": "#cd9282", "Staff": "#037f4c",
    "Trending Content": "#ff6d3b",
}

# Cache for Monday data
_cache = {"items": [], "last_fetch": 0, "lock": threading.Lock()}
CACHE_TTL = 300  # 5 minutes


def monday_query(query):
    """Execute a Monday.com GraphQL query."""
    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request("https://api.monday.com/v2", data=data, headers={
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Monday API error: {e}")
        return {"data": None, "error": str(e)}


def monday_mutate(query, variables=None):
    """Execute a Monday.com GraphQL mutation."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    data = json.dumps(payload).encode()
    req = urllib.request.Request("https://api.monday.com/v2", data=data, headers={
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Monday mutation error: {e}")
        return {"error": str(e)}


_groups_cache = {"groups": [], "last_fetch": 0}


def get_board_groups(force=False):
    """Fetch all groups from ALL configured boards (cached)."""
    now = time.time()
    if not force and _groups_cache["groups"] and (now - _groups_cache["last_fetch"]) < CACHE_TTL:
        return _groups_cache["groups"]

    board_ids = ",".join(BOARDS.keys())
    query = '{ boards(ids: [%s]) { id name groups { id title } } }' % board_ids
    result = monday_query(query)
    groups = []
    seen = set()
    if result.get("data") and result["data"]["boards"]:
        for board in result["data"]["boards"]:
            board_name = board["name"]
            for g in board["groups"]:
                # Deduplicate by title (same group name across boards)
                if g["title"] not in seen:
                    seen.add(g["title"])
                    groups.append({"id": g["id"], "title": g["title"], "board": board_name})

    _groups_cache["groups"] = groups
    _groups_cache["last_fetch"] = now
    return groups


def fetch_board_items(board_id):
    """Fetch all items from a single board with pagination."""
    all_items = []
    cursor = None

    while True:
        if cursor:
            query = '''
            { next_items_page(limit: 200, cursor: "%s") {
                cursor
                items {
                    id name
                    group { id title }
                    column_values { id text value type }
                    assets { id name url file_extension public_url }
                }
            }}
            ''' % cursor
        else:
            query = '''
            { boards(ids: %s) {
                items_page(limit: 200) {
                    cursor
                    items {
                        id name
                        group { id title }
                        column_values { id text value type }
                        assets { id name url file_extension public_url }
                    }
                }
            }}
            ''' % board_id

        result = monday_query(query)
        if not result.get("data"):
            break

        if cursor:
            page = result["data"]["next_items_page"]
        else:
            page = result["data"]["boards"][0]["items_page"]

        items = page.get("items", [])
        # Tag each item with its board_id
        for it in items:
            it["_board_id"] = board_id
        all_items.extend(items)
        cursor = page.get("cursor")
        if not cursor or not items:
            break

    return all_items


def fetch_all_items():
    """Fetch all items from ALL configured social media boards."""
    all_items = []
    for board_id in BOARDS:
        items = fetch_board_items(board_id)
        all_items.extend(items)
    return all_items


def parse_item(item):
    """Parse a Monday item into a clean dict. Board-aware for column mappings."""
    board_id = item.get("_board_id", SOCIAL_BOARD_ID)
    board_cfg = BOARDS.get(board_id, BOARDS[SOCIAL_BOARD_ID])
    board_col = board_cfg["col"]
    board_plat_cols = board_cfg["platform_cols"]

    cols = {c["id"]: c for c in item["column_values"]}

    # Parse date
    date_val = cols.get(board_col["date"], {}).get("text", "")

    # Parse status (some boards don't have a status column)
    STATUS_COLORS_BY_NAME = {
        "Working on it": "#fdab3d", "Posted": "#00c875",
        "Need Content": "#df2f4a", "Scheduled": "#579bfc",
        "For Scheduling": "#faa1f1",
    }
    status_text = ""
    status_color = "#555"
    if board_col.get("status"):
        status_text = cols.get(board_col["status"], {}).get("text") or ""
        status_color = STATUS_COLORS_BY_NAME.get(status_text, "#555")

    # Parse post type — use text directly since label indices differ across boards
    pt_text = cols.get(board_col["post_type"], {}).get("text") or ""
    pt_color = "#555"
    # Look up color from POST_TYPE_COLORS (keyed by label name)
    pt_color = POST_TYPE_COLORS_BY_NAME.get(pt_text, "#555")

    # Parse platform links (LinkedIn Link, Instagram Link, etc.)
    platform_links = {}
    link_cols = board_cfg.get("link_cols", {})
    for plat_name, col_id in link_cols.items():
        link_raw = cols.get(col_id, {}).get("value")
        if link_raw:
            try:
                lv = json.loads(link_raw)
                url = lv.get("url", "")
                txt = lv.get("text", "")
                if txt == "ig-story" or url == "https://ig-story":
                    platform_links[plat_name] = "ig-story"
                elif url:
                    platform_links[plat_name] = url
            except:
                txt = cols.get(col_id, {}).get("text", "")
                if txt == "ig-story":
                    platform_links[plat_name] = "ig-story"
                elif txt:
                    platform_links[plat_name] = txt

    # Legacy social_link for backward compat (use LinkedIn link)
    social_link = platform_links.get("LinkedIn", "")

    # Parse platforms (checkboxes) — use board-specific column IDs
    platforms = []
    for col_id, plat_name in board_plat_cols.items():
        cv = cols.get(col_id, {}).get("value")
        if cv:
            try:
                if json.loads(cv).get("checked"):
                    platforms.append(plat_name)
            except:
                pass

    # Parse notes
    notes_col = board_col.get("notes")
    notes = cols.get(notes_col, {}).get("text") or "" if notes_col else ""

    # Parse files (some boards don't have a files column)
    files = []
    files_col = board_col.get("files")
    if files_col:
        file_raw = cols.get(files_col, {}).get("value")
        if file_raw:
            try:
                fv = json.loads(file_raw)
                for f in fv.get("files", []):
                    files.append({
                        "name": f.get("name", ""),
                        "assetId": f.get("assetId"),
                        "isImage": f.get("isImage") == "true",
                    })
            except:
                pass

    # Assets with public URLs
    assets = []
    for a in item.get("assets", []):
        assets.append({
            "id": a["id"],
            "name": a["name"],
            "public_url": a.get("public_url", ""),
            "extension": a.get("file_extension", ""),
        })

    return {
        "id": item["id"],
        "name": item["name"],
        "board_id": board_id,
        "board_name": board_cfg["name"],
        "group_id": item["group"]["id"],
        "group_name": item["group"]["title"],
        "date": date_val,
        "status": status_text,
        "status_color": status_color,
        "social_link": social_link,
        "platform_links": platform_links,
        "post_type": pt_text,
        "post_type_color": pt_color,
        "platforms": platforms,
        "notes": notes,
        "files": files,
        "assets": assets,
        "has_status_col": board_col.get("status") is not None,
    }


def get_cached_items(force=False):
    """Get items with caching."""
    with _cache["lock"]:
        now = time.time()
        if not force and _cache["items"] and (now - _cache["last_fetch"]) < CACHE_TTL:
            return _cache["items"]

    raw = fetch_all_items()
    parsed = [parse_item(it) for it in raw]
    # Sort by date
    parsed.sort(key=lambda x: x["date"] or "9999-99-99")

    with _cache["lock"]:
        _cache["items"] = parsed
        _cache["last_fetch"] = time.time()

    return parsed


# Pre-warm cache in background on module load
def _warm_cache():
    try:
        print("[Social Calendar] Pre-warming cache...")
        items = get_cached_items(force=True)
        get_board_groups(force=True)
        print(f"[Social Calendar] Cache warmed: {len(items)} items")
    except Exception as e:
        print(f"[Social Calendar] Cache warm error: {e}")

_warm_thread = threading.Thread(target=_warm_cache, daemon=True)
_warm_thread.start()


# ─── Monday.com Webhook for Real-Time Sync ────────────────────────────────────

# Version counter — incremented on webhook events; frontend polls this to know
# when to auto-refresh without waiting for the full cache TTL.
_sync_version = {"v": 0, "last_event": 0}


@social_cal_bp.route("/api/social-calendar/webhook", methods=["POST"])
def api_monday_webhook():
    """Receive Monday.com webhook events for real-time sync.
    
    Monday sends two types of requests:
    1. Verification challenge (on webhook creation): {"challenge": "..."}
       → Must respond with {"challenge": "..."} 
    2. Event payload: {"event": {"type": "...", "boardId": ..., ...}}
       → Invalidate cache and bump version counter
    """
    body = request.get_json(silent=True) or {}

    # Handle verification challenge (Monday sends this when creating the webhook)
    if "challenge" in body:
        print(f"[Webhook] Monday verification challenge received")
        return jsonify({"challenge": body["challenge"]})

    # Handle event — invalidate cache
    event = body.get("event", {})
    event_type = event.get("type", "unknown")
    board_id = str(event.get("boardId", ""))
    item_id = event.get("pulseId", event.get("itemId", ""))

    print(f"[Webhook] Monday event: type={event_type}, board={board_id}, item={item_id}")

    # Invalidate cache so next request fetches fresh data
    with _cache["lock"]:
        _cache["last_fetch"] = 0

    # Bump sync version so polling frontends know to refresh
    _sync_version["v"] += 1
    _sync_version["last_event"] = time.time()

    return jsonify({"ok": True})


@social_cal_bp.route("/api/social-calendar/sync-version")
def api_sync_version():
    """Lightweight endpoint the frontend polls to detect webhook-triggered changes.
    Returns the current version counter. When it changes, frontend auto-refreshes."""
    return jsonify({
        "v": _sync_version["v"],
        "last_event": _sync_version["last_event"],
    })


# ─── API Routes ───────────────────────────────────────────────────────────────

@social_cal_bp.route("/api/social-calendar/items")
def api_calendar_items():
    """Return all social media items for calendar rendering."""
    force = request.args.get("refresh") == "1"
    items = get_cached_items(force=force)
    # Filter to items with dates only for calendar
    dated = [it for it in items if it["date"]]
    # Fetch all groups from the board so the filter shows every group
    all_groups = get_board_groups(force=force)
    return jsonify({
        "items": dated,
        "total": len(items),
        "dated": len(dated),
        "all_groups": all_groups,
        "cached_at": _cache["last_fetch"],
    })


@social_cal_bp.route("/api/social-calendar/item/<item_id>")
def api_calendar_item_detail(item_id):
    """Return full detail for a single item, including fresh asset URLs."""
    # Determine which board this item belongs to from cache
    cached = get_cached_items()
    board_id = SOCIAL_BOARD_ID
    for ci in cached:
        if ci["id"] == str(item_id):
            board_id = ci.get("board_id", SOCIAL_BOARD_ID)
            break

    # Refresh asset URLs since they expire
    query = '''
    { items(ids: [%s]) {
        id name
        group { id title }
        column_values { id text value type }
        assets { id name url file_extension public_url }
    }}
    ''' % item_id
    result = monday_query(query)
    if result.get("data") and result["data"]["items"]:
        raw_item = result["data"]["items"][0]
        raw_item["_board_id"] = board_id
        item = parse_item(raw_item)
        return jsonify(item)
    return jsonify({"error": "Item not found"}), 404


@social_cal_bp.route("/api/social-calendar/update-status", methods=["POST"])
def api_update_status():
    """Update an item's status on Monday.com (e.g., mark as Scheduled)."""
    body = request.get_json()
    item_id = body.get("item_id")
    status_label = body.get("status_label")  # "Posted", "Scheduled", "Working on it", etc.
    board_id = body.get("board_id", SOCIAL_BOARD_ID)

    if not item_id or not status_label:
        return jsonify({"error": "item_id and status_label required"}), 400

    # Check if this board has a status column
    board_cfg = BOARDS.get(board_id, BOARDS[SOCIAL_BOARD_ID])
    status_col = board_cfg["col"].get("status")
    if not status_col:
        return jsonify({"error": "This board does not have a status column"}), 400

    # Monday's change_simple_column_value accepts the label string directly
    mutation = '''
    mutation {
        change_simple_column_value(
            item_id: %s,
            board_id: %s,
            column_id: "%s",
            value: "%s"
        ) { id }
    }
    ''' % (item_id, board_id, status_col, status_label)

    result = monday_mutate(mutation)
    if result.get("errors"):
        err_msg = result["errors"][0].get("message", "Unknown error")
        return jsonify({"error": err_msg}), 500
    if result.get("error"):
        return jsonify({"error": result["error"]}), 500

    # Invalidate cache so next fetch gets fresh data
    with _cache["lock"]:
        _cache["last_fetch"] = 0

    # If marking as Posted, auto-find links from Sprout Social
    # DISABLED 2026-05-04 per Molly: do NOT auto-find links and do NOT write
    # them into Monday's link columns. Gated behind FEATURE_AUTO_FIND_LINKS /
    # FEATURE_WRITE_LINKS_TO_MONDAY so this can be re-enabled cleanly later.
    found_links = {}
    if status_label == "Posted" and FEATURE_AUTO_FIND_LINKS:
        # Force refresh cache to get latest item data (platforms, date, etc.)
        cached = get_cached_items(force=True)
        item_data = None
        for ci in cached:
            if ci["id"] == str(item_id):
                item_data = ci
                break

        if item_data and item_data.get("platforms"):
            found_links = find_post_links(
                item_name=item_data["name"],
                post_date=item_data["date"],
                platforms=item_data["platforms"],
                notes=item_data.get("notes", ""),
            )

            # Write found links to Monday board
            if found_links and FEATURE_WRITE_LINKS_TO_MONDAY:
                link_cols = board_cfg.get("link_cols", {})
                for plat_label, url in found_links.items():
                    # Map platform to link column
                    col_id = None
                    if plat_label == "LinkedIn" and "LinkedIn" in link_cols:
                        col_id = link_cols["LinkedIn"]
                    elif plat_label == "Instagram" and "Instagram" in link_cols:
                        col_id = link_cols["Instagram"]
                    elif plat_label == "Twitter" and "Twitter" in link_cols:
                        col_id = link_cols["Twitter"]
                    elif plat_label == "TikTok" and "TikTok" in link_cols:
                        col_id = link_cols["TikTok"]
                    elif plat_label == "YT Full Length" and "YT Full" in link_cols:
                        col_id = link_cols["YT Full"]
                    elif plat_label == "YT Shorts" and "YT Short" in link_cols:
                        col_id = link_cols["YT Short"]

                    if col_id and url:
                        link_val = json.dumps({"url": url, "text": plat_label})
                        mut = '''mutation { change_column_value(
                            item_id: %s, board_id: %s,
                            column_id: "%s", value: "%s"
                        ) { id } }''' % (item_id, board_id, col_id, link_val.replace('"', '\\"'))
                        monday_mutate(mut)

    # Invalidate cache so next fetch gets fresh data
    with _cache["lock"]:
        _cache["last_fetch"] = 0

    return jsonify({
        "success": True,
        "item_id": item_id,
        "status": status_label,
        "found_links": found_links,
    })


# ─── Sprout Social Auto-Link Finder ──────────────────────────────────────────

SPROUT_API_KEY = os.environ.get("SPROUT_API_KEY", "")
SPROUT_CUSTOMER_ID = "2625468"

# Sprout profile IDs per platform
SPROUT_PROFILES = {
    "LinkedIn": "7074021",
    "Instagram": "7073666",
    "Twitter": "7071657",
    "TikTok": "7430178",
}

# YouTube Data API for YT matching
YT_API_KEY = os.environ.get("YT_API_KEY", "")
YT_CHANNEL_ID = "UCY6TEokyfC4sw--JMLoojDg"  # iConnections YouTube channel


def find_post_links(item_name, post_date, platforms, notes=""):
    """Find matching post URLs across platforms via Sprout Social + YouTube API."""
    found = {}

    # Build search keywords from item name
    keywords = item_name.lower().split()

    for platform in platforms:
        if platform in ("In-app Feed",):
            continue  # Skip non-linkable platforms

        if platform in ("YT Full Length", "YT Shorts"):
            url = _find_youtube_link(item_name, post_date, keywords, platform, notes=notes)
            if url:
                found[platform] = url
            continue

        profile_id = SPROUT_PROFILES.get(platform)
        if not profile_id:
            continue

        url = _find_sprout_link(profile_id, platform, item_name, post_date, keywords, notes)
        if url:
            found[platform] = url

    return found


def _find_sprout_link(profile_id, platform, item_name, post_date, keywords, notes=""):
    """Search Sprout Social for a matching post."""
    try:
        # Search ±3 days around the post date
        from datetime import datetime as dt
        d = dt.strptime(post_date, "%Y-%m-%d")
        start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
        end = (d + timedelta(days=4)).strftime("%Y-%m-%d")  # exclusive

        url = "https://api.sproutsocial.com/v1/%s/analytics/posts" % SPROUT_CUSTOMER_ID
        body = {
            "filters": [
                "customer_profile_id.eq(%s)" % profile_id,
                "created_time.in(%s...%s)" % (start, end),
            ],
            "metrics": ["lifetime.impressions"],
            "fields": ["created_time", "perma_link", "text"],
        }

        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": "Bearer " + SPROUT_API_KEY,
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        posts = result.get("data", [])

        if not posts:
            return None

        # Score each post by keyword match + date proximity
        best_url = None
        best_score = -1

        for p in posts:
            text = (p.get("text") or "").lower()
            link = p.get("perma_link", "")
            created = p.get("created_time", "")

            if not link:
                continue

            # Skip Instagram stories — they're ephemeral
            if "stories" in link:
                continue

            # Keyword matching score
            score = 0
            for kw in keywords:
                if len(kw) > 2 and kw in text:
                    score += 1

            # Bonus for date match
            if created and post_date in created:
                score += 3
            elif created:
                try:
                    cd = dt.strptime(created[:10], "%Y-%m-%d")
                    delta = abs((cd - dt.strptime(post_date, "%Y-%m-%d")).days)
                    if delta <= 1:
                        score += 2
                except:
                    pass

            if score > best_score:
                best_score = score
                best_url = link

        # Only return if we have a reasonable match (at least 2 keyword hits or date match)
        return best_url if best_score >= 2 else None

    except Exception as e:
        print(f"Sprout link finder error ({platform}): {e}")
        return None


def _parse_yt_duration(dur_str):
    """Parse ISO 8601 duration (PT1M30S) to seconds."""
    import re
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur_str or '')
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def _is_youtube_short(vid_id):
    """Check if a YouTube video is a Short by testing the /shorts/ URL.
    If /shorts/{id} stays at that URL → it's a Short.
    If it redirects to /watch?v= → it's a regular video."""
    try:
        url = "https://www.youtube.com/shorts/%s" % vid_id
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        resp = urllib.request.urlopen(req, timeout=8)
        final_url = resp.geturl()
        return "/shorts/" in final_url
    except Exception:
        # Fallback to duration-based guess if URL check fails
        return None


# Stopwords to exclude from keyword matching
_YT_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "of", "in", "to",
    "for", "with", "on", "at", "from", "by", "about", "as", "into",
    "through", "during", "before", "after", "above", "below", "and", "but",
    "or", "nor", "not", "so", "yet", "both", "either", "neither", "each",
    "every", "all", "any", "few", "more", "most", "other", "some", "such",
    "no", "only", "own", "same", "than", "too", "very", "just", "don",
    "now", "how", "why", "what", "when", "where", "who", "which", "that",
    "this", "these", "those", "it", "its", "he", "she", "we", "they",
    "his", "her", "our", "your", "their", "my", "me", "him", "us", "them",
    "up", "out", "get", "got", "new", "one", "two", "you", "i",
    # iConnections-specific stopwords (appear in nearly every title)
    "global", "alts", "miami", "2026", "2025", "iconnections",
}


def _yt_keyword_score(item_name, yt_title, yt_description="", notes=""):
    """Score how well a YouTube video matches a Monday item.
    Returns (score, details_str) where higher = better match."""
    import re
    # Build keyword set from item name (skip short words and stopwords)
    item_words = set(re.findall(r'[a-z0-9]+', item_name.lower())) - _YT_STOPWORDS
    item_words = {w for w in item_words if len(w) > 2}

    # Also extract 2-word phrases from item name for better matching
    # Only include bigrams where at least one word is NOT a stopword
    item_lower = item_name.lower()
    item_bigrams = set()
    words_list = re.findall(r'[a-z0-9]+', item_lower)
    for i in range(len(words_list) - 1):
        w1, w2 = words_list[i], words_list[i + 1]
        if w1 in _YT_STOPWORDS and w2 in _YT_STOPWORDS:
            continue  # Skip bigrams made entirely of stopwords
        bg = w1 + " " + w2
        item_bigrams.add(bg)

    yt_text = (yt_title + " " + yt_description).lower()

    # Score individual keyword hits in title (worth more) and description
    title_lower = yt_title.lower()
    score = 0
    matched = []

    for w in item_words:
        if w in title_lower:
            score += 3  # Title match is strong signal
            matched.append(f"+3 title:{w}")
        elif w in yt_text:
            score += 1  # Description match is weaker
            matched.append(f"+1 desc:{w}")

    # Bigram matches are very strong (catches "russell wilson", "real estate", etc.)
    for bg in item_bigrams:
        if bg in title_lower:
            score += 5
            matched.append(f"+5 bigram:{bg}")
        elif bg in yt_text:
            score += 2
            matched.append(f"+2 desc-bigram:{bg}")

    # Also check notes against YT title
    if notes:
        notes_words = set(re.findall(r'[a-z0-9]+', notes.lower())) - _YT_STOPWORDS
        notes_words = {w for w in notes_words if len(w) > 3} - item_words
        for w in notes_words:
            if w in title_lower:
                score += 2
                matched.append(f"+2 notes:{w}")

    return score, ", ".join(matched) if matched else "no matches"


def _find_youtube_link(item_name, post_date, keywords, platform, notes=""):
    """Search YouTube Data API for a matching video using smart matching.
    
    Strategy:
    1. Fetch ALL channel uploads for ±3 day window
    2. Get durations to filter shorts (<90s) vs full-length
    3. Score each video by keyword/bigram matching
    4. Auto-link only when confidence is high enough
    """
    try:
        from datetime import datetime as dt
        d = dt.strptime(post_date, "%Y-%m-%d")
        after = (d - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")
        before = (d + timedelta(days=4)).strftime("%Y-%m-%dT00:00:00Z")

        is_shorts = (platform == "YT Shorts")

        # Step 1: Get ALL channel videos in date range (no search query to avoid bias)
        params = urllib.parse.urlencode({
            "key": YT_API_KEY,
            "channelId": YT_CHANNEL_ID,
            "type": "video",
            "publishedAfter": after,
            "publishedBefore": before,
            "maxResults": 15,
            "part": "snippet",
            "order": "date",
        })
        url = "https://www.googleapis.com/youtube/v3/search?%s" % params
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())

        search_items = result.get("items", [])
        if not search_items:
            print(f"[YT] No videos found for date range around {post_date}")
            return None

        # Step 2: Get video details (duration) for all results
        vid_ids = [it.get("id", {}).get("videoId", "") for it in search_items if it.get("id", {}).get("videoId")]
        if not vid_ids:
            return None

        det_params = urllib.parse.urlencode({
            "key": YT_API_KEY,
            "id": ",".join(vid_ids),
            "part": "contentDetails,snippet",
        })
        det_url = "https://www.googleapis.com/youtube/v3/videos?%s" % det_params
        det_req = urllib.request.Request(det_url)
        det_resp = urllib.request.urlopen(det_req, timeout=15)
        det_result = json.loads(det_resp.read())

        # Step 3: Filter by short/full-length using URL-based detection + score
        candidates = []
        for v in det_result.get("items", []):
            vid_id = v["id"]
            dur_secs = _parse_yt_duration(v.get("contentDetails", {}).get("duration", ""))
            title = v.get("snippet", {}).get("title", "")
            desc = v.get("snippet", {}).get("description", "")
            pub_date = v.get("snippet", {}).get("publishedAt", "")[:10]

            # Determine if video is a Short via URL check (most reliable)
            # For efficiency, only check videos under 3 minutes (Shorts can't be longer)
            if dur_secs <= 180:
                vid_is_short = _is_youtube_short(vid_id)
                if vid_is_short is None:
                    # URL check failed — fall back to duration
                    vid_is_short = dur_secs < 90
            else:
                vid_is_short = False  # Over 3 min = definitely not a Short

            if is_shorts and not vid_is_short:
                continue
            if not is_shorts and vid_is_short:
                continue

            score, details = _yt_keyword_score(item_name, title, desc, notes)

            # Date proximity bonus
            if pub_date == post_date:
                score += 3
                details += ", +3 exact-date"
            elif abs((dt.strptime(pub_date, "%Y-%m-%d") - d).days) <= 1:
                score += 1
                details += ", +1 near-date"

            if is_shorts:
                link = "https://www.youtube.com/shorts/%s" % vid_id
            else:
                link = "https://www.youtube.com/watch?v=%s" % vid_id

            candidates.append({
                "vid_id": vid_id,
                "title": title,
                "url": link,
                "score": score,
                "details": details,
                "duration": dur_secs,
                "pub_date": pub_date,
            })

        if not candidates:
            type_str = "shorts" if is_shorts else "full-length"
            print(f"[YT] No {type_str} videos found for '{item_name}' around {post_date}")
            return None

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        # Log for debugging
        print(f"[YT] Matching '{item_name}' ({platform}) on {post_date}:")
        for c in candidates[:5]:
            dur_m = c['duration'] // 60
            dur_s = c['duration'] % 60
            print(f"  score={c['score']:3d}  {dur_m}:{dur_s:02d}  {c['title'][:60]}")
            print(f"         {c['details']}")

        # Confidence thresholds:
        # - If only 1 candidate of the right type, auto-link with score >= 1
        # - If multiple candidates, need score >= 5 AND 3+ point gap over #2
        if len(candidates) == 1:
            if best["score"] >= 1:
                print(f"[YT] ✅ Auto-linked (sole candidate): {best['url']}")
                return best["url"]
            else:
                print(f"[YT] ⚠️ Sole candidate but low score ({best['score']}), skipping")
                return None
        else:
            second = candidates[1]
            gap = best["score"] - second["score"]
            if best["score"] >= 5 and gap >= 3:
                print(f"[YT] ✅ Auto-linked (confident, gap={gap}): {best['url']}")
                return best["url"]
            else:
                print(f"[YT] ⚠️ Not confident enough (best={best['score']}, gap={gap}), skipping")
                return None

    except Exception as e:
        print(f"[YT] Link finder error: {e}")
        import traceback
        traceback.print_exc()
        return None


@social_cal_bp.route("/api/social-calendar/find-links", methods=["POST"])
def api_find_links():
    """Manually trigger link finding for an item (for batch backfill)."""
    if not FEATURE_AUTO_FIND_LINKS:
        return jsonify({
            "error": "Auto link-finding is disabled.",
            "reason": "Disabled by user (Molly) on 2026-05-04. Set FEATURE_AUTO_FIND_LINKS=True to re-enable.",
            "disabled": True,
        }), 503
    body = request.get_json()
    item_id = body.get("item_id")

    if not item_id:
        return jsonify({"error": "item_id required"}), 400

    # Get item from cache
    cached = get_cached_items()
    item_data = None
    board_id = SOCIAL_BOARD_ID
    for ci in cached:
        if ci["id"] == str(item_id):
            item_data = ci
            board_id = ci.get("board_id", SOCIAL_BOARD_ID)
            break

    if not item_data:
        return jsonify({"error": "Item not found"}), 404

    if not item_data.get("platforms"):
        return jsonify({"error": "No platforms checked"}), 400

    found_links = find_post_links(
        item_name=item_data["name"],
        post_date=item_data["date"],
        platforms=item_data["platforms"],
        notes=item_data.get("notes", ""),
    )

    # Write to Monday
    board_cfg = BOARDS.get(board_id, BOARDS[SOCIAL_BOARD_ID])
    link_cols = board_cfg.get("link_cols", {})
    written = {}
    for plat_label, url in found_links.items():
        col_id = None
        if plat_label == "LinkedIn" and "LinkedIn" in link_cols:
            col_id = link_cols["LinkedIn"]
        elif plat_label == "Instagram" and "Instagram" in link_cols:
            col_id = link_cols["Instagram"]
        elif plat_label == "Twitter" and "Twitter" in link_cols:
            col_id = link_cols["Twitter"]
        elif plat_label == "TikTok" and "TikTok" in link_cols:
            col_id = link_cols["TikTok"]
        elif plat_label == "YT Full Length" and "YT Full" in link_cols:
            col_id = link_cols["YT Full"]
        elif plat_label == "YT Shorts" and "YT Short" in link_cols:
            col_id = link_cols["YT Short"]

        if col_id and url:
            link_val = json.dumps({"url": url, "text": plat_label})
            mut = '''mutation { change_column_value(
                item_id: %s, board_id: %s,
                column_id: "%s", value: "%s"
            ) { id } }''' % (item_id, board_id, col_id, link_val.replace('"', '\\"'))
            monday_mutate(mut)
            written[plat_label] = url

    with _cache["lock"]:
        _cache["last_fetch"] = 0

    return jsonify({
        "success": True,
        "item_id": item_id,
        "found_links": found_links,
        "written_links": written,
    })


@social_cal_bp.route("/api/social-calendar/update-link", methods=["POST"])
def api_update_link():
    """Update a single platform link for an item on Monday.com."""
    body = request.get_json()
    item_id = body.get("item_id")
    platform = body.get("platform")  # e.g. "LinkedIn", "Instagram", etc.
    url_val = body.get("url", "").strip()
    board_id = body.get("board_id", SOCIAL_BOARD_ID)

    if not item_id or not platform:
        return jsonify({"error": "item_id and platform required"}), 400

    board_cfg = BOARDS.get(board_id, BOARDS[SOCIAL_BOARD_ID])
    link_cols = board_cfg.get("link_cols", {})

    # Map platform name to link column
    col_id = None
    plat_map = {
        "LinkedIn": "LinkedIn", "Instagram": "Instagram",
        "Twitter": "Twitter", "TikTok": "TikTok",
        "YT Full Length": "YT Full", "YT Shorts": "YT Short",
    }
    col_key = plat_map.get(platform, platform)
    col_id = link_cols.get(col_key)

    if not col_id:
        return jsonify({"error": "No link column found for platform: " + platform}), 400

    if url_val == "ig-story":
        # Special marker for Instagram Stories — no permanent link
        # Monday link columns need a URL, so we use a placeholder
        link_json = json.dumps({"url": "https://ig-story", "text": "ig-story"})
        mut = 'mutation { change_column_value(item_id: %s, board_id: %s, column_id: "%s", value: "%s") { id } }' % (
            item_id, board_id, col_id, link_json.replace('"', '\\"'))
    elif url_val:
        link_json = json.dumps({"url": url_val, "text": platform})
        mut = 'mutation { change_column_value(item_id: %s, board_id: %s, column_id: "%s", value: "%s") { id } }' % (
            item_id, board_id, col_id, link_json.replace('"', '\\"'))
    else:
        # Clear the link
        mut = 'mutation { change_column_value(item_id: %s, board_id: %s, column_id: "%s", value: "{}") { id } }' % (
            item_id, board_id, col_id)

    result = monday_mutate(mut)
    if result.get("errors"):
        return jsonify({"error": result["errors"][0].get("message", "Unknown")}), 500

    with _cache["lock"]:
        _cache["last_fetch"] = 0

    return jsonify({"success": True, "item_id": item_id, "platform": platform, "url": url_val})


@social_cal_bp.route("/api/social-calendar/suggest-links", methods=["POST"])
def api_suggest_links():
    """Return top candidate links for a missing platform link on an item."""
    body = request.get_json()
    item_id = body.get("item_id")
    platform = body.get("platform")  # e.g. "YT Full Length", "LinkedIn", etc.

    if not item_id or not platform:
        return jsonify({"error": "item_id and platform required"}), 400

    # Get item from cache
    cached = get_cached_items()
    item_data = None
    for ci in cached:
        if ci["id"] == str(item_id):
            item_data = ci
            break

    if not item_data:
        return jsonify({"error": "Item not found"}), 404

    post_date = item_data.get("date", "")
    item_name = item_data.get("name", "")
    notes = item_data.get("notes", "")

    candidates = _get_link_candidates(item_name, post_date, platform, notes)
    return jsonify({"candidates": candidates, "item_id": item_id, "platform": platform})


def _get_link_candidates(item_name, post_date, platform, notes=""):
    """Get top link candidates for a platform. Returns list of {url, title, date, score}."""
    import re
    from datetime import datetime as dt

    if not post_date:
        return []

    keywords = item_name.lower().split()

    if platform in ("YT Full Length", "YT Shorts"):
        return _get_yt_candidates(item_name, post_date, platform, notes)

    # Sprout Social platforms
    profile_id = SPROUT_PROFILES.get(platform)
    if not profile_id:
        return []

    try:
        d = dt.strptime(post_date, "%Y-%m-%d")
        start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
        end = (d + timedelta(days=4)).strftime("%Y-%m-%d")

        url = "https://api.sproutsocial.com/v1/%s/analytics/posts" % SPROUT_CUSTOMER_ID
        body = {
            "filters": [
                "customer_profile_id.eq(%s)" % profile_id,
                "created_time.in(%s...%s)" % (start, end),
            ],
            "metrics": ["lifetime.impressions"],
            "fields": ["created_time", "perma_link", "text"],
        }
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": "Bearer " + SPROUT_API_KEY,
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        posts = result.get("data", [])

        candidates = []
        for p in posts:
            text = (p.get("text") or "")
            link = p.get("perma_link", "")
            created = p.get("created_time", "")
            if not link or "stories" in link:
                continue

            # Score
            text_lower = text.lower()
            score = sum(1 for kw in keywords if len(kw) > 2 and kw in text_lower)
            if created and post_date in created:
                score += 3
            elif created:
                try:
                    cd = dt.strptime(created[:10], "%Y-%m-%d")
                    delta = abs((cd - d).days)
                    if delta <= 1:
                        score += 2
                except:
                    pass

            # Truncate caption for display
            preview = text[:120].replace("\n", " ")
            if len(text) > 120:
                preview += "..."

            candidates.append({
                "url": link,
                "title": preview,
                "date": created[:10] if created else "",
                "score": score,
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:5]

    except Exception as e:
        print(f"Suggest links error ({platform}): {e}")
        return []


def _get_yt_candidates(item_name, post_date, platform, notes=""):
    """Get top YouTube video candidates for a platform."""
    from datetime import datetime as dt

    try:
        d = dt.strptime(post_date, "%Y-%m-%d")
        after = (d - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")
        before = (d + timedelta(days=4)).strftime("%Y-%m-%dT00:00:00Z")
        is_shorts = (platform == "YT Shorts")

        # Get all channel videos in date range
        params = urllib.parse.urlencode({
            "key": YT_API_KEY, "channelId": YT_CHANNEL_ID,
            "type": "video", "publishedAfter": after, "publishedBefore": before,
            "maxResults": 15, "part": "snippet", "order": "date",
        })
        url = "https://www.googleapis.com/youtube/v3/search?%s" % params
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())

        search_items = result.get("items", [])
        if not search_items:
            return []

        vid_ids = [it["id"]["videoId"] for it in search_items if it.get("id", {}).get("videoId")]
        if not vid_ids:
            return []

        # Get durations
        det_params = urllib.parse.urlencode({
            "key": YT_API_KEY, "id": ",".join(vid_ids), "part": "contentDetails,snippet",
        })
        det_url = "https://www.googleapis.com/youtube/v3/videos?%s" % det_params
        det_resp = urllib.request.urlopen(urllib.request.Request(det_url), timeout=15)
        det_result = json.loads(det_resp.read())

        candidates = []
        for v in det_result.get("items", []):
            vid_id = v["id"]
            dur_secs = _parse_yt_duration(v.get("contentDetails", {}).get("duration", ""))
            title = v.get("snippet", {}).get("title", "")
            desc = v.get("snippet", {}).get("description", "")
            pub_date = v.get("snippet", {}).get("publishedAt", "")[:10]

            # Filter by type using URL check for short videos
            if dur_secs <= 180:
                vid_is_short = _is_youtube_short(vid_id)
                if vid_is_short is None:
                    vid_is_short = dur_secs < 90
            else:
                vid_is_short = False

            if is_shorts and not vid_is_short:
                continue
            if not is_shorts and vid_is_short:
                continue

            score, _ = _yt_keyword_score(item_name, title, desc, notes)
            if pub_date == post_date:
                score += 3

            dur_m = dur_secs // 60
            dur_s = dur_secs % 60

            if is_shorts:
                link = "https://www.youtube.com/shorts/%s" % vid_id
            else:
                link = "https://www.youtube.com/watch?v=%s" % vid_id

            candidates.append({
                "url": link,
                "title": title,
                "date": pub_date,
                "duration": "%d:%02d" % (dur_m, dur_s),
                "score": score,
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:5]

    except Exception as e:
        print(f"YT suggest error: {e}")
        return []


@social_cal_bp.route("/api/social-calendar/asset/<asset_id>")
def api_asset_proxy(asset_id):
    """Proxy for Monday.com file assets. Fetches a fresh signed URL on each request
    so images never expire in the browser."""
    from flask import Response
    # Query Monday for a fresh public URL for this asset
    query = '{ assets(ids: [%s]) { public_url name file_extension } }' % asset_id
    result = monday_query(query)
    assets = (result.get("data") or {}).get("assets", [])
    if not assets:
        return jsonify({"error": "Asset not found"}), 404

    asset = assets[0]
    public_url = asset.get("public_url", "")
    if not public_url:
        return jsonify({"error": "No public URL available"}), 404

    # Check if download mode requested
    is_download = request.args.get("download") == "1"
    filename = asset.get("name", f"asset-{asset_id}")

    # Fetch the actual file content and proxy it through
    try:
        req = urllib.request.Request(public_url, headers={
            "User-Agent": "iConnections-Dashboard/1.0"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            headers = {"Cache-Control": "public, max-age=300"}
            if is_download:
                headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            return Response(content, content_type=content_type, headers=headers)
    except Exception as e:
        print(f"Asset proxy error for {asset_id}: {e}")
        return jsonify({"error": "Failed to fetch asset"}), 502


@social_cal_bp.route("/api/social-calendar/analyze-speaker-image", methods=["POST"])
def api_analyze_speaker_image():
    """Analyze a speaker announcement graphic to extract name, title, firm, and type.
    Uses OpenAI GPT-4o-mini vision. Requires OPENAI_API_KEY env var."""
    if not OPENAI_API_KEY:
        return jsonify({"error": "No OpenAI API key configured. Set OPENAI_API_KEY env var to enable image analysis.", "needs_key": True}), 400

    body = request.get_json()
    asset_id = body.get("asset_id")
    if not asset_id:
        return jsonify({"error": "No asset_id provided"}), 400

    try:
        # 1. Get fresh public URL from Monday.com
        query = '{ assets(ids: [%s]) { public_url name file_extension } }' % asset_id
        result = monday_query(query)
        assets_data = (result.get("data") or {}).get("assets", [])
        if not assets_data:
            return jsonify({"error": "Asset not found on Monday.com"}), 404

        public_url = assets_data[0].get("public_url", "")
        if not public_url:
            return jsonify({"error": "No public URL for asset"}), 404

        # 2. Download the image
        req = urllib.request.Request(public_url, headers={"User-Agent": "iConnections-Dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            image_bytes = resp.read()
            content_type = resp.headers.get("Content-Type", "image/png")

        # 3. Base64 encode for OpenAI vision
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # 4. Call OpenAI GPT-4o-mini vision
        vision_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this speaker announcement graphic. Extract:
1. Speaker name
2. Their title/role
3. Their firm/company name
4. Whether it says "Confirmed Speaker" or "Fireside Spotlight" (or similar wording)

Return ONLY a JSON object with these keys: name, title, firm, speaker_type
For speaker_type use exactly "confirmed" or "fireside".
If you can't determine a field, use an empty string.
Return ONLY the JSON, no other text."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{b64_image}",
                            "detail": "low"  # Low detail is cheaper and sufficient for text extraction
                        }
                    }
                ]
            }],
            "max_tokens": 200,
            "temperature": 0,
        }).encode("utf-8")

        api_req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=vision_body,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
        )
        with urllib.request.urlopen(api_req, timeout=30) as api_resp:
            api_data = json.loads(api_resp.read())

        # 5. Parse the response
        content = api_data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        speaker_info = json.loads(content)
        return jsonify({
            "success": True,
            "speaker_info": {
                "name": speaker_info.get("name", ""),
                "title": speaker_info.get("title", ""),
                "firm": speaker_info.get("firm", ""),
                "speaker_type": speaker_info.get("speaker_type", "confirmed"),
            }
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse vision response: {e}", "raw": content if 'content' in dir() else ""}), 500
    except Exception as e:
        print(f"Speaker image analysis error: {e}")
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500


@social_cal_bp.route("/api/social-calendar/vision-status")
def api_vision_status():
    """Check if vision/image analysis is available."""
    return jsonify({"available": bool(OPENAI_API_KEY)})


@social_cal_bp.route("/api/social-calendar/analyze-image", methods=["POST"])
def api_analyze_image():
    """Analyze any social media graphic to extract what it's about.
    Returns a content description that should be used for caption generation
    instead of the internal Monday.com item name."""
    if not OPENAI_API_KEY:
        return jsonify({"error": "No OpenAI API key configured.", "needs_key": True}), 400

    body = request.get_json()
    asset_id = body.get("asset_id")
    post_type = body.get("post_type", "")
    if not asset_id:
        return jsonify({"error": "No asset_id provided"}), 400

    try:
        # Fetch asset from Monday.com
        query = '{ assets(ids: [%s]) { public_url name file_extension } }' % asset_id
        result = monday_query(query)
        assets_data = (result.get("data") or {}).get("assets", [])
        if not assets_data:
            return jsonify({"error": "Asset not found"}), 404

        public_url = assets_data[0].get("public_url", "")
        if not public_url:
            return jsonify({"error": "No public URL"}), 404

        req = urllib.request.Request(public_url, headers={"User-Agent": "iConnections-Dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            image_bytes = resp.read()
            content_type = resp.headers.get("Content-Type", "image/png")

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        result_text = _call_llm_vision(
            "You analyze social media graphics for iConnections (a platform connecting allocators and managers in alternative investments).",
            f"""Analyze this social media graphic. Extract ALL visible text and what it's promoting.

Post type context: {post_type}

Return ONLY a JSON object with these keys:
- "headline": the main headline or title shown on the graphic
- "subtitle": any subtitle or secondary text
- "description": a brief 1-sentence description of what this graphic is promoting/announcing
- "speaker_name": if this is a speaker graphic, the speaker's name (empty string if not a speaker graphic)
- "speaker_title": speaker's title/role (empty string if N/A)
- "speaker_firm": speaker's company (empty string if N/A)
- "speaker_type": "confirmed" or "fireside" (empty string if not a speaker graphic)
- "partners": any co-branding partners shown (e.g. "J.P. Morgan Asset Management")

Return ONLY valid JSON, no other text.""",
            b64_image, content_type, max_tokens=400
        )

        if not result_text:
            return jsonify({"error": "Vision analysis failed — no API key or service unavailable."}), 500

        # Parse JSON from response
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        image_data = json.loads(result_text)
        return jsonify({"success": True, "image_data": image_data})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse: {e}"}), 500
    except Exception as e:
        print(f"Image analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@social_cal_bp.route("/api/social-calendar/generate-caption", methods=["POST"])
def api_generate_caption():
    """Generate AI captions for a post. This endpoint returns suggested captions
    for each platform the post is going on."""
    if not FEATURE_AI_CAPTIONS:
        return jsonify({
            "error": "AI caption generation is disabled.",
            "reason": "Disabled by user (Molly) on 2026-05-04. Set FEATURE_AI_CAPTIONS=True to re-enable.",
            "disabled": True,
            "captions": {},
        }), 503
    body = request.get_json()
    item_name = body.get("name", "")
    post_type = body.get("post_type", "")
    group_name = body.get("group_name", "")
    platforms = body.get("platforms", [])
    notes = body.get("notes", "")
    refinement = body.get("refinement", "")  # Optional: user feedback for refining
    image_info = body.get("image_info")  # Optional: speaker details from image analysis
    image_data = body.get("image_data")  # Optional: general image content from analysis

    if not platforms:
        return jsonify({"error": "No platforms specified"}), 400

    # If image_data was provided (from analyze-image), use LLM to generate captions
    # based on what's actually ON the graphic, not the internal item name
    if image_data and isinstance(image_data, dict) and image_data.get("headline"):
        captions = _generate_captions_from_image_data(
            image_data, item_name, post_type, group_name, notes, platforms, image_info
        )
        return jsonify({"captions": captions})

    captions = {}
    for platform in platforms:
        caption = _generate_caption_for_platform(
            platform, item_name, post_type, group_name, notes, refinement, image_info
        )
        if isinstance(caption, dict):
            captions[platform] = caption
        else:
            captions[platform] = caption

    return jsonify({"captions": captions})


# ─── LLM Config for Refinement & Vision ───────────────────────────────────────
REFINE_MODEL = os.environ.get("REFINE_MODEL", "openai/gpt-4o-mini")
# OpenClaw Gateway — local LLM proxy (uses whatever providers are configured in OpenClaw)
OPENCLAW_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
OPENCLAW_GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")


def _call_llm(system_prompt, user_prompt, max_tokens=500):
    """Call an LLM for caption generation/refinement.
    Uses direct OpenAI API. Requires OPENAI_API_KEY env var.

    Note: We deliberately do NOT use the OpenClaw Gateway's /v1/chat/completions
    endpoint because it routes through a full agent pipeline (with system prompts,
    bootstrap files, memory, etc.) which makes it unsuitable for plain LLM calls.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenAI direct LLM call error: {e}")
        return None


def _call_llm_vision(system_prompt, user_prompt, image_b64, content_type="image/png", max_tokens=500):
    """Call an LLM with vision (image analysis). Tries OpenAI first (needs key), then gateway."""

    # OpenAI vision (direct — most reliable for vision)
    if OPENAI_API_KEY:
        try:
            body = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{system_prompt}\n\n{user_prompt}"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{content_type};base64,{image_b64}",
                            "detail": "low"
                        }}
                    ]
                }],
                "max_tokens": max_tokens,
                "temperature": 0,
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenAI vision call error: {e}")

    return None


def _rule_based_refine(caption, feedback, platform):
    """Fallback rule-based refinement when no LLM API key is available.
    Handles common feedback patterns."""
    feedback_lower = feedback.lower().strip()
    lines = caption.strip().split("\n")

    # "shorter" / "more concise" / "trim"
    if any(w in feedback_lower for w in ["shorter", "concise", "trim", "cut", "brief"]):
        # Keep first line (hook), last line (tags), and any reg links. Remove filler.
        important = []
        for line in lines:
            l = line.strip()
            if not l:
                continue
            # Keep: hook (first non-empty), reg links, tag lines, link in bio / tap the link in our story
            if l.startswith("Manager Reg") or l.startswith("Investor Reg") or l.startswith("Register"):
                important.append(l)
            elif l.startswith("#") or l.startswith("@"):
                important.append(l)
            elif l == "Link in bio 👆" or l.startswith("Tap the link in our story") or l.startswith("."):
                important.append(l)
            elif not important:
                important.append(l)  # first line = hook
        return "\n".join(important)

    # "add emoji" / "more emojis"
    if any(w in feedback_lower for w in ["emoji", "emojis"]):
        import random
        emojis = ["🔥", "✨", "🚀", "💡", "⭐", "🎯", "📈", "💪"]
        if lines:
            lines[0] = lines[0] + " " + random.choice(emojis)
        return "\n".join(lines)

    # "more urgent" / "urgency"
    if any(w in feedback_lower for w in ["urgent", "urgency", "fomo"]):
        urgency_adds = [
            "Spots are filling fast.",
            "Don't wait — seats are limited.",
            "The window is closing. Act now.",
        ]
        import random
        # Insert urgency line after the hook
        if len(lines) > 1:
            lines.insert(1, random.choice(urgency_adds))
        else:
            lines.append(random.choice(urgency_adds))
        return "\n".join(lines)

    # "more casual" / "less formal"
    if any(w in feedback_lower for w in ["casual", "informal", "less formal", "relaxed"]):
        text = caption
        text = text.replace("We are excited to welcome", "Excited to have")
        text = text.replace("We are thrilled to welcome", "Thrilled to have")
        text = text.replace("We are pleased to welcome", "Stoked to welcome")
        text = text.replace("We are delighted to announce", "Big news:")
        text = text.replace("We are thrilled to announce that", "Big announcement:")
        text = text.replace("We are excited to announce that", "Exciting news:")
        return text

    # If we can't handle it rule-based, return None to signal failure
    return None


@social_cal_bp.route("/api/social-calendar/refine-caption", methods=["POST"])
def api_refine_caption():
    """Refine an existing caption using AI based on user feedback.
    Uses OpenAI if API key is available, otherwise falls back to rule-based refinement."""
    if not FEATURE_AI_CAPTIONS:
        return jsonify({
            "error": "AI caption refinement is disabled.",
            "reason": "Disabled by user (Molly) on 2026-05-04. Set FEATURE_AI_CAPTIONS=True to re-enable.",
            "disabled": True,
        }), 503
    body = request.get_json()
    current_caption = body.get("caption", "")
    feedback = body.get("feedback", "")
    platform = body.get("platform", "")
    post_type = body.get("post_type", "")

    if not current_caption or not feedback:
        return jsonify({"error": "Caption and feedback are required"}), 400

    system_prompt = f"""You are a social media copywriter for iConnections, the leading platform connecting allocators and managers in alternative investments.

Your job: rewrite the caption below based on the user's feedback. Keep the same general message, links, and tags, but adjust the tone, length, structure, or wording as requested.

Rules:
- Maximum 5 hashtags total (count any in the body too). #iConnections must always be the first hashtag.
- Keep any @MFA / @MFAupdates / @mfa_alts tags that are present.
- Keep any registration links that are present.
- Platform: {platform}
{"- Twitter: max 280 characters for tweets." if platform == "Twitter" else ""}
- Do NOT add explanatory text or notes. Return ONLY the refined caption text, ready to copy-paste.
- Do not wrap in quotes or markdown."""

    user_prompt = f"""Current caption:
{current_caption}

Feedback: {feedback}

Rewrite the caption based on this feedback. Return ONLY the new caption text."""

    # Try LLM-based refinement first (real AI rewrite, requires OPENAI_API_KEY)
    refined = _call_llm(system_prompt, user_prompt)
    if refined:
        return jsonify({"caption": refined, "method": "ai"})

    # Fallback: rule-based refinement (handles common patterns: shorter, casual, urgency, emoji)
    refined = _rule_based_refine(current_caption, feedback, platform)
    if refined and refined != current_caption:
        return jsonify({"caption": refined, "method": "rule"})

    # Nothing worked
    if not OPENAI_API_KEY:
        return jsonify({
            "error": "AI refinement isn't set up yet. Try simple rule-based feedback: 'shorter', 'more casual', 'add urgency', or 'add emoji'. For full AI refinement, an OpenAI API key needs to be added (one-time setup).",
            "needs_key": True,
        }), 400
    return jsonify({
        "error": "Refinement failed. Try more specific feedback like: 'shorter', 'more casual', 'add urgency', or 'add emoji'.",
    }), 400


# ─── Ask Nick (Slack-routed AI captions) ─────────────────────────────────────
# When OpenAI/local LLM isn't available, route caption requests to Nick via Slack.
# Flow: dashboard creates request JSON → posts Slack message to Nick → Nick writes
# caption back to results JSON → dashboard polls results endpoint and auto-fills.

NICK_QUEUE_DIR = "/tmp/iconnections-nick-queue"
NICK_RESULTS_DIR = "/tmp/iconnections-nick-results"
os.makedirs(NICK_QUEUE_DIR, exist_ok=True)
os.makedirs(NICK_RESULTS_DIR, exist_ok=True)

# OpenClaw's Slack bot token — used to ping Nick when a caption request comes in.
# Falls back to the bot token configured in OpenClaw's channels.slack.botToken.
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
# Where caption requests are sent. Default: DM Molly (U0801RGF87P) directly so the
# rest of the team doesn't see the dashboard pings. Override with SLACK_NICK_DM_CHANNEL
# env var (can be a user ID for DM or a channel ID).
SLACK_NICK_DM_CHANNEL = os.environ.get("SLACK_NICK_DM_CHANNEL", "U0801RGF87P")


def _post_slack_message_to_nick(text):
    """Post a message to Nick via Slack so he can pick up a caption request.
    Uses the Slack bot token configured in OpenClaw."""
    if not SLACK_BOT_TOKEN or not SLACK_NICK_DM_CHANNEL:
        return False
    try:
        body = json.dumps({
            "channel": SLACK_NICK_DM_CHANNEL,
            "text": text,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=body,
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json; charset=utf-8",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("ok", False)
    except Exception as e:
        print(f"Slack post error: {e}")
        return False


@social_cal_bp.route("/api/social-calendar/ask-nick", methods=["POST"])
def api_ask_nick():
    """Submit a caption request to Nick via Slack. Returns a request_id the dashboard
    can poll for the result. Nick (the agent) reads the Slack message, writes the
    caption, and saves it to the results directory."""
    if not FEATURE_AI_CAPTIONS:
        return jsonify({
            "error": "Ask-Nick caption requests are disabled.",
            "reason": "Disabled by user (Molly) on 2026-05-04. Set FEATURE_AI_CAPTIONS=True to re-enable.",
            "disabled": True,
        }), 503
    body = request.get_json()
    request_type = body.get("type", "refine")
    current_caption = body.get("caption", "")
    feedback = body.get("feedback", "")
    platform = body.get("platform", "")
    post_type = body.get("post_type", "")
    item_name = body.get("item_name", "")
    group_name = body.get("group_name", "")
    notes = body.get("notes", "")
    image_data = body.get("image_data")

    request_id = hashlib.sha256(f"{time.time()}-{item_name}-{platform}-{feedback}".encode()).hexdigest()[:12]
    result_path = os.path.join(NICK_RESULTS_DIR, f"{request_id}.json")
    queue_path = os.path.join(NICK_QUEUE_DIR, f"{request_id}.json")

    request_data = {
        "id": request_id,
        "type": request_type,
        "caption": current_caption,
        "feedback": feedback,
        "platform": platform,
        "post_type": post_type,
        "item_name": item_name,
        "group_name": group_name,
        "notes": notes,
        "image_data": image_data,
        "created_at": time.time(),
    }
    with open(queue_path, "w") as f:
        json.dump(request_data, f, indent=2)

    # Build a clear Slack message for Nick. The format makes it easy for Nick to
    # see what's needed and respond by writing the caption to result_path.
    if request_type == "refine":
        slack_text = (
            f"🤖 *Caption refine request* (id: `{request_id}`)\n"
            f"*Platform:* {platform} — *Post:* {item_name} ({post_type})\n"
            f"*Feedback:* {feedback}\n\n"
            f"*Current caption:*\n```\n{current_caption}\n```\n\n"
            f"Nick: rewrite the caption per the feedback (keep the 5-hashtag rule, MFA tag if event post, links). "
            f"Save the result with:\n"
            f"```\necho '{{\"caption\": \"YOUR REWRITTEN CAPTION HERE\"}}' > {result_path}\n```\n"
            f"Or write the file directly. The dashboard is polling."
        )
    else:
        ctx = f"item: {item_name} | post_type: {post_type} | group: {group_name}"
        if notes:
            ctx += f" | notes: {notes}"
        if image_data:
            ctx += f"\nimage content: {json.dumps(image_data)}"
        slack_text = (
            f"🤖 *Caption generate request* (id: `{request_id}`)\n"
            f"*Platform:* {platform}\n"
            f"*Context:* {ctx}\n\n"
            f"Nick: write a {platform} caption for this. Follow the 5-hashtag rule, MFA tag if event post. "
            f"Save the result with:\n"
            f"```\necho '{{\"caption\": \"YOUR CAPTION HERE\"}}' > {result_path}\n```"
        )

    posted = _post_slack_message_to_nick(slack_text)

    return jsonify({
        "request_id": request_id,
        "status": "pending",
        "slack_posted": posted,
        "message": "Sent to Nick on Slack..." if posted else "Slack notification failed.",
    })


@social_cal_bp.route("/api/social-calendar/ask-nick-status/<request_id>")
def api_ask_nick_status(request_id):
    """Poll for the result of an 'ask-nick' caption request."""
    if not all(c in "0123456789abcdef" for c in request_id):
        return jsonify({"error": "Invalid request_id"}), 400

    result_path = os.path.join(NICK_RESULTS_DIR, f"{request_id}.json")
    queue_path = os.path.join(NICK_QUEUE_DIR, f"{request_id}.json")

    if os.path.exists(result_path):
        try:
            with open(result_path) as f:
                result = json.load(f)
            return jsonify({
                "status": "done",
                "caption": result.get("caption", ""),
            })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    if not os.path.exists(queue_path):
        return jsonify({"status": "error", "error": "Request not found"}), 404

    return jsonify({"status": "pending"})


def _generate_captions_from_image_data(image_data, item_name, post_type, group_name, notes, platforms, image_info=None):
    """Generate captions using LLM based on what's actually on the graphic.
    Used when the image has been analyzed and we have its real content."""

    # For Speaker posts with image_data that has speaker info, route to speaker templates
    if post_type in ("Speaker", "Panel") and image_data.get("speaker_name"):
        speaker_image_info = {
            "name": image_data.get("speaker_name", ""),
            "title": image_data.get("speaker_title", ""),
            "firm": image_data.get("speaker_firm", ""),
            "speaker_type": image_data.get("speaker_type", "confirmed"),
        }
        # Merge with any manual overrides from image_info
        if image_info:
            for k, v in image_info.items():
                if v:
                    speaker_image_info[k] = v

        captions = {}
        for platform in platforms:
            cap = _generate_caption_for_platform(
                platform, item_name, post_type, group_name, notes, "", speaker_image_info
            )
            captions[platform] = cap
        return captions

    # For Milestones, still use the template engine
    if post_type == "Milestones":
        captions = {}
        for platform in platforms:
            cap = _generate_caption_for_platform(
                platform, item_name, post_type, group_name, notes, "")
            captions[platform] = cap
        return captions

    # For all other post types: use LLM to write captions based on the image content
    _event_key, event_cfg = _get_event_config(group_name)
    is_event = _event_key is not None

    # Build context for the LLM
    headline = image_data.get("headline", "")
    subtitle = image_data.get("subtitle", "")
    description = image_data.get("description", "")
    partners = image_data.get("partners", "")

    # Check for content-specific CTA (e.g. Global Allocator Report)
    content_cta = _get_content_cta(
        item_name=item_name, image_headline=headline,
        image_description=description, notes=notes,
    )

    reg_links = ""
    if content_cta:
        # Content-specific CTA takes precedence over event registration links
        reg_links += f"\n{content_cta['label']}: {content_cta['url']}"
    elif event_cfg:
        if event_cfg.get("manager_reg"):
            reg_links += f"\nManager Registration: {event_cfg['manager_reg']}"
        if event_cfg.get("investor_reg_url"):
            reg_links += f"\nInvestor Registration: {event_cfg['investor_reg_url']}"

    image_context = f"Headline on graphic: {headline}"
    if subtitle:
        image_context += f"\nSubtitle: {subtitle}"
    if description:
        image_context += f"\nWhat it's promoting: {description}"
    if partners:
        image_context += f"\nCo-branding partners: {partners}"
    if notes:
        image_context += f"\nInternal notes: {notes}"

    captions = {}
    for platform in platforms:
        mfa_tag = _get_mfa_tag(platform) if is_event else ""
        hashtag_block = _build_hashtag_block(platform, event_hashtag_in_body=False,
            extra_tags=["#AlternativeInvestments", "#PrivateMarkets", "#InvestmentLeadership"])
        tag_line = f"{mfa_tag} {hashtag_block}".strip() if mfa_tag else hashtag_block

        platform_rules = f"Platform: {platform}"
        if platform == "Twitter":
            platform_rules += "\n- Max 280 characters. No links in the tweet."
        elif platform == "Instagram":
            ig_cta = _build_instagram_cta(content_cta, fallback_action="learn more")
            platform_rules += f"\n- Include this CTA line before hashtags: '{ig_cta}'"
            platform_rules += "\n- Do NOT include the URL in the body — IG doesn't support clickable links."
        elif platform == "TikTok":
            platform_rules += "\n- Short, punchy, with relevant hashtags."

        system_prompt = f"""You are a social media copywriter for iConnections, the leading platform connecting allocators and managers in alternative investments.

Write a caption for this social media post based on what's shown in the graphic (NOT the internal item name).

{platform_rules}

Rules:
- Base the caption on the graphic content below, NOT internal titles like "prospect launch" or "members launch"
- Use the actual headline/title shown on the graphic
- Tone: professional but energetic, not corporate-speak
- End with these tags on their own line: {tag_line}
{f'- Include these registration links:' + reg_links if reg_links else ''}
- Do NOT add explanatory notes. Return ONLY the caption text, ready to copy-paste.
- Do not wrap in quotes or markdown."""

        user_prompt = f"""Post type: {post_type}
{image_context}

Write the {platform} caption."""

        llm_caption = _call_llm(system_prompt, user_prompt, max_tokens=400)

        if llm_caption:
            captions[platform] = llm_caption
        else:
            # Fallback to template if LLM fails
            captions[platform] = _generate_caption_for_platform(
                platform, headline or item_name, post_type, group_name, notes, "")

    return captions


# ─── Speaker Announcement Templates (Molly's confirmed templates) ─────────────

import random as _random

_SPEAKER_ANNOUNCEMENT_EMOJIS = ["📣", "🎤", "🔊", "✨", "🌟", "⭐", "🎯", "💡", "🏆", "📢"]
_SPEAKER_INTRO_PHRASES = [
    "We are excited to welcome",
    "We are thrilled to welcome",
    "We are pleased to welcome",
    "We are delighted to announce",
    "We are proud to welcome",
]
_FIRESIDE_INTRO_PHRASES = [
    "We are thrilled to announce that",
    "We are excited to announce that",
    "We are pleased to share that",
    "We are delighted to announce that",
]

# Event-specific registration links & hashtags
_EVENT_CONFIG = {
    "GANY": {
        "hashtag": "#GlobalAltsNewYork",
        "year": "2026",
        "manager_reg": "https://share.hsforms.com/11g1Qy5nVTxCacJXZGdYe0A4rr50",
        "investor_reg_display": "iconn.cc/GANY-2026",
        "investor_reg_url": "http://iconn.cc/GANY-2026",
    },
    "GAAS": {
        "hashtag": "#GlobalAltsAsia",
        "year": "2026",
        "manager_reg": "",
        "investor_reg_display": "iconn.cc/GAAS-2026",
        "investor_reg_url": "http://iconn.cc/GAAS-2026",
    },
    "GAMI": {
        "hashtag": "#GlobalAltsMiami",
        "year": "2027",
        "manager_reg": "",
        "investor_reg_display": "iconn.cc/GAMI-2027",
        "investor_reg_url": "http://iconn.cc/GAMI-2027",
    },
    "GAEU": {
        "hashtag": "#GlobalAltsEurope",
        "year": "2027",
        "manager_reg": "",
        "investor_reg_display": "iconn.cc/GAEU-2027",
        "investor_reg_url": "http://iconn.cc/GAEU-2027",
    },
}

# ─── Hashtag & Tagging Rules (Molly's confirmed rules) ────────────────────────
# 1. Total hashtag count per post: MAX 5 (including any used mid-sentence)
# 2. #iConnections always comes FIRST in the hashtag block
# 3. All Global Alts flagship event posts must tag MFA at the end
# 4. MFA handles per platform:
#    - LinkedIn: @MFA
#    - Twitter/X: @MFAupdates
#    - Instagram: @mfa_alts
#    Other platforms: @MFA (default)

_MFA_TAG = {
    "LinkedIn": "@MFA",
    "Twitter": "@MFAupdates",
    "Instagram": "@mfa_alts",
    "TikTok": "@MFA",
    "YT Full Length": "",
    "YT Shorts": "",
    "In-app Feed": "",
}

def _get_mfa_tag(platform):
    """Get the MFA tag for a given platform. Empty string for platforms that don't need it."""
    return _MFA_TAG.get(platform, "@MFA")

def _build_hashtag_block(platform, event_hashtag_in_body=False, extra_tags=None):
    """Build a hashtag block respecting the 5-hashtag limit.
    
    Args:
        platform: target platform
        event_hashtag_in_body: True if the event hashtag (e.g. #GlobalAltsNewYork) is already used in the caption body
        extra_tags: list of additional hashtags to consider (after #iConnections)
    
    Returns: string of hashtags, max 5 total (accounting for any in-body hashtag)
    """
    max_tags = 5
    used_in_body = 1 if event_hashtag_in_body else 0
    remaining = max_tags - used_in_body

    # #iConnections always first
    tags = ["#iConnections"]

    # Platform-appropriate extras
    default_extras = ["#AlternativeInvestments", "#InvestmentLeadership", "#PrivateMarkets"]
    if extra_tags:
        pool = extra_tags
    else:
        pool = default_extras

    for tag in pool:
        if len(tags) >= remaining:
            break
        if tag not in tags:
            tags.append(tag)

    return " ".join(tags)


_SPEAKER_SOCIAL_TAGS_LEGACY = "@MFAupdates #iConnections #AlternativeInvestments #InvestmentLeadership"  # kept for reference only


def _detect_speaker_type(item_name, notes="", image_info=None):
    """Detect whether this is a confirmed speaker or fireside spotlight.
    Returns: 'fireside' or 'confirmed'"""
    if image_info and image_info.get("speaker_type"):
        return image_info["speaker_type"]
    combined = f"{item_name} {notes}".lower()
    if "fireside" in combined or "spotlight" in combined or "fireside spotlight" in combined:
        return "fireside"
    return "confirmed"


def _extract_speaker_info(item_name, notes="", image_info=None):
    """Extract speaker name, title, and firm.
    Priority: image_info (from vision analysis) > notes > item_name parsing."""
    info = {
        "name": item_name.strip(),
        "title": "",
        "firm": "",
    }

    # If image analysis provided structured data, use it
    if image_info:
        if image_info.get("name"):
            info["name"] = image_info["name"]
        if image_info.get("title"):
            info["title"] = image_info["title"]
        if image_info.get("firm"):
            info["firm"] = image_info["firm"]
        return info

    # Clean item name: remove annotations like "(add chainsmokers mention)" and "- fireside"
    name = item_name.strip()
    # Remove fireside / spotlight suffix
    for suffix in [" - fireside", " -fireside", " – fireside", " fireside spotlight", " - spotlight"]:
        if name.lower().endswith(suffix.lower()):
            name = name[:len(name)-len(suffix)].strip()
    # Remove parenthetical notes
    import re as _re
    name = _re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
    info["name"] = name

    # Try to extract title and firm from notes
    if notes:
        # Common patterns: "Title at Firm", "Title, Firm"
        notes_clean = notes.strip()
        if " at " in notes_clean:
            parts = notes_clean.split(" at ", 1)
            info["title"] = parts[0].strip()
            info["firm"] = parts[1].strip()
        elif ", " in notes_clean and len(notes_clean.split(", ")) >= 2:
            parts = notes_clean.split(", ")
            # Heuristic: if last part looks like a firm name
            info["title"] = ", ".join(parts[:-1]).strip()
            info["firm"] = parts[-1].strip()

    return info


def _get_event_config(group_name):
    """Get event config from group name."""
    for key, cfg in _EVENT_CONFIG.items():
        if key in group_name:
            return key, cfg
    return None, None


# ─── Content-specific CTA links (Molly's confirmed mappings) ───────────────────────
# When a post is about specific content (reports, products, etc.), use the matching
# CTA link instead of (or in addition to) generic event registration links.
# Match keys are lowercase substrings checked against item_name + image_data.headline + notes.
# action_verb is the verb phrase that completes "Tap the link in our story to ___"
# (e.g. "read the report", "register now", "watch the full episode")
_CONTENT_CTA_LINKS = [
    {
        "match": ["global allocator report", "allocator report", "global allocator report 2026"],
        "label": "Read the report",
        "action_verb": "read the full report",
        "url": "https://iconnections.io/insights/global-allocator-report-2026/",
        "name": "Global Allocator Report",
    },
]


def _get_content_cta(item_name="", image_headline="", image_description="", notes=""):
    """Find a content-specific CTA link based on item name, image content, or notes.
    Returns dict with {label, url, name, action_verb} or None."""
    haystack = " ".join([item_name or "", image_headline or "", image_description or "", notes or ""]).lower()
    for entry in _CONTENT_CTA_LINKS:
        for match in entry["match"]:
            if match.lower() in haystack:
                return entry
    return None


def _build_instagram_cta(content_cta=None, fallback_action="learn more"):
    """Build the Instagram CTA line. Format: 'Tap the link in our story to [action]'.
    Per Molly: most posts get reposted to story with the link, so this is the
    canonical CTA for IG instead of 'Link in bio'.
    """
    if content_cta and content_cta.get("action_verb"):
        return f"Tap the link in our story to {content_cta['action_verb']} 👆"
    return f"Tap the link in our story to {fallback_action} 👆"


def _build_speaker_caption_confirmed(speaker_info, event_key, event_cfg, platform):
    """Build confirmed speaker caption using Molly's template."""
    emoji = _random.choice(_SPEAKER_ANNOUNCEMENT_EMOJIS)
    intro = _random.choice(_SPEAKER_INTRO_PHRASES)
    name = speaker_info["name"]
    title = speaker_info["title"]
    firm = speaker_info["firm"]

    # Build the name + title string
    if title and firm:
        speaker_str = f"{name}, {title} at {firm},"
    elif firm:
        speaker_str = f"{name} from {firm}"
    elif title:
        speaker_str = f"{name}, {title},"
    else:
        speaker_str = name

    event_hashtag = event_cfg["hashtag"] if event_cfg else "#GlobalAlts"
    year = event_cfg["year"] if event_cfg else "2026"
    mfa_tag = _get_mfa_tag(platform)

    # event_hashtag is used in the body, so it counts toward the 5-hashtag limit
    hashtag_block = _build_hashtag_block(platform, event_hashtag_in_body=True,
        extra_tags=["#AlternativeInvestments", "#InvestmentLeadership", "#PrivateMarkets"])

    base_text = f"{emoji} {intro} {speaker_str} to the {event_hashtag} {year} stage as a confirmed speaker!"

    if platform == "Twitter":
        main_tweet = f"{base_text}\n{mfa_tag} {hashtag_block}".strip()
        return main_tweet
    else:
        manager_link = event_cfg.get("manager_reg", "") if event_cfg else ""
        investor_url = event_cfg.get("investor_reg_url", "") if event_cfg else ""

        links = ""
        if manager_link:
            links += f"\nManager Registration: {manager_link}"
        if investor_url:
            links += f"\nInvestor Registration: {investor_url}"

        tag_line = f"{mfa_tag} {hashtag_block}".strip() if mfa_tag else hashtag_block
        return f"{base_text}{links}\n{tag_line}"


def _build_speaker_caption_fireside(speaker_info, event_key, event_cfg, platform):
    """Build fireside spotlight caption using Molly's template."""
    intro = _random.choice(_FIRESIDE_INTRO_PHRASES)
    name = speaker_info["name"]
    title = speaker_info["title"]
    firm = speaker_info["firm"]

    # Build the name + title string
    if title and firm:
        speaker_str = f"{name}, {title} at {firm},"
    elif firm:
        speaker_str = f"{name} from {firm}"
    elif title:
        speaker_str = f"{name}, {title},"
    else:
        speaker_str = name

    event_hashtag = event_cfg["hashtag"] if event_cfg else "#GlobalAlts"
    year = event_cfg["year"] if event_cfg else "2026"
    mfa_tag = _get_mfa_tag(platform)

    # event_hashtag is used in the body, so it counts toward the 5-hashtag limit
    hashtag_block = _build_hashtag_block(platform, event_hashtag_in_body=True,
        extra_tags=["#AlternativeInvestments", "#InvestmentLeadership", "#PrivateMarkets"])

    base_text = f"📢 {intro} {speaker_str} will join the {event_hashtag} {year} stage for a special fireside chat!"

    if platform == "Twitter":
        main_tweet = f"{base_text}\n{mfa_tag} {hashtag_block}".strip()
        return main_tweet
    else:
        manager_link = event_cfg.get("manager_reg", "") if event_cfg else ""
        investor_url = event_cfg.get("investor_reg_url", "") if event_cfg else ""

        links = ""
        if manager_link:
            links += f"\nManager Registration: {manager_link}"
        if investor_url:
            links += f"\nInvestor Registration: {investor_url}"

        tag_line = f"{mfa_tag} {hashtag_block}".strip() if mfa_tag else hashtag_block
        return f"{base_text}{links}\n{tag_line}"


def _build_twitter_reply_cta(event_cfg):
    """Build a Twitter reply with CTA and link (to be posted as reply to the main tweet)."""
    if not event_cfg:
        return "🔗 Register now:\nManager: [link]\nInvestor: [link]"

    parts = []
    manager_link = event_cfg.get("manager_reg", "")
    investor_url = event_cfg.get("investor_reg_url", "")
    investor_display = event_cfg.get("investor_reg_display", "")

    if manager_link:
        parts.append(f"Manager Registration ➡️ {manager_link}")
    if investor_url:
        parts.append(f"Investor Registration ➡️ {investor_url}")

    return "🔗 Register now:\n" + "\n".join(parts) if parts else ""


def _build_twitter_text_only(speaker_info, speaker_type, event_key, event_cfg):
    """Build a text-only thought leadership tweet for when no graphic is recommended.
    This follows the Twitter repositioning strategy toward thought leadership content.
    Respects 5-hashtag limit: event hashtag in body + up to 4 trailing."""
    name = speaker_info["name"]
    title = speaker_info["title"]
    firm = speaker_info["firm"]

    event_hashtag = event_cfg["hashtag"] if event_cfg else "#GlobalAlts"
    year = event_cfg["year"] if event_cfg else "2026"
    mfa_tag = _get_mfa_tag("Twitter")

    # event_hashtag is in body → 4 remaining for trailing block
    # #iConnections first, then up to 3 more
    trailing_tags = _build_hashtag_block("Twitter", event_hashtag_in_body=True,
        extra_tags=["#AlternativeInvestments", "#InvestmentLeadership", "#PrivateMarkets"])

    tag_line = f"{mfa_tag} {trailing_tags}"

    # Build credential string
    if title and firm:
        credential = f"{name} ({title}, {firm})"
    elif firm:
        credential = f"{name} ({firm})"
    elif title:
        credential = f"{name} ({title})"
    else:
        credential = name

    if speaker_type == "fireside":
        options = [
            f"What does it take to build a generational investment firm? {credential} will share their perspective at {event_hashtag} {year} in a fireside conversation you won't want to miss.\n\n{tag_line}",
            f"Few investors have the track record to fill a room just by walking in. {credential} is one of them — joining us for a fireside at {event_hashtag} {year}.\n\n{tag_line}",
            f"The most valuable 30 minutes at any conference? An honest fireside chat with someone who's actually built it. {credential} joins us at {event_hashtag} {year}.\n\n{tag_line}",
        ]
    else:
        options = [
            f"The {event_hashtag} {year} speaker lineup keeps getting stronger. {credential} brings a perspective the industry needs to hear right now.\n\n{tag_line}",
            f"Why {name}? Because allocators are asking the questions only experienced operators can answer. See them at {event_hashtag} {year}.\n\n{tag_line}",
            f"The conversations that move markets don't happen on earnings calls — they happen in rooms like {event_hashtag} {year}. {credential} joins the stage.\n\n{tag_line}",
        ]

    return _random.choice(options)


def _classify_milestone(item_name, notes=""):
    """Classify what kind of milestone this is from the item name and notes."""
    combined = f"{item_name} {notes}".lower()

    # LP registration count milestones (e.g. "200 LPs Registered", "100 LPs Registered")
    import re as _re
    lp_count_match = _re.search(r'(\d+)\s*lps?\s*(registered|and counting|signed up)', combined)
    if lp_count_match:
        return "lp_count", {"count": lp_count_match.group(1)}

    # Percentage ahead milestones (e.g. "61% Ahead LP reg")
    pct_match = _re.search(r'(\d+)%\s*ahead', combined)
    if pct_match:
        return "pct_ahead", {"pct": pct_match.group(1)}

    # Scheduler opens (e.g. "LP Scheduler Opens Tomorrow")
    if "scheduler" in combined and ("open" in combined or "live" in combined or "tomorrow" in combined):
        return "scheduler_opens", {}

    # Speaker wave announcements (e.g. "First Wave of Speakers")
    if "wave" in combined and "speaker" in combined:
        return "speaker_wave", {}
    if "first wave" in combined or "second wave" in combined:
        return "speaker_wave", {}

    # Agenda related (e.g. "Agenda Sneak Peek")
    if "agenda" in combined:
        return "agenda", {}

    # Generic milestone
    return "generic", {}


def _build_milestone_caption(item_name, group_name, notes, platform):
    """Build optimized milestone captions using Molly's reference style."""
    _event_key, event_cfg = _get_event_config(group_name)
    event_hashtag = event_cfg["hashtag"] if event_cfg else "#GlobalAlts"
    year = event_cfg["year"] if event_cfg else "2026"
    milestone_type, meta = _classify_milestone(item_name, notes)

    manager_link = event_cfg.get("manager_reg", "") if event_cfg else ""
    investor_url = event_cfg.get("investor_reg_url", "") if event_cfg else ""
    mfa_tag = _get_mfa_tag(platform)

    # All hooks use event_hashtag in body → counts toward the 5-tag limit
    hashtag_block = _build_hashtag_block(platform, event_hashtag_in_body=True,
        extra_tags=["#AlternativeInvestments", "#PrivateMarkets", "#InstitutionalInvesting"])
    tag_line = f"{mfa_tag} {hashtag_block}".strip() if mfa_tag else hashtag_block

    reg_block = ""
    if manager_link:
        reg_block += f"\nManager Registration: {manager_link}"
    if investor_url:
        reg_block += f"\nInvestor Registration: {investor_url}"

    # ── Platform-aware captions ──────────────────────────────────────────────

    if milestone_type == "lp_count":
        count = meta["count"]
        urgency_phrases = [
            "Registrations are accelerating. Secure your spot.",
            "Momentum is building fast. Don't wait.",
            "The allocator community is showing up. Will you?",
            "The room is filling up. Secure your seat.",
        ]
        urgency = _random.choice(urgency_phrases)
        hooks = [
            f"{count} LPs and counting for {event_hashtag} {year} 📈",
            f"{count}+ allocators registered for {event_hashtag} {year} 📈",
            f"We just passed {count} LP registrations for {event_hashtag} {year} 🚀",
        ]
        hook = _random.choice(hooks)

    elif milestone_type == "pct_ahead":
        pct = meta["pct"]
        urgency_phrases = [
            "Pace is picking up. Secure your spot.",
            "This year's momentum is unlike anything we've seen.",
            "The allocator community is moving early this year.",
        ]
        urgency = _random.choice(urgency_phrases)
        hooks = [
            f"We're already {pct}% ahead on LP registrations for {event_hashtag} {year} 📈",
            f"LP registrations for {event_hashtag} {year} are {pct}% ahead of last year's pace 🔥",
            f"{pct}% ahead of last year. {event_hashtag} {year} is building fast 📈",
        ]
        hook = _random.choice(hooks)

    elif milestone_type == "scheduler_opens":
        urgency_phrases = [
            "Start planning your meetings now.",
            "Build your schedule before the best slots fill up.",
            "Lock in the conversations that matter most.",
        ]
        urgency = _random.choice(urgency_phrases)
        hooks = [
            f"The LP Scheduler for {event_hashtag} {year} opens tomorrow ⏰",
            f"⏰ {event_hashtag} {year} meeting scheduler goes live tomorrow",
            f"Tomorrow: the {event_hashtag} {year} scheduler opens. Your meetings start here.",
        ]
        hook = _random.choice(hooks)

    elif milestone_type == "speaker_wave":
        urgency_phrases = [
            "More names dropping soon.",
            "This is just the beginning.",
            "Stay tuned — more announcements incoming.",
        ]
        urgency = _random.choice(urgency_phrases)
        hooks = [
            f"The first wave of speakers for {event_hashtag} {year} is here 🎤",
            f"🎤 Meet the first speakers confirmed for {event_hashtag} {year}",
            f"Speaker lineup is taking shape for {event_hashtag} {year} 🔥",
        ]
        hook = _random.choice(hooks)

    elif milestone_type == "agenda":
        urgency_phrases = [
            "This year's programming is designed to deliver.",
            "Curated for allocators and managers who mean business.",
            "Sessions built around the conversations that move capital.",
        ]
        urgency = _random.choice(urgency_phrases)
        hooks = [
            f"Sneak peek: the {event_hashtag} {year} agenda 👀",
            f"👀 First look at the {event_hashtag} {year} agenda",
            f"The {event_hashtag} {year} agenda just dropped. Here's what's coming.",
        ]
        hook = _random.choice(hooks)

    else:
        # Generic milestone — use item name directly
        urgency = "Don't miss it."
        hook = f"🎉 {item_name} — {event_hashtag} {year}"

    # Add notes context if available and not already captured
    notes_extra = ""
    if notes and milestone_type == "generic":
        notes_extra = f"\n{notes.strip()}"

    # ── Build per-platform ────────────────────────────────────────────────────

    if platform == "Twitter":
        # Twitter: no links, multi-variant
        twitter_tag_line = f"{_get_mfa_tag('Twitter')} {_build_hashtag_block('Twitter', event_hashtag_in_body=True, extra_tags=['#AlternativeInvestments', '#PrivateMarkets', '#InstitutionalInvesting'])}"
        main_tweet = f"{hook}\n{urgency}\n{twitter_tag_line}"
        if len(main_tweet) > 275:
            main_tweet = f"{hook}\n{urgency}\n{_get_mfa_tag('Twitter')} #iConnections #AlternativeInvestments"

        reply_cta = _build_twitter_reply_cta(event_cfg)

        # Text-only thought leadership version
        text_only_tag = f"{_get_mfa_tag('Twitter')} {_build_hashtag_block('Twitter', event_hashtag_in_body=True, extra_tags=['#AlternativeInvestments', '#PrivateMarkets'])}"
        text_only_options = [
            f"The best conferences don't just announce lineups — they build anticipation. {event_hashtag} {year} is proving that thesis in real time.\n\n{text_only_tag}",
            f"When LPs register early, it's a signal. They're not browsing — they're planning. {event_hashtag} {year} is tracking ahead of every prior year.\n\n{text_only_tag}",
            f"Conference registrations are a leading indicator of LP sentiment. What we're seeing for {event_hashtag} {year} says something about where allocators are headed.\n\n{text_only_tag}",
        ]

        return {
            "_multi": True,
            "tweet_with_graphic": main_tweet,
            "reply_cta": reply_cta,
            "text_only_suggestion": _random.choice(text_only_options),
        }

    elif platform == "LinkedIn":
        caption = f"{hook}\n{urgency}{notes_extra}\nRegister now:{reg_block}\n{tag_line}"
        return caption.strip()

    elif platform == "Instagram":
        ig_tag_line = f"{_get_mfa_tag('Instagram')} {_build_hashtag_block('Instagram', event_hashtag_in_body=True, extra_tags=['#AlternativeInvestments', '#PrivateMarkets', '#InstitutionalInvesting'])}"
        ig_cta = _build_instagram_cta(fallback_action="register")
        caption = f"{hook}\n{urgency}{notes_extra}\n{ig_cta}\n.\n.\n.\n{ig_tag_line}"
        return caption.strip()

    elif platform == "TikTok":
        tk_tag_line = f"{_get_mfa_tag('TikTok')} {_build_hashtag_block('TikTok', event_hashtag_in_body=True, extra_tags=['#AlternativeInvestments', '#PrivateMarkets', '#InstitutionalInvesting'])}"
        caption = f"{hook}\n{urgency}{notes_extra}\n{tk_tag_line}"
        return caption.strip()

    elif platform in ("YT Full Length", "YT Shorts"):
        yt_tags = _build_hashtag_block(platform, event_hashtag_in_body=True,
            extra_tags=["#AlternativeInvestments", "#PrivateMarkets"])
        caption = f"{hook}\n{urgency}{notes_extra}\n\nSubscribe for more from iConnections.\n{yt_tags}"
        return caption.strip()

    elif platform == "In-app Feed":
        caption = f"{hook}\n{urgency}{notes_extra}"
        return caption.strip()

    else:
        caption = f"{hook}\n{urgency}{notes_extra}\nRegister now:{reg_block}\n{tag_line}"
        return caption.strip()


def _generate_caption_for_platform(platform, item_name, post_type, group_name, notes, refinement="", image_info=None):
    """Generate a caption optimized for a specific platform.
    Uses Molly's confirmed templates for Speaker/Panel and Milestone posts.
    For Twitter Speaker/Milestone posts, returns a dict with multiple caption variants."""

    # ── Speaker / Panel posts use Molly's templates ──────────────────────────
    if post_type in ("Speaker", "Panel"):
        speaker_info = _extract_speaker_info(item_name, notes, image_info)
        speaker_type = _detect_speaker_type(item_name, notes, image_info)
        _event_key, event_cfg = _get_event_config(group_name)

        if platform == "Twitter":
            # Twitter gets multiple variants: main tweet (no links), reply CTA, text-only suggestion
            if speaker_type == "fireside":
                main_tweet = _build_speaker_caption_fireside(speaker_info, _event_key, event_cfg, "Twitter")
            else:
                main_tweet = _build_speaker_caption_confirmed(speaker_info, _event_key, event_cfg, "Twitter")

            reply_cta = _build_twitter_reply_cta(event_cfg)
            text_only = _build_twitter_text_only(speaker_info, speaker_type, _event_key, event_cfg)

            result = {
                "_multi": True,
                "tweet_with_graphic": main_tweet,
                "reply_cta": reply_cta,
                "text_only_suggestion": text_only,
            }
            return result
        else:
            # All other platforms get the standard template with links
            if speaker_type == "fireside":
                caption = _build_speaker_caption_fireside(speaker_info, _event_key, event_cfg, platform)
            else:
                caption = _build_speaker_caption_confirmed(speaker_info, _event_key, event_cfg, platform)

            return caption.strip()

    # ── Milestones posts use Molly's LP registration / event milestone style ──
    if post_type == "Milestones":
        caption = _build_milestone_caption(item_name, group_name, notes, platform)
        if isinstance(caption, dict):
            # Twitter multi-variant
            return caption
        else:
            return caption.strip()

    # ── All other post types: rule-based generation ──────────────────────────
    brand = "iConnections"

    # Check if this is a Global Alts flagship event post (needs MFA tag)
    _evt_key, _evt_cfg = _get_event_config(group_name)
    is_event_post = _evt_key is not None
    mfa_tag = _get_mfa_tag(platform) if is_event_post else ""

    # Check for content-specific CTA (e.g. Global Allocator Report → specific URL)
    content_cta = _get_content_cta(item_name=item_name, notes=notes)
    cta_line = ""
    if content_cta:
        cta_line = f"\n{content_cta['label']}: {content_cta['url']}"

    # Post type specific framing
    type_frames = {
        "Sponsor": f"Proud to welcome {item_name} as a sponsor",
        "Report": f"New insights: {item_name}",
        "Research": f"New research: {item_name}",
        "Product": f"Introducing: {item_name}",
        "Product Launch": f"🚀 Now live: {item_name}",
        "Coffee & Connections": f"Join us for Coffee & Connections: {item_name}",
        "Networking Event": f"Networking opportunity: {item_name}",
        "Partner Event": f"Partner event spotlight: {item_name}",
        "Press Release": f"📢 {item_name}",
        "Video": f"🎬 Watch now: {item_name}",
        "Podcast": f"🎙️ New episode: {item_name}",
        "Testimonial": f"Hear from {item_name}",
        "Testimonials": f"Hear from {item_name}",
        "Milestones": f"🎉 Milestone: {item_name}",
        "Case Study": f"Case study: {item_name}",
        "Meetups": f"Meetup: {item_name}",
        "Media": f"In the media: {item_name}",
        "Current Events": f"{item_name}",
        "Post Miami Campaign": f"{item_name}",
        "Post GAMI25 Content": f"{item_name}",
    }

    frame = type_frames.get(post_type, item_name)

    # Add notes context if available
    notes_context = f"\n\nContext: {notes}" if notes else ""

    # Build hashtag block (max 5 total, #iConnections first)
    generic_extras = ["#AlternativeInvestments", "#PrivateMarkets", "#InvestmentLeadership"]
    hashtag_block = _build_hashtag_block(platform, event_hashtag_in_body=False, extra_tags=generic_extras)
    tag_line = f"{mfa_tag} {hashtag_block}".strip() if mfa_tag else hashtag_block

    # Platform-specific optimization
    if platform == "LinkedIn":
        caption = f"""{frame}.

{notes_context.strip()}

At {brand}, we're building the year-round infrastructure connecting allocators and managers across private markets.{cta_line}

{tag_line}"""

    elif platform == "Instagram":
        ig_tag_line = f"{_get_mfa_tag('Instagram') if is_event_post else ''} {_build_hashtag_block('Instagram', event_hashtag_in_body=False, extra_tags=['#AlternativeInvestments', '#PrivateMarkets', '#InvestmentLeadership'])}".strip()
        # Default IG fallback action depends on post type
        _ig_fallback = {
            "Sponsor": "meet our sponsor",
            "Report": "read the full report",
            "Research": "read the research",
            "Product": "learn more",
            "Product Launch": "check it out",
            "Press Release": "read the announcement",
            "Video": "watch the full video",
            "Podcast": "listen to the episode",
            "Case Study": "read the case study",
            "Media": "read the article",
            "Coffee & Connections": "register",
            "Networking Event": "register",
            "Partner Event": "register",
            "Meetups": "register",
        }.get(post_type, "learn more")
        ig_cta = _build_instagram_cta(content_cta, fallback_action=_ig_fallback)
        caption = f"""{frame} ✨

{notes_context.strip()}

{ig_cta}

{ig_tag_line}"""

    elif platform == "Twitter":
        tw_tag_line = f"{_get_mfa_tag('Twitter') if is_event_post else ''} {_build_hashtag_block('Twitter', event_hashtag_in_body=False, extra_tags=['#AlternativeInvestments', '#PrivateMarkets'])}".strip()
        # Keep under 280 chars (no link in tweet body — link goes in reply or bio)
        caption = f"""{frame}.

{notes_context.strip()[:100]}

{tw_tag_line}"""
        if len(caption) > 275:
            caption = caption[:272] + "..."

    elif platform == "TikTok":
        tk_tag_line = f"{_get_mfa_tag('TikTok') if is_event_post else ''} {_build_hashtag_block('TikTok', event_hashtag_in_body=False, extra_tags=['#AlternativeInvestments', '#PrivateMarkets', '#InvestmentLeadership'])}".strip()
        caption = f"""{frame} 🔥

{notes_context.strip()}{cta_line}

{tk_tag_line}"""

    elif platform in ("YT Full Length", "YT Shorts"):
        yt_tags = _build_hashtag_block(platform, event_hashtag_in_body=False,
            extra_tags=["#AlternativeInvestments", "#PrivateMarkets"])
        caption = f"""{frame}

{notes_context.strip()}

Subscribe for more insights from {brand} — the leading platform connecting allocators and managers in alternative investments.

{yt_tags}"""

    elif platform == "In-app Feed":
        caption = f"""{frame}

{notes_context.strip()}"""

    else:
        caption = f"{frame}\n\n{notes_context.strip()}\n\n{tag_line}"

    # Apply refinement if provided

    return caption.strip()


# ─── Tab HTML ─────────────────────────────────────────────────────────────────

SOCIAL_CAL_TAB_HTML = '''
<div id="socialcal-view" style="display:none">
  <div class="page-header">
    <div class="page-title">📅 Social Calendar</div>
    <div class="page-sub">Content calendar synced from Monday.com · AI-powered caption drafting · Post scheduling workflow</div>
  </div>

  <!-- Board selector + refresh -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="color:var(--muted);font-size:0.8rem;">Sources:</span>
      <span style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:0.78rem;color:var(--text);">2026 Social Media + 2025 Social Media</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="color:var(--muted);font-size:0.8rem;">Filter Group:</span>
      <select id="sc-group-filter" onchange="scApplyFilters()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:0.82rem;">
        <option value="all">All Groups</option>
      </select>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="color:var(--muted);font-size:0.8rem;">Filter Type:</span>
      <select id="sc-type-filter" onchange="scApplyFilters()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:0.82rem;">
        <option value="all">All Types</option>
      </select>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="color:var(--muted);font-size:0.8rem;">Filter Status:</span>
      <select id="sc-status-filter" onchange="scApplyFilters()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:0.82rem;">
        <option value="all">All Statuses</option>
        <option value="Working on it">Working on it</option>
        <option value="Scheduled">Scheduled</option>
        <option value="For Scheduling">For Scheduling</option>
        <option value="Posted">Posted</option>
        <option value="Need Content">Need Content</option>
        <option value="none">No Status</option>
      </select>
    </div>
    <button onclick="scRefresh()" style="background:var(--purple);color:#fff;border:none;border-radius:6px;padding:5px 14px;font-size:0.8rem;cursor:pointer;">↻ Refresh</button>
    <span id="sc-item-count" style="color:var(--muted);font-size:0.78rem;margin-left:auto;"></span>
  </div>

  <!-- Calendar View Toggle -->
  <div style="display:flex;gap:4px;margin-bottom:16px;">
    <button class="tab active" onclick="scSwitchCalView('weekly')" id="sc-cal-btn-weekly">📅 Weekly</button>
    <button class="tab" onclick="scSwitchCalView('monthly')" id="sc-cal-btn-monthly">🗓️ Monthly</button>
  </div>

  <!-- Calendar Navigation -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
    <button onclick="scNavPrev()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 14px;cursor:pointer;font-size:1rem;">◀</button>
    <span id="sc-cal-label" style="font-weight:600;font-size:1rem;min-width:220px;text-align:center;"></span>
    <button onclick="scNavNext()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 14px;cursor:pointer;font-size:1rem;">▶</button>
    <button onclick="scNavToday()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:5px 12px;cursor:pointer;font-size:0.82rem;">Today</button>
    <input type="date" id="sc-cal-jump" onchange="scJumpToDate()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:0.82rem;" />
  </div>

  <!-- Calendar Grid -->
  <div id="sc-calendar-grid" style="margin-bottom:32px;"></div>

  <!-- Upcoming Post Schedule -->
  <div style="border-top:1px solid var(--border);padding-top:24px;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <div style="font-size:1.05rem;font-weight:700;">📋 Post Queue & Schedule</div>
      <button onclick="scUpcomingPrev()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:0.9rem;">◀</button>
      <span id="sc-upcoming-label" style="font-weight:500;font-size:0.9rem;min-width:180px;text-align:center;"></span>
      <button onclick="scUpcomingNext()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:0.9rem;">▶</button>
      <button onclick="scUpcomingThisWeek()" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:0.78rem;">This Week</button>
    </div>
    <div id="sc-upcoming-cards"></div>
  </div>

  <!-- Item Detail Modal -->
  <div id="sc-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;overflow-y:auto;" onclick="if(event.target===this)scCloseModal()">
    <div id="sc-modal-content" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;max-width:800px;margin:40px auto;padding:28px;position:relative;"></div>
  </div>
</div>
'''

SOCIAL_CAL_TAB_JS = '''
// ─── Social Calendar JavaScript ───────────────────────────────────────────────
let scItems = [];
let scFilteredItems = [];
let scCalView = 'weekly'; // 'weekly' or 'monthly'
let scCalDate = new Date(); // reference date for navigation
let scUpcomingDate = new Date(); // reference date for upcoming section
let scLoaded = false;
let scCaptionCache = {}; // Cache generated captions per item
let scImageDataCache = {}; // Cache image analysis results per item

// ── Post Type Colors (from Monday board) ──
const SC_POST_TYPE_COLORS = {
  // 2026 board
  "Meetups": "#bca58a", "Product": "#7e3b8a", "Case Study": "#a9bee8",
  "Testimonial": "#bda8f9", "Product Launch": "#784bd1", "Partner Event": "#175a63",
  "Video": "#ff7575", "Sponsor": "#74afcc", "Speaker": "#4eccc6",
  "Report": "#e484bd", "Press Release": "#ffadad", "Milestones": "#579bfc",
  "Networking Event": "#ff5ac4", "Post Miami Campaign": "#401694",
  "Testimonials": "#a1e3f6", "Post GAMI25 Content": "#66ccff",
  "Coffee & Connections": "#757575", "Current Events": "#9d99b9",
  "Panel": "#00c875", "Media": "#7f5347", "Podcast": "#037f4c",
  "Research": "#9cd326",
  // 2025 board additional types
  "Announcement": "#333333", "Blog Post": "#216edf", "Board Members": "#faa1f1",
  "Cocktails & Connections": "#ffcb00", "Content Social Clips": "#9d50dd",
  "Countdown": "#225091", "F4C": "#5559df", "FOMO": "#fdab3d",
  "Funny": "#007eb5", "Funny Videos": "#9cd326", "Holiday": "#7f5347",
  "IRN": "#ff007f", "Investment Newsletter": "#df2f4a",
  "Onsite Content": "#563e3e", "Partnerships": "#cab641",
  "Past speaker clips": "#cd9282", "Staff": "#037f4c",
  "Trending Content": "#ff6d3b",
};

// ── Status Colors ──
const SC_STATUS_COLORS = {
  "Working on it": "#fdab3d",
  "Posted": "#00c875",
  "Need Content": "#df2f4a",
  "For Scheduling": "#faa1f1",
  "Scheduled": "#579bfc",
};

// ── Date Helpers ──
function scFmtDate(d) { return d.toISOString().split('T')[0]; }
function scParseDate(s) { const [y,m,d] = s.split('-').map(Number); return new Date(y, m-1, d); }
function scWeekStart(d) { const dt = new Date(d); dt.setDate(dt.getDate() - dt.getDay()); return dt; }
function scWeekEnd(d) { const dt = scWeekStart(d); dt.setDate(dt.getDate() + 6); return dt; }
function scMonthStart(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function scMonthEnd(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 0); }
function scFmtRange(start, end) {
  const opts = { month: 'short', day: 'numeric' };
  const y = start.getFullYear();
  return start.toLocaleDateString('en-US', opts) + ' – ' + end.toLocaleDateString('en-US', opts) + ', ' + y;
}
function scFmtMonth(d) {
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}
function scFmtDay(d) {
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

// ── Data Loading ──
let scAllGroups = []; // All groups from the board (even empty ones)

async function scLoadData(force) {
  // Show loading feedback
  const refreshBtn = document.querySelector('[onclick="scRefresh()"]');
  if (refreshBtn && force) {
    refreshBtn.textContent = '⏳ Refreshing...';
    refreshBtn.disabled = true;
    refreshBtn.style.opacity = '0.6';
  }
  const grid = document.getElementById('sc-calendar-grid');
  const upcoming = document.getElementById('sc-upcoming-cards');
  if (!scItems.length) {
    if (grid) grid.innerHTML = '<div style="color:var(--muted);padding:40px;text-align:center;font-size:0.9rem;">⏳ Loading social calendar data...</div>';
    if (upcoming) upcoming.innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;font-size:0.85rem;">Loading...</div>';
  }
  const url = '/api/social-calendar/items' + (force ? '?refresh=1' : '');
  try {
    const res = await fetch(url);
    const data = await res.json();
    scItems = data.items || [];
    scAllGroups = data.all_groups || [];
    scPopulateFilters();
    scApplyFilters();
  } catch(e) {
    console.error('Social calendar load error:', e);
    if (grid) grid.innerHTML = '<div style="color:var(--muted);padding:20px;">Error loading data. Try refreshing.</div>';
  }
  if (refreshBtn) {
    refreshBtn.textContent = '↻ Refresh';
    refreshBtn.disabled = false;
    refreshBtn.style.opacity = '1';
  }
}

function scPopulateFilters() {
  // Populate group filter from ALL board groups (not just items with dates)
  const groups = scAllGroups.map(g => g.title).sort();
  const gf = document.getElementById('sc-group-filter');
  const currentG = gf.value;
  gf.innerHTML = '<option value="all">All Groups</option>' + groups.map(g => '<option value="'+g+'">'+g+'</option>').join('');
  gf.value = currentG || 'all';

  // Populate type filter from all known post types (items may not cover all)
  const itemTypes = [...new Set(scItems.filter(i => i.post_type).map(i => i.post_type))];
  const allTypeNames = Object.values(SC_POST_TYPE_COLORS).length ? Object.keys(SC_POST_TYPE_COLORS) : itemTypes;
  const types = [...new Set([...itemTypes, ...allTypeNames])].sort();
  const tf = document.getElementById('sc-type-filter');
  const currentT = tf.value;
  tf.innerHTML = '<option value="all">All Types</option>' + types.map(t => '<option value="'+t+'">'+t+'</option>').join('');
  tf.value = currentT || 'all';
}

function scApplyFilters() {
  const gf = document.getElementById('sc-group-filter').value;
  const tf = document.getElementById('sc-type-filter').value;
  const sf = document.getElementById('sc-status-filter').value;
  scFilteredItems = scItems.filter(i => {
    if (gf !== 'all' && i.group_name !== gf) return false;
    if (tf !== 'all' && i.post_type !== tf) return false;
    if (sf !== 'all') {
      if (sf === 'none') { if (i.status) return false; }
      else { if (i.status !== sf) return false; }
    }
    return true;
  });
  document.getElementById('sc-item-count').textContent = scFilteredItems.length + ' of ' + scItems.length + ' posts';
  scRenderCalendar();
  scRenderUpcoming();
}

function scRefresh() {
  scLoadData(true);
}

// ── Calendar View Switching ──
function scSwitchCalView(view) {
  scCalView = view;
  document.getElementById('sc-cal-btn-weekly').className = 'tab ' + (view === 'weekly' ? 'active' : '');
  document.getElementById('sc-cal-btn-monthly').className = 'tab ' + (view === 'monthly' ? 'active' : '');
  scRenderCalendar();
}

// ── Calendar Navigation ──
function scNavPrev() {
  if (scCalView === 'weekly') { scCalDate.setDate(scCalDate.getDate() - 7); }
  else { scCalDate.setMonth(scCalDate.getMonth() - 1); }
  scRenderCalendar();
}
function scNavNext() {
  if (scCalView === 'weekly') { scCalDate.setDate(scCalDate.getDate() + 7); }
  else { scCalDate.setMonth(scCalDate.getMonth() + 1); }
  scRenderCalendar();
}
function scNavToday() {
  scCalDate = new Date();
  scRenderCalendar();
}
function scJumpToDate() {
  const v = document.getElementById('sc-cal-jump').value;
  if (v) { scCalDate = scParseDate(v); scRenderCalendar(); }
}

// ── Render Calendar ──
function scRenderCalendar() {
  if (scCalView === 'weekly') scRenderWeekly();
  else scRenderMonthly();
}

function scRenderWeekly() {
  const ws = scWeekStart(scCalDate);
  const we = scWeekEnd(scCalDate);
  document.getElementById('sc-cal-label').textContent = scFmtRange(ws, we);

  // Build day columns
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(ws);
    d.setDate(d.getDate() + i);
    days.push(d);
  }

  const today = scFmtDate(new Date());
  // Weekend columns narrower (0.6fr Sun/Sat), weekdays wider (1fr Mon-Fri) so weekdays have more room
  let html = '<div style="display:grid;grid-template-columns:0.6fr 1fr 1fr 1fr 1fr 1fr 0.6fr;gap:4px;min-height:300px;">';

  days.forEach(day => {
    const ds = scFmtDate(day);
    const isToday = ds === today;
    const dayItems = scFilteredItems.filter(it => it.date === ds);
    const dayName = day.toLocaleDateString('en-US', { weekday: 'short' });
    const dayNum = day.getDate();

    html += '<div style="background:var(--surface2);border-radius:8px;padding:8px;min-height:120px;border:' + (isToday ? '2px solid var(--purple)' : '1px solid var(--border)') + ';">';
    html += '<div style="font-size:0.72rem;color:' + (isToday ? 'var(--purple)' : 'var(--muted)') + ';font-weight:' + (isToday ? '700' : '500') + ';margin-bottom:6px;">' + dayName + ' ' + dayNum + '</div>';

    dayItems.forEach(it => {
      const bgColor = SC_POST_TYPE_COLORS[it.post_type] || '#555';
      // Determine text color based on background brightness
      const textColor = scContrastColor(bgColor);
      html += '<div onclick="scShowItem(\\''+it.id+'\\');event.stopPropagation();" style="background:'+bgColor+';color:'+textColor+';padding:4px 6px;border-radius:5px;margin-bottom:3px;font-size:0.7rem;cursor:pointer;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+scEsc(it.name)+' ('+scEsc(it.post_type)+')">';
      html += scEsc(it.name);
      html += '</div>';
    });

    html += '</div>';
  });

  html += '</div>';
  document.getElementById('sc-calendar-grid').innerHTML = html;
}

function scRenderMonthly() {
  const ms = scMonthStart(scCalDate);
  const me = scMonthEnd(scCalDate);
  document.getElementById('sc-cal-label').textContent = scFmtMonth(scCalDate);

  // Calendar grid: start from Sunday of the week containing the 1st
  const calStart = scWeekStart(ms);
  const today = scFmtDate(new Date());

  // Header row — weekend columns narrower (0.6fr), weekdays wider (1fr)
  const monthlyCols = 'grid-template-columns:0.6fr 1fr 1fr 1fr 1fr 1fr 0.6fr';
  let html = '<div style="display:grid;' + monthlyCols + ';gap:3px;">';
  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
    html += '<div style="text-align:center;font-size:0.72rem;color:var(--muted);font-weight:600;padding:4px 0;">' + d + '</div>';
  });

  // Day cells (6 weeks max)
  const cur = new Date(calStart);
  for (let w = 0; w < 6; w++) {
    for (let d = 0; d < 7; d++) {
      const ds = scFmtDate(cur);
      const isToday = ds === today;
      const inMonth = cur.getMonth() === scCalDate.getMonth();
      const dayItems = scFilteredItems.filter(it => it.date === ds);

      html += '<div style="background:' + (inMonth ? 'var(--surface2)' : 'var(--bg)') + ';border-radius:6px;padding:4px;min-height:70px;border:' + (isToday ? '2px solid var(--purple)' : '1px solid var(--border)') + ';opacity:' + (inMonth ? '1' : '0.4') + ';">';
      html += '<div style="font-size:0.68rem;color:' + (isToday ? 'var(--purple)' : 'var(--muted)') + ';font-weight:' + (isToday ? '700' : '400') + ';margin-bottom:3px;">' + cur.getDate() + '</div>';

      dayItems.slice(0, 3).forEach(it => {
        const bgColor = SC_POST_TYPE_COLORS[it.post_type] || '#555';
        const textColor = scContrastColor(bgColor);
        html += '<div onclick="scShowItem(\\''+it.id+'\\');event.stopPropagation();" style="background:'+bgColor+';color:'+textColor+';padding:2px 4px;border-radius:4px;margin-bottom:2px;font-size:0.62rem;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+scEsc(it.name)+'">';
        html += scEsc(it.name);
        html += '</div>';
      });
      if (dayItems.length > 3) {
        html += '<div style="font-size:0.6rem;color:var(--muted);cursor:pointer;" onclick="scCalDate=scParseDate(\\''+ds+'\\');scSwitchCalView(\\'weekly\\');">+' + (dayItems.length - 3) + ' more</div>';
      }

      html += '</div>';
      cur.setDate(cur.getDate() + 1);
    }
    // Stop if we've passed the month
    if (cur.getMonth() > scCalDate.getMonth() && cur.getFullYear() >= scCalDate.getFullYear()) {
      if (w >= 3) break;
    }
  }

  html += '</div>';
  document.getElementById('sc-calendar-grid').innerHTML = html;
}

// ── Upcoming Post Schedule ──
function scUpcomingPrev() { scUpcomingDate.setDate(scUpcomingDate.getDate() - 7); scRenderUpcoming(); }
function scUpcomingNext() { scUpcomingDate.setDate(scUpcomingDate.getDate() + 7); scRenderUpcoming(); }
function scUpcomingThisWeek() { scUpcomingDate = new Date(); scRenderUpcoming(); }

function scRenderUpcoming() {
  const ws = scWeekStart(scUpcomingDate);
  const we = scWeekEnd(scUpcomingDate);
  document.getElementById('sc-upcoming-label').textContent = scFmtRange(ws, we);

  const wsStr = scFmtDate(ws);
  const weStr = scFmtDate(we);
  const weekItems = scFilteredItems.filter(it => it.date >= wsStr && it.date <= weStr);
  weekItems.sort((a, b) => a.date.localeCompare(b.date));

  if (!weekItems.length) {
    document.getElementById('sc-upcoming-cards').innerHTML = '<div style="color:var(--muted);padding:20px;text-align:center;font-size:0.85rem;">No posts for this week.</div>';
    return;
  }

  // Split into three sections
  const needsScheduling = weekItems.filter(it => it.status !== 'Scheduled' && it.status !== 'Posted');
  const scheduled = weekItems.filter(it => it.status === 'Scheduled');
  const posted = weekItems.filter(it => it.status === 'Posted');

  let html = '';

  // Section 1: Needs Scheduling (the queue)
  html += '<div style="margin-bottom:4px;">';
  html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">';
  html += '<span style="font-size:0.92rem;font-weight:600;">📋 Needs Scheduling</span>';
  html += '<span style="font-size:0.72rem;color:var(--muted);background:var(--surface2);border-radius:10px;padding:2px 8px;">' + needsScheduling.length + '</span>';
  html += '</div>';
  if (!needsScheduling.length) {
    html += '<div style="color:var(--muted);padding:12px 20px;text-align:center;font-size:0.82rem;background:var(--surface2);border-radius:8px;border:1px dashed var(--border);margin-bottom:8px;">🎉 All posts for this week are scheduled or posted!</div>';
  }
  needsScheduling.forEach(it => {
    html += scRenderUpcomingCard(it);
  });
  html += '</div>';

  // Divider
  html += '<div style="border-top:2px solid var(--border);margin:24px 0;position:relative;">';
  html += '<span style="position:absolute;top:-10px;left:20px;background:var(--bg);padding:0 10px;font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;">Scheduled</span>';
  html += '</div>';

  // Section 2: Scheduled
  html += '<div style="margin-bottom:4px;">';
  html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">';
  html += '<span style="font-size:0.92rem;font-weight:600;">✅ Scheduled</span>';
  html += '<span style="font-size:0.72rem;color:var(--muted);background:var(--surface2);border-radius:10px;padding:2px 8px;">' + scheduled.length + '</span>';
  html += '</div>';
  if (!scheduled.length) {
    html += '<div style="color:var(--muted);padding:12px 20px;text-align:center;font-size:0.82rem;background:var(--surface2);border-radius:8px;border:1px dashed var(--border);margin-bottom:8px;">No posts scheduled yet for this week.</div>';
  }
  scheduled.forEach(it => {
    html += scRenderUpcomingCard(it);
  });
  html += '</div>';

  // Divider
  html += '<div style="border-top:2px solid var(--border);margin:24px 0;position:relative;">';
  html += '<span style="position:absolute;top:-10px;left:20px;background:var(--bg);padding:0 10px;font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;">Posted</span>';
  html += '</div>';

  // Section 3: Posted
  html += '<div style="margin-bottom:4px;">';
  html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">';
  html += '<span style="font-size:0.92rem;font-weight:600;">📤 Posted</span>';
  html += '<span style="font-size:0.72rem;color:var(--muted);background:var(--surface2);border-radius:10px;padding:2px 8px;">' + posted.length + '</span>';
  html += '</div>';
  if (!posted.length) {
    html += '<div style="color:var(--muted);padding:12px 20px;text-align:center;font-size:0.82rem;background:var(--surface2);border-radius:8px;border:1px dashed var(--border);margin-bottom:8px;">No posts marked as posted yet for this week.</div>';
  }
  posted.forEach(it => {
    html += scRenderUpcomingCard(it);
  });
  html += '</div>';

  document.getElementById('sc-upcoming-cards').innerHTML = html;

  // Auto-render cached captions
  weekItems.forEach(it => {
    if (scCaptionCache[it.id]) scRenderCaptions(it.id, scCaptionCache[it.id]);
  });
}

// ── Render a single upcoming post card ──
function scRenderUpcomingCard(it) {
  let html = '';
  const ptColor = SC_POST_TYPE_COLORS[it.post_type] || '#555';
  const stColor = SC_STATUS_COLORS[it.status] || 'var(--muted)';
  const itLinks = it.platform_links || {};
  const platBadges = it.platforms.map(p => {
    // Map platform checkbox names to link column key names
    const linkKey = p === 'YT Full Length' ? 'YT Full' : p === 'YT Shorts' ? 'YT Short' : p;
    const linkVal = itLinks[linkKey];
    const linkIcon = (it.status === 'Posted' && p !== 'In-app Feed') ? (linkVal === 'ig-story' ? ' 📖' : linkVal ? ' ✅' : ' ⚠️') : '';
    return '<span style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:0.68rem;margin-right:3px;">'+scEsc(p)+linkIcon+'</span>';
  }).join('');
  const dateLabel = scParseDate(it.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

  html += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;border-left:4px solid '+ptColor+';">';
  html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;flex-wrap:wrap;gap:8px;">';
  html += '<div>';
  html += '<div style="font-weight:600;font-size:0.95rem;">'+scEsc(it.name)+'</div>';
  html += '<div style="font-size:0.75rem;color:var(--muted);margin-top:2px;">'+scEsc(it.group_name)+' · '+dateLabel+(it.board_name && it.board_name !== '2026 Social Media' ? ' · <span style=\"opacity:0.7;\">'+scEsc(it.board_name)+'</span>' : '')+'</div>';
  html += '</div>';
  html += '<div style="display:flex;gap:6px;align-items:center;">';
  html += '<span style="background:'+ptColor+';color:'+scContrastColor(ptColor)+';padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:500;">'+scEsc(it.post_type)+'</span>';
  if (it.status) html += '<span style="background:'+stColor+';color:#fff;padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:500;">'+scEsc(it.status)+'</span>';
  html += '</div></div>';

  // Platforms
  if (it.platforms.length) {
    html += '<div style="margin-bottom:8px;">'+platBadges+'</div>';
  }

  // Notes
  if (it.notes) {
    html += '<div style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;"><strong>Notes:</strong> '+scEsc(it.notes)+'</div>';
  }

  // Asset preview
  if (it.assets && it.assets.length) {
    html += '<div style="margin-bottom:10px;">';
    it.assets.forEach(a => {
      if (['.png','.jpg','.jpeg','.gif','.webp'].includes(a.extension.toLowerCase())) {
        html += '<div style="display:inline-block;position:relative;margin-right:6px;margin-bottom:4px;">';
        html += '<img src="/api/social-calendar/asset/'+a.id+'" style="max-width:200px;max-height:150px;border-radius:6px;border:1px solid var(--border);display:block;" />';
        html += '<a href="/api/social-calendar/asset/'+a.id+'?download=1" download="'+scEsc(a.name)+'" style="position:absolute;bottom:4px;right:4px;background:rgba(0,0,0,0.7);color:#fff;border-radius:4px;padding:2px 6px;font-size:0.6rem;text-decoration:none;cursor:pointer;" title="Download">⬇</a>';
        html += '</div>';
      } else {
        html += '<span style="background:var(--bg);padding:3px 8px;border-radius:4px;font-size:0.72rem;border:1px solid var(--border);">📎 '+scEsc(a.name)+'</span>';
      }
    });
    html += '</div>';
  }

  // Caption section — collapsible, only for posts NOT yet scheduled or posted
  if (it.platforms.length && it.status !== 'Scheduled' && it.status !== 'Posted') {
    const cacheKey = it.id;
    html += '<div style="border-top:1px solid var(--border);padding-top:10px;margin-top:6px;">';
    html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer;" onclick="scToggleCaptions(\\''+it.id+'\\',this)">';
    html += '<span id="sc-cap-arrow-'+it.id+'" style="font-size:0.7rem;transition:transform 0.2s;">▶</span>';
    html += '<span style="font-size:0.82rem;font-weight:600;">✨ AI Captions</span>';
    html += '</div>';
    html += '<div id="sc-cap-panel-'+it.id+'" style="display:none;">';

    // Speaker info inputs for Speaker/Panel posts (for Molly's template)
    if (it.post_type === 'Speaker' || it.post_type === 'Panel') {
      html += '<div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:10px;">';
      html += '<div style="font-size:0.72rem;font-weight:600;color:var(--text);margin-bottom:6px;">🎤 Speaker Details <span style="color:var(--muted);font-weight:400;">(auto-reads from image, or type manually)</span></div>';

      // "Analyze Image" button if there are image assets
      const imgAssets = (it.assets || []).filter(a => ['.png','.jpg','.jpeg','.gif','.webp'].includes((a.extension||'').toLowerCase()));
      if (imgAssets.length > 0) {
        html += '<div style="margin-bottom:8px;">';
        html += '<button id="sc-analyze-btn-'+it.id+'" onclick="event.stopPropagation();scAnalyzeSpeakerImage(\\''+it.id+'\\',\\''+imgAssets[0].id+'\\',this)" style="background:#10B981;color:#fff;border:none;border-radius:5px;padding:4px 12px;font-size:0.72rem;cursor:pointer;display:flex;align-items:center;gap:4px;">🔍 Auto-Read from Image</button>';
        html += '<div id="sc-analyze-status-'+it.id+'" style="font-size:0.65rem;color:var(--muted);margin-top:3px;"></div>';
        html += '</div>';
      }

      // Image type selector
      html += '<div style="display:flex;gap:8px;margin-bottom:6px;flex-wrap:wrap;">';
      html += '<label style="font-size:0.7rem;color:var(--muted);display:flex;align-items:center;gap:4px;cursor:pointer;">';
      html += '<input type="radio" name="sc-imgtype-'+it.id+'" value="confirmed" checked style="margin:0;"> Confirmed Speaker</label>';
      html += '<label style="font-size:0.7rem;color:var(--muted);display:flex;align-items:center;gap:4px;cursor:pointer;">';
      html += '<input type="radio" name="sc-imgtype-'+it.id+'" value="fireside" style="margin:0;"> Fireside Spotlight</label>';
      html += '</div>';

      // Auto-detect fireside from item name
      const isFireside = it.name.toLowerCase().includes('fireside') || it.name.toLowerCase().includes('spotlight');

      html += '<div style="display:flex;gap:6px;flex-wrap:wrap;">';
      html += '<input id="sc-spk-title-'+it.id+'" type="text" placeholder="Title (e.g. Managing Director & Head of Growth Equity)" style="flex:1;min-width:180px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:5px;padding:4px 8px;font-size:0.72rem;" />';
      html += '<input id="sc-spk-firm-'+it.id+'" type="text" placeholder="Firm (e.g. CPP Investments)" style="flex:1;min-width:140px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:5px;padding:4px 8px;font-size:0.72rem;" />';
      html += '</div>';

      html += '</div>';

      // Auto-check fireside radio if detected from item name
      if (isFireside) {
        setTimeout(() => {
          const r = document.querySelector('input[name="sc-imgtype-'+it.id+'"][value="fireside"]');
          if (r) r.checked = true;
        }, 0);
      }
    }

    // "Read from Image" button for ANY post type with image assets (not just Speaker)
    if (it.post_type !== 'Speaker' && it.post_type !== 'Panel') {
      const allImgAssets = (it.assets || []).filter(a => ['.png','.jpg','.jpeg','.gif','.webp'].includes((a.extension||'').toLowerCase()));
      if (allImgAssets.length > 0) {
        html += '<div style="margin-bottom:8px;">';
        html += '<button id="sc-analyze-btn-'+it.id+'" onclick="event.stopPropagation();scAnalyzePostImage(\\''+it.id+'\\',\\''+allImgAssets[0].id+'\\',this)" style="background:#10B981;color:#fff;border:none;border-radius:5px;padding:4px 12px;font-size:0.72rem;cursor:pointer;display:flex;align-items:center;gap:4px;">🔍 Read from Image</button>';
        html += '<div id="sc-analyze-status-'+it.id+'" style="font-size:0.65rem;color:var(--muted);margin-top:3px;"></div>';
        html += '</div>';
      }
    }

    html += '<div style="margin-bottom:8px;"><button onclick="event.stopPropagation();scGenerateCaptions(\\''+it.id+'\\',this)" style="background:var(--purple);color:#fff;border:none;border-radius:5px;padding:3px 10px;font-size:0.72rem;cursor:pointer;">Generate Captions</button></div>';
    html += '<div id="sc-captions-'+it.id+'"></div>';
    html += '</div>';
    html += '</div>';
  }

  // Action buttons
  html += '<div style="display:flex;gap:6px;margin-top:10px;border-top:1px solid var(--border);padding-top:10px;">';
  html += '<button onclick="scShowItem(\\''+it.id+'\\');" style="background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:4px 12px;font-size:0.72rem;cursor:pointer;color:var(--text);">🔍 View Details</button>';
  if (it.has_status_col) {
    if (it.status !== 'Scheduled' && it.status !== 'Posted') {
      html += '<button onclick="scMarkScheduled(\\''+it.id+'\\',this)" style="background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:4px 12px;font-size:0.72rem;cursor:pointer;color:var(--text);">✅ Mark as Scheduled</button>';
    }
    if (it.status !== 'Posted') {
      html += '<button onclick="scMarkPosted(\\''+it.id+'\\',this)" style="background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:4px 12px;font-size:0.72rem;cursor:pointer;color:var(--text);">📤 Mark as Posted</button>';
    }
  }
  html += '</div>';

  html += '</div>';
  return html;
}

// ── Caption Generation ──
async function scGenerateCaptions(itemId, btn) {
  const item = scItems.find(i => i.id === itemId);
  if (!item) return;
  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    // Build request body
    const reqBody = {
      name: item.name,
      post_type: item.post_type,
      group_name: item.group_name,
      platforms: item.platforms,
      notes: item.notes,
    };

    // For Speaker/Panel posts, include speaker details from the inputs
    if (item.post_type === 'Speaker' || item.post_type === 'Panel') {
      const titleEl = document.getElementById('sc-spk-title-' + itemId);
      const firmEl = document.getElementById('sc-spk-firm-' + itemId);
      const imgTypeRadio = document.querySelector('input[name="sc-imgtype-'+itemId+'"]:checked');

      const imageInfo = {};
      if (titleEl && titleEl.value.trim()) imageInfo.title = titleEl.value.trim();
      if (firmEl && firmEl.value.trim()) imageInfo.firm = firmEl.value.trim();
      if (imgTypeRadio) imageInfo.speaker_type = imgTypeRadio.value;

      if (Object.keys(imageInfo).length > 0) {
        reqBody.image_info = imageInfo;
      }
    }

    // If image was analyzed, include image_data so captions are based on the graphic content
    if (scImageDataCache[itemId]) {
      reqBody.image_data = scImageDataCache[itemId];
    }

    const res = await fetch('/api/social-calendar/generate-caption', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();
    scCaptionCache[itemId] = data.captions;
    scRenderCaptions(itemId, data.captions);
  } catch(e) {
    console.error('Caption gen error:', e);
  }
  btn.disabled = false;
  btn.textContent = 'Generate Captions';
}

// Twitter sub-variant labels & descriptions
const _twitterVariantMeta = {
  tweet_with_graphic: {
    label: '🐦 Tweet (with graphic)',
    desc: 'Post this with the speaker image. No links — keeps engagement high.',
    color: '#1DA1F2',
  },
  reply_cta: {
    label: '↩️ Reply CTA (post as reply to the tweet above)',
    desc: 'Reply to your own tweet with the registration links.',
    color: '#F59E0B',
  },
  text_only_suggestion: {
    label: '💡 Text-Only Tweet (Nick\\'s suggestion — no graphic)',
    desc: 'Thought leadership framing. Use this as a standalone text tweet OR as an alternative to the graphic version when you want to position the brand as an industry voice rather than a conference promoter.',
    color: '#10B981',
  },
};

function scRenderCaptions(itemId, captions) {
  const el = document.getElementById('sc-captions-' + itemId);
  if (!el) return;

  let html = '';
  Object.entries(captions).forEach(([platform, caption]) => {
    // Check if this platform returned multi-variant captions (e.g., Twitter for Speaker posts)
    if (caption && typeof caption === 'object' && caption._multi) {
      // Render the multi-variant Twitter section
      html += '<div style="margin-bottom:14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;">';
      html += '<div style="font-size:0.8rem;font-weight:700;color:var(--purple);margin-bottom:8px;display:flex;align-items:center;gap:6px;">'+scEsc(platform)+' <span style="font-size:0.65rem;background:var(--purple);color:#fff;padding:1px 6px;border-radius:10px;font-weight:500;">3 variants</span></div>';

      ['tweet_with_graphic', 'reply_cta', 'text_only_suggestion'].forEach(variantKey => {
        const variantCaption = caption[variantKey] || '';
        const meta = _twitterVariantMeta[variantKey] || {};
        const vid = 'sc-cap-' + itemId + '-Twitter-' + variantKey;

        html += '<div style="margin-bottom:10px;border-left:3px solid '+(meta.color||'var(--border)')+';padding-left:10px;">';
        html += '<div style="font-size:0.72rem;font-weight:600;color:'+(meta.color||'var(--text)')+';margin-bottom:2px;">'+(meta.label||variantKey)+'</div>';
        html += '<div style="font-size:0.65rem;color:var(--muted);margin-bottom:4px;">'+(meta.desc||'')+'</div>';
        html += '<textarea id="'+vid+'" style="width:100%;min-height:70px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px;font-size:0.78rem;resize:vertical;font-family:inherit;">' + scEsc(variantCaption) + '</textarea>';
        html += '<div style="display:flex;gap:6px;margin-top:4px;">';
        if (variantKey === 'tweet_with_graphic') {
          html += '<button onclick="scRefineCaptionPrompt(\\''+itemId+'\\',\\'Twitter\\',\\''+vid+'\\');" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:0.68rem;cursor:pointer;color:var(--text);">🔄 Refine</button>';
        }
        html += '<button onclick="scCopyCap(\\''+vid+'\\');" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:0.68rem;cursor:pointer;color:var(--text);">📋 Copy</button>';
        html += '</div></div>';
      });

      html += '</div>';
    } else {
      // Standard single-caption rendering
      const id = 'sc-cap-' + itemId + '-' + platform.replace(/[^a-zA-Z]/g, '');
      html += '<div style="margin-bottom:10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;">';
      html += '<div style="font-size:0.75rem;font-weight:600;color:var(--purple);margin-bottom:4px;">'+scEsc(platform)+'</div>';
      html += '<textarea id="'+id+'" style="width:100%;min-height:80px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px;font-size:0.78rem;resize:vertical;font-family:inherit;" onchange="scCaptionEdited(\\''+itemId+'\\',\\''+scEsc(platform)+'\\',this.value)">' + scEsc(caption) + '</textarea>';
      html += '<div style="display:flex;gap:6px;margin-top:4px;">';
      html += '<button onclick="scRefineCaptionPrompt(\\''+itemId+'\\',\\''+scEsc(platform)+'\\',\\''+id+'\\');" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:0.68rem;cursor:pointer;color:var(--text);">🔄 Refine</button>';
      html += '<button onclick="scCopyCap(\\''+id+'\\');" style="background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:0.68rem;cursor:pointer;color:var(--text);">📋 Copy</button>';
      html += '</div></div>';
    }
  });

  el.innerHTML = html;
}

function scCaptionEdited(itemId, platform, value) {
  if (scCaptionCache[itemId]) scCaptionCache[itemId][platform] = value;
}

async function scRefineCaptionPrompt(itemId, platform, textareaId) {
  const feedback = prompt('How would you like to refine this caption? (e.g., "shorter", "more casual", "add a CTA", "more thought leadership", or any natural language instruction)');
  if (!feedback) return;

  const item = scItems.find(i => i.id === itemId);
  if (!item) return;

  const ta = document.getElementById(textareaId);
  const origText = ta.value;
  ta.value = '✨ Refining...';
  ta.disabled = true;

  // Find the Refine button and update it
  const refineBtn = ta.parentElement.querySelector('button');
  if (refineBtn) { refineBtn.textContent = '⏳ Refining...'; refineBtn.disabled = true; }

  // First try rule-based / OpenAI refine (instant)
  try {
    const res = await fetch('/api/social-calendar/refine-caption', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        caption: origText,
        feedback: feedback,
        platform: platform,
        post_type: item.post_type,
      })
    });
    const data = await res.json();
    if (data.caption) {
      ta.value = data.caption;
      if (scCaptionCache[itemId] && scCaptionCache[itemId][platform] !== undefined) {
        if (typeof scCaptionCache[itemId][platform] === 'object' && scCaptionCache[itemId][platform]._multi) {
          scCaptionCache[itemId][platform] = ta.value;
        } else {
          scCaptionCache[itemId][platform] = ta.value;
        }
      }
      ta.disabled = false;
      if (refineBtn) { refineBtn.textContent = '🔄 Refine'; refineBtn.disabled = false; }
      return;
    }

    // Rule-based couldn't handle it — ask Nick via Slack
    if (data.needs_key || data.error) {
      ta.value = '🤖 Sending to Nick on Slack...';
      const askRes = await fetch('/api/social-calendar/ask-nick', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          type: 'refine',
          caption: origText,
          feedback: feedback,
          platform: platform,
          post_type: item.post_type,
          item_name: item.name,
          group_name: item.group_name,
          notes: item.notes,
        })
      });
      const askData = await askRes.json();
      if (askData.request_id) {
        ta.value = '🤖 Nick is writing your caption on Slack... (this can take a minute)';
        // Poll for result
        const result = await scPollNick(askData.request_id);
        if (result) {
          ta.value = result;
          if (scCaptionCache[itemId] && scCaptionCache[itemId][platform] !== undefined) {
            scCaptionCache[itemId][platform] = result;
          }
        } else {
          ta.value = origText;
          alert('Nick did not respond in time. Try again, or use simpler feedback like "shorter" / "add emoji" / "more urgent" / "more casual".');
        }
      } else {
        ta.value = origText;
        alert('Could not reach Nick. Try simpler feedback: "shorter", "more casual", "add urgency", "add emoji".');
      }
    }
  } catch(e) {
    ta.value = origText;
    console.error('Refine error:', e);
    alert('Refine error: ' + e.message);
  }
  ta.disabled = false;
  if (refineBtn) { refineBtn.textContent = '🔄 Refine'; refineBtn.disabled = false; }
}

// Poll for Nick's caption response (up to 3 minutes)
async function scPollNick(requestId, timeoutSec) {
  timeoutSec = timeoutSec || 180;
  const start = Date.now();
  while ((Date.now() - start) < timeoutSec * 1000) {
    await new Promise(r => setTimeout(r, 5000)); // poll every 5 seconds
    try {
      const res = await fetch('/api/social-calendar/ask-nick-status/' + requestId);
      const data = await res.json();
      if (data.status === 'done' && data.caption) return data.caption;
      if (data.status === 'error') return null;
    } catch(e) {
      console.error('Poll error:', e);
    }
  }
  return null;
}

function scCopyCap(textareaId) {
  const ta = document.getElementById(textareaId);
  navigator.clipboard.writeText(ta.value).then(() => {
    const btn = ta.parentElement.querySelector('button:last-child');
    btn.textContent = '✅ Copied!';
    setTimeout(() => btn.textContent = '📋 Copy', 1500);
  });
}

// ── Analyze Speaker Image (Vision API) ──
async function scAnalyzeSpeakerImage(itemId, assetId, btn) {
  btn.disabled = true;
  btn.innerHTML = '⏳ Analyzing image...';
  const statusEl = document.getElementById('sc-analyze-status-' + itemId);

  try {
    const res = await fetch('/api/social-calendar/analyze-speaker-image', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ asset_id: assetId })
    });
    const data = await res.json();

    if (data.needs_key) {
      // No API key configured — show helpful message
      if (statusEl) statusEl.innerHTML = '⚠️ Vision API not configured. Enter details manually, or ask Nick/Kelly to add an OpenAI API key.';
      btn.innerHTML = '🔍 Auto-Read from Image';
      btn.disabled = false;
      return;
    }

    if (data.error) {
      if (statusEl) statusEl.innerHTML = '❌ ' + data.error;
      btn.innerHTML = '🔍 Auto-Read from Image';
      btn.disabled = false;
      return;
    }

    if (data.success && data.speaker_info) {
      const info = data.speaker_info;

      // Fill in the title and firm fields
      const titleEl = document.getElementById('sc-spk-title-' + itemId);
      const firmEl = document.getElementById('sc-spk-firm-' + itemId);
      if (titleEl && info.title) titleEl.value = info.title;
      if (firmEl && info.firm) firmEl.value = info.firm;

      // Set the image type radio
      if (info.speaker_type) {
        const radio = document.querySelector('input[name="sc-imgtype-'+itemId+'"][value="'+info.speaker_type+'"]');
        if (radio) radio.checked = true;
      }

      // Show success
      if (statusEl) {
        statusEl.innerHTML = '✅ Found: <strong>' + scEsc(info.name || '') + '</strong>'
          + (info.title ? ', ' + scEsc(info.title) : '')
          + (info.firm ? ' at ' + scEsc(info.firm) : '')
          + ' (' + (info.speaker_type === 'fireside' ? 'Fireside Spotlight' : 'Confirmed Speaker') + ')';
      }

      btn.innerHTML = '✅ Image Analyzed';
      btn.style.background = '#059669';
    }
  } catch(e) {
    console.error('Image analysis error:', e);
    if (statusEl) statusEl.innerHTML = '❌ Analysis failed. Enter details manually.';
    btn.innerHTML = '🔍 Auto-Read from Image';
    btn.disabled = false;
  }
}

// ── Analyze Any Post Image (General Vision API) ──
async function scAnalyzePostImage(itemId, assetId, btn) {
  const item = scItems.find(i => i.id === itemId);
  btn.disabled = true;
  btn.innerHTML = '⏳ Reading image...';
  const statusEl = document.getElementById('sc-analyze-status-' + itemId);

  try {
    const res = await fetch('/api/social-calendar/analyze-image', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ asset_id: assetId, post_type: item ? item.post_type : '' })
    });
    const data = await res.json();

    if (data.needs_key) {
      if (statusEl) statusEl.innerHTML = '⚠️ Vision API not configured. Ask Nick/Kelly to add an OpenAI API key for image reading.';
      btn.innerHTML = '🔍 Read from Image';
      btn.disabled = false;
      return;
    }

    if (data.error) {
      if (statusEl) statusEl.innerHTML = '❌ ' + data.error;
      btn.innerHTML = '🔍 Read from Image';
      btn.disabled = false;
      return;
    }

    if (data.success && data.image_data) {
      // Cache the image data so Generate Captions can use it
      scImageDataCache[itemId] = data.image_data;

      const d = data.image_data;
      let summary = '✅ Read: <strong>' + scEsc(d.headline || '') + '</strong>';
      if (d.subtitle) summary += ' — ' + scEsc(d.subtitle);
      if (d.partners) summary += ' (with ' + scEsc(d.partners) + ')';
      summary += '<br><span style="color:var(--muted);font-size:0.62rem;">Captions will be based on this. Click Generate Captions to proceed.</span>';

      if (statusEl) statusEl.innerHTML = summary;
      btn.innerHTML = '✅ Image Read';
      btn.style.background = '#059669';
    }
  } catch(e) {
    console.error('Image analysis error:', e);
    if (statusEl) statusEl.innerHTML = '❌ Analysis failed.';
    btn.innerHTML = '🔍 Read from Image';
    btn.disabled = false;
  }
}

// ── Toggle Caption Panel ──
function scToggleCaptions(itemId, headerEl) {
  const panel = document.getElementById('sc-cap-panel-' + itemId);
  const arrow = document.getElementById('sc-cap-arrow-' + itemId);
  if (!panel) return;
  const isOpen = panel.style.display !== 'none';
  panel.style.display = isOpen ? 'none' : '';
  if (arrow) arrow.style.transform = isOpen ? '' : 'rotate(90deg)';
}

// ── Status Updates ──
async function scMarkScheduled(itemId, btn) {
  await scUpdateStatus(itemId, 'Scheduled', btn);
}
async function scMarkPosted(itemId, btn) {
  await scUpdateStatus(itemId, 'Posted', btn);
}

async function scUpdateStatus(itemId, label, btn) {
  if (!confirm('Mark this post as "' + label + '"?')) return;
  const item = scItems.find(i => i.id === itemId);
  btn.disabled = true;
  btn.textContent = label === 'Posted' ? 'Updating & finding links...' : 'Updating...';
  try {
    const res = await fetch('/api/social-calendar/update-status', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: itemId, status_label: label, board_id: item ? item.board_id : '' })
    });
    const data = await res.json();
    if (data.success) {
      // Show found links if any
      if (data.found_links && Object.keys(data.found_links).length > 0) {
        const linkCount = Object.keys(data.found_links).length;
        btn.textContent = '✅ Posted + ' + linkCount + ' link' + (linkCount > 1 ? 's' : '') + ' found!';
      } else if (label === 'Posted') {
        btn.textContent = '✅ Posted (no links matched)';
      } else {
        btn.textContent = '✅ ' + label + '!';
      }
      btn.style.background = '#00c875';
      btn.style.color = '#fff';
      btn.style.border = 'none';
      // Refresh data from Monday to update everywhere (calendar + queue + modals)
      await scLoadData(true);
    } else {
      btn.textContent = '❌ Error: ' + (data.error || 'Unknown');
      console.error('Status update error:', data);
    }
  } catch(e) {
    btn.textContent = '❌ Error';
    console.error('Status update exception:', e);
  }
}

// ── Item Detail Modal ──
async function scShowItem(itemId) {
  const modal = document.getElementById('sc-modal-overlay');
  const content = document.getElementById('sc-modal-content');
  content.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted);">Loading...</div>';
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';

  try {
    const res = await fetch('/api/social-calendar/item/' + itemId);
    const item = await res.json();
    if (item.error) { content.innerHTML = '<p>Error loading item.</p>'; return; }

    const ptColor = SC_POST_TYPE_COLORS[item.post_type] || '#555';
    const stColor = SC_STATUS_COLORS[item.status] || '#777';
    const dateLabel = item.date ? scParseDate(item.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }) : 'No date set';
    const platBadges = item.platforms.map(p => '<span style="background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:3px 8px;font-size:0.75rem;">'+scEsc(p)+'</span>').join(' ');

    let html = '<button onclick="scCloseModal()" style="position:absolute;top:12px;right:16px;background:none;border:none;font-size:1.3rem;cursor:pointer;color:var(--muted);">✕</button>';
    html += '<div style="border-left:4px solid '+ptColor+';padding-left:16px;margin-bottom:20px;">';
    html += '<div style="font-size:1.2rem;font-weight:700;">'+scEsc(item.name)+'</div>';
    html += '<div style="font-size:0.82rem;color:var(--muted);margin-top:4px;">'+scEsc(item.group_name)+'</div>';
    html += '</div>';

    // Info grid
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">';
    html += '<div><span style="font-size:0.72rem;color:var(--muted);display:block;">Post Date</span><span style="font-size:0.88rem;">'+dateLabel+'</span></div>';
    html += '<div><span style="font-size:0.72rem;color:var(--muted);display:block;">Post Type</span><span style="background:'+ptColor+';color:'+scContrastColor(ptColor)+';padding:2px 10px;border-radius:5px;font-size:0.78rem;">'+scEsc(item.post_type || 'None')+'</span></div>';
    html += '<div><span style="font-size:0.72rem;color:var(--muted);display:block;">Status</span><span style="background:'+(item.status ? stColor : '#555')+';color:#fff;padding:2px 10px;border-radius:5px;font-size:0.78rem;">'+scEsc(item.status || 'No status')+'</span></div>';
    // Platform links — show each checked platform with link or ⚠️
    const pLinks = item.platform_links || {};
    const linkablePlats = (item.platforms || []).filter(p => p !== 'In-app Feed');
    if (linkablePlats.length) {
      let linksHtml = '<span style="font-size:0.72rem;color:var(--muted);display:block;margin-bottom:6px;">Post Links</span>';
      linkablePlats.forEach(p => {
        // Map platform checkbox names to link column key names
        const linkKey = p === 'YT Full Length' ? 'YT Full' : p === 'YT Shorts' ? 'YT Short' : p;
        const url = pLinks[linkKey] || pLinks[p] || '';
        const inputId = 'sc-link-edit-' + item.id + '-' + p.replace(/[^a-zA-Z]/g, '');
        if (url === 'ig-story') {
          linksHtml += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">';
          linksHtml += '<span style="font-size:0.78rem;font-weight:500;min-width:90px;">'+scEsc(p)+'</span>';
          linksHtml += '<span style="font-size:0.78rem;color:#E1306C;">📖 Instagram Story (no permanent link)</span>';
          linksHtml += '<button onclick="scEditLink(\\''+item.id+'\\',\\''+scEsc(p)+'\\',\\''+scEsc(item.board_id)+'\\',\\''+inputId+'\\',\\'\\');" style="background:none;border:none;cursor:pointer;font-size:0.8rem;" title="Change">✏️</button>';
          linksHtml += '</div>';
          linksHtml += '<div id="'+inputId+'" style="display:none;margin-bottom:6px;margin-left:96px;"></div>';
        } else if (url) {
          linksHtml += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">';
          linksHtml += '<span style="font-size:0.78rem;font-weight:500;min-width:90px;">'+scEsc(p)+'</span>';
          linksHtml += '<a href="'+scEsc(url)+'" target="_blank" style="color:var(--purple);font-size:0.78rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:400px;">'+scEsc(url)+' ↗</a>';
          linksHtml += '<button onclick="scEditLink(\\''+item.id+'\\',\\''+scEsc(p)+'\\',\\''+scEsc(item.board_id)+'\\',\\''+inputId+'\\',\\''+scEsc(url)+'\\');" style="background:none;border:none;cursor:pointer;font-size:0.8rem;" title="Edit link">✏️</button>';
          linksHtml += '</div>';
        } else {
          const suggestId = 'sc-suggest-' + item.id + '-' + p.replace(/[^a-zA-Z]/g, '');
          linksHtml += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">';
          linksHtml += '<span style="font-size:0.78rem;font-weight:500;min-width:90px;">'+scEsc(p)+'</span>';
          linksHtml += '<span style="font-size:0.78rem;color:#df2f4a;">⚠️ Not found</span>';
          linksHtml += '<button onclick="scSuggestLinks(\\''+item.id+'\\',\\''+scEsc(p)+'\\',\\''+scEsc(item.board_id)+'\\',\\''+suggestId+'\\');" style="background:none;border:none;cursor:pointer;font-size:0.8rem;" title="Show best guesses">🔍</button>';
          linksHtml += '<button onclick="scEditLink(\\''+item.id+'\\',\\''+scEsc(p)+'\\',\\''+scEsc(item.board_id)+'\\',\\''+inputId+'\\',\\'\\');" style="background:none;border:none;cursor:pointer;font-size:0.8rem;" title="Paste link manually">✏️</button>';
          linksHtml += '</div>';
          linksHtml += '<div id="'+suggestId+'" style="display:none;margin-left:96px;margin-bottom:8px;"></div>';
        }
        linksHtml += '<div id="'+inputId+'" style="display:none;margin-bottom:6px;margin-left:96px;"></div>';
      });
      html += '<div style="margin-bottom:12px;">'+linksHtml+'</div>';
    }
    html += '</div>';

    // Platforms
    if (item.platforms.length) {
      html += '<div style="margin-bottom:16px;"><span style="font-size:0.72rem;color:var(--muted);display:block;margin-bottom:4px;">Platforms</span>' + platBadges + '</div>';
    }

    // Notes
    if (item.notes) {
      html += '<div style="margin-bottom:16px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;"><span style="font-size:0.72rem;color:var(--muted);display:block;margin-bottom:4px;">Notes</span><span style="font-size:0.85rem;">'+scEsc(item.notes)+'</span></div>';
    }

    // Assets/files
    if (item.assets && item.assets.length) {
      html += '<div style="margin-bottom:16px;"><span style="font-size:0.72rem;color:var(--muted);display:block;margin-bottom:8px;">Attached Files</span>';
      item.assets.forEach(a => {
        if (['.png','.jpg','.jpeg','.gif','.webp'].includes(a.extension.toLowerCase())) {
          html += '<div style="position:relative;display:inline-block;margin-bottom:8px;">';
          html += '<img src="/api/social-calendar/asset/'+a.id+'" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid var(--border);display:block;" />';
          html += '<a href="/api/social-calendar/asset/'+a.id+'?download=1" download="'+scEsc(a.name)+'" style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.75);color:#fff;border-radius:6px;padding:4px 10px;font-size:0.72rem;text-decoration:none;cursor:pointer;display:flex;align-items:center;gap:4px;">⬇️ Download</a>';
          html += '</div>';
        } else {
          html += '<div style="display:flex;align-items:center;gap:8px;background:var(--surface2);padding:8px 12px;border-radius:6px;border:1px solid var(--border);margin-bottom:4px;font-size:0.82rem;"><span>📎 '+scEsc(a.name)+'</span><a href="/api/social-calendar/asset/'+a.id+'?download=1" download="'+scEsc(a.name)+'" style="color:var(--purple);font-size:0.72rem;text-decoration:none;">⬇️ Download</a></div>';
        }
      });
      html += '</div>';
    }

    // Action buttons (only if board has status column)
    html += '<div style="display:flex;gap:8px;margin-top:16px;border-top:1px solid var(--border);padding-top:16px;">';
    if (item.has_status_col) {
      if (item.status !== 'Scheduled' && item.status !== 'Posted') html += '<button onclick="scMarkScheduled(\\''+item.id+'\\',this);scCloseModal();" style="background:var(--purple);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:0.82rem;cursor:pointer;">✅ Mark as Scheduled</button>';
      if (item.status !== 'Posted') html += '<button onclick="scMarkPosted(\\''+item.id+'\\',this);scCloseModal();" style="background:#00c875;color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:0.82rem;cursor:pointer;">📤 Mark as Posted</button>';
    }
    html += '</div>';

    content.innerHTML = html;
  } catch(e) {
    content.innerHTML = '<p>Error loading item details.</p>';
  }
}

async function scSuggestLinks(itemId, platform, boardId, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Toggle
  if (container.style.display !== 'none') {
    container.style.display = 'none';
    return;
  }
  container.style.display = 'block';
  container.innerHTML = '<div style="color:var(--muted);font-size:0.75rem;padding:4px 0;">🔍 Searching for matches...</div>';

  try {
    const res = await fetch('/api/social-calendar/suggest-links', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: itemId, platform: platform })
    });
    const data = await res.json();
    const candidates = data.candidates || [];

    if (!candidates.length) {
      container.innerHTML = '<div style="color:var(--muted);font-size:0.75rem;padding:4px 0;">No candidates found for this date range.</div>';
      return;
    }

    let html = '<div style="font-size:0.72rem;color:var(--muted);margin-bottom:4px;">Best guesses (click to use):</div>';
    candidates.forEach((c, i) => {
      const scoreBar = c.score >= 5 ? '🟢' : c.score >= 2 ? '🟡' : '🔴';
      const durStr = c.duration ? ' · ' + c.duration : '';
      html += '<div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 10px;margin-bottom:4px;cursor:pointer;" ';
      html += 'onclick="scPickSuggestion(\\'' + itemId + '\\',\\'' + scEsc(platform) + '\\',\\'' + scEsc(boardId) + '\\',\\'' + scEsc(c.url) + '\\',\\'' + containerId + '\\')">';
      html += '<div style="display:flex;align-items:center;gap:6px;">';
      html += '<span>' + scoreBar + '</span>';
      html += '<span style="font-size:0.78rem;font-weight:500;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + scEsc(c.title) + '</span>';
      html += '</div>';
      html += '<div style="font-size:0.7rem;color:var(--muted);margin-top:2px;">' + scEsc(c.date) + durStr + ' · <a href="' + scEsc(c.url) + '" target="_blank" onclick="event.stopPropagation();" style="color:var(--purple);">preview ↗</a></div>';
      html += '</div>';
    });
    // Add "Instagram Story" option for Instagram platform
    if (platform === 'Instagram') {
      html += '<div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 10px;margin-bottom:4px;margin-top:8px;cursor:pointer;border-left:3px solid #E1306C;" ';
      html += 'onclick="scPickSuggestion(\\'' + itemId + '\\',\\'' + scEsc(platform) + '\\',\\'' + scEsc(boardId) + '\\',\\'ig-story\\',\\'' + containerId + '\\')">';
      html += '<div style="display:flex;align-items:center;gap:6px;">';
      html += '<span>📖</span>';
      html += '<span style="font-size:0.78rem;font-weight:500;">This was an Instagram Story (no permanent link)</span>';
      html += '</div>';
      html += '</div>';
    }
    container.innerHTML = html;
  } catch(e) {
    container.innerHTML = '<div style="color:#df2f4a;font-size:0.75rem;">Error loading suggestions.</div>';
  }
}

async function scPickSuggestion(itemId, platform, boardId, url, suggestContainerId) {
  const container = document.getElementById(suggestContainerId);
  if (container) container.innerHTML = '<div style="color:var(--muted);font-size:0.75rem;padding:4px 0;">💾 Saving...</div>';

  try {
    const res = await fetch('/api/social-calendar/update-link', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: itemId, platform: platform, board_id: boardId, url: url })
    });
    const data = await res.json();
    if (data.success) {
      const label = url === 'ig-story' ? '✅ Marked as Instagram Story!' : '✅ Link saved!';
      if (container) container.innerHTML = '<div style="color:#00c875;font-size:0.75rem;padding:4px 0;">' + label + ' Refreshing...</div>';
      // Refresh data and re-open the modal
      await scLoadData(true);
      scShowItem(itemId);
    } else {
      if (container) container.innerHTML = '<div style="color:#df2f4a;font-size:0.75rem;">Error: ' + (data.error || 'Unknown') + '</div>';
    }
  } catch(e) {
    if (container) container.innerHTML = '<div style="color:#df2f4a;font-size:0.75rem;">Error saving link.</div>';
  }
}

function scEditLink(itemId, platform, boardId, containerId, currentUrl) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Toggle: if already showing, hide it
  if (container.style.display !== 'none') {
    container.style.display = 'none';
    return;
  }
  container.style.display = 'flex';
  container.style.gap = '6px';
  container.style.alignItems = 'center';
  container.innerHTML = '<input type="text" id="'+containerId+'-input" value="'+scEsc(currentUrl)+'" placeholder="Paste URL here..." style="flex:1;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:5px;padding:4px 8px;font-size:0.78rem;" />' +
    '<button onclick="scSaveLink(\\''+itemId+'\\',\\''+scEsc(platform)+'\\',\\''+scEsc(boardId)+'\\',\\''+containerId+'-input\\')" style="background:var(--purple);color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:0.72rem;cursor:pointer;">Save</button>' +
    '<button onclick="document.getElementById(\\''+containerId+'\\').style.display=\\'none\\'" style="background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:4px 8px;font-size:0.72rem;cursor:pointer;color:var(--text);">Cancel</button>';
  document.getElementById(containerId+'-input').focus();
}

async function scSaveLink(itemId, platform, boardId, inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const url = input.value.trim();
  input.disabled = true;

  // Find the Save button (sibling of the input)
  const saveBtn = input.parentElement.querySelector('button');
  const origBtnText = saveBtn ? saveBtn.textContent : '';
  if (saveBtn) { saveBtn.textContent = '⏳ Saving...'; saveBtn.disabled = true; }

  try {
    const res = await fetch('/api/social-calendar/update-link', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: itemId, platform: platform, board_id: boardId, url: url })
    });
    const data = await res.json();
    if (data.success) {
      if (saveBtn) { saveBtn.textContent = '✅ Saved!'; }
      // Brief pause so they see the confirmation, then refresh
      await new Promise(r => setTimeout(r, 600));
      await scLoadData(true);
      scShowItem(itemId);
    } else {
      alert('Error saving link: ' + (data.error || 'Unknown'));
      if (saveBtn) { saveBtn.textContent = origBtnText; saveBtn.disabled = false; }
    }
  } catch(e) {
    alert('Error saving link');
    if (saveBtn) { saveBtn.textContent = origBtnText; saveBtn.disabled = false; }
  }
  input.disabled = false;
}

function scCloseModal() {
  document.getElementById('sc-modal-overlay').style.display = 'none';
  document.body.style.overflow = '';
}

// ── Utility ──
function scEsc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function scContrastColor(hex) {
  if (!hex || hex[0] !== '#') return '#fff';
  const r = parseInt(hex.substr(1,2), 16);
  const g = parseInt(hex.substr(3,2), 16);
  const b = parseInt(hex.substr(5,2), 16);
  const lum = (0.299*r + 0.587*g + 0.114*b) / 255;
  return lum > 0.55 ? '#1a1a2e' : '#ffffff';
}

// ── Real-Time Sync via Webhook Version Polling ──
let scSyncVersion = 0;
let scSyncInterval = null;

async function scPollSync() {
  try {
    const res = await fetch('/api/social-calendar/sync-version');
    const data = await res.json();
    if (data.v > scSyncVersion) {
      console.log('[Social Calendar] Webhook sync detected (v' + scSyncVersion + ' → v' + data.v + '), refreshing...');
      scSyncVersion = data.v;
      await scLoadData(true);
    }
  } catch(e) {
    // Silently ignore polling errors
  }
}

function scStartSyncPolling() {
  if (scSyncInterval) return;
  // Poll every 5 seconds for webhook-triggered changes
  scSyncInterval = setInterval(scPollSync, 5000);
  // Also do an initial check
  scPollSync();
}

function scStopSyncPolling() {
  if (scSyncInterval) {
    clearInterval(scSyncInterval);
    scSyncInterval = null;
  }
}

// ── Init ──
function scInit() {
  if (scLoaded) {
    // Already loaded — just re-render from cached data
    scApplyFilters();
    scStartSyncPolling();
    return;
  }
  scLoaded = true;
  // Use server cache first (fast), then user can hit Refresh for fresh data
  scLoadData(false);
  // Start polling for webhook-triggered changes
  scStartSyncPolling();
}
'''
