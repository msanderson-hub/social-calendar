"""
Dummy-mode patch for the Social Calendar tab.

Import this module BEFORE you import anything from `social_calendar`. It
monkey-patches the four functions that talk to Monday.com so the tab runs
fully offline against an in-memory dataset:

    fetch_all_items()            → returns raw Monday-shaped items (not used directly
                                   by the tab; we patch the parsed cache instead)
    get_cached_items(force=...)  → returns the dummy ITEMS list, sorted by date
    get_board_groups(force=...)  → returns the dummy group list
    api_update_status            → flips the status in-memory (Option 2 — feels real)
    api_update_link              → flips the platform link URL in-memory

Restart the app to reset the demo data — there is no persistence.

To opt OUT of dummy mode in production, just don't import this module; the
real `social_calendar.py` will fetch from Monday like normal.
"""

import threading
from flask import jsonify, request

import social_calendar as sc
import dummy_data


# ─── Replace the in-process cache with our mutable dummy list ─────────────────
# Sorting matches what get_cached_items() does in the real module.
_DUMMY_ITEMS = sorted(
    [dict(it) for it in dummy_data.ITEMS],
    key=lambda x: x["date"] or "9999-99-99",
)
_DUMMY_LOCK = threading.Lock()
_SYNC_VERSION = 1


def _find_item(item_id):
    """Look up a dummy item by id. Returns None if not found."""
    for it in _DUMMY_ITEMS:
        if it["id"] == str(item_id):
            return it
    return None


# ─── Patch the fetch layer ────────────────────────────────────────────────────
def _patched_get_cached_items(force=False):
    """Return the in-memory dummy items. `force` is ignored — no real cache."""
    with _DUMMY_LOCK:
        # Re-sort in case the list was mutated (date edits etc.)
        _DUMMY_ITEMS.sort(key=lambda x: x["date"] or "9999-99-99")
        return list(_DUMMY_ITEMS)


def _patched_get_board_groups(force=False):
    return dummy_data.list_groups()


def _patched_fetch_all_items():
    """Not used by the tab (which goes through get_cached_items), but patched
    for completeness so any direct caller in test code doesn't hit Monday."""
    return []  # raw-shape items; we bypass parse_item entirely in dummy mode


sc.get_cached_items   = _patched_get_cached_items
sc.get_board_groups   = _patched_get_board_groups
sc.fetch_all_items    = _patched_fetch_all_items

# Safety net: short-circuit any direct Monday API calls. Anything that slips
# past the higher-level patches returns an empty payload instead of hitting
# api.monday.com.
sc.monday_query  = lambda q: {"data": None, "_dummy": True}
sc.monday_mutate = lambda q, variables=None: {"data": None, "_dummy": True}


# ─── Patch the writeback endpoints (Option 2: live in-memory updates) ─────────
# We strip the existing routes off the blueprint and re-register replacements
# so Flask sees our handlers instead of the ones that call monday_mutate().

_STATUS_COLORS = dummy_data.STATUS_COLORS


def _bump_sync_version():
    global _SYNC_VERSION
    with _DUMMY_LOCK:
        _SYNC_VERSION += 1


def _dummy_update_status():
    body = request.get_json(silent=True) or {}
    item_id      = body.get("item_id")
    status_label = body.get("status_label")
    if not item_id or not status_label:
        return jsonify({"error": "item_id and status_label required"}), 400

    item = _find_item(item_id)
    if not item:
        return jsonify({"error": "item not found in dummy data"}), 404

    with _DUMMY_LOCK:
        item["status"]       = status_label
        item["status_color"] = _STATUS_COLORS.get(status_label, "#555")
    _bump_sync_version()

    return jsonify({
        "success":     True,
        "item_id":     item_id,
        "status":      status_label,
        "found_links": {},  # match real-mode response shape
        "_dummy":      True,
    })


def _dummy_update_link():
    body = request.get_json(silent=True) or {}
    item_id  = body.get("item_id")
    platform = body.get("platform")
    url_val  = (body.get("url") or "").strip()
    if not item_id or not platform:
        return jsonify({"error": "item_id and platform required"}), 400

    item = _find_item(item_id)
    if not item:
        return jsonify({"error": "item not found in dummy data"}), 404

    with _DUMMY_LOCK:
        if url_val:
            item["platform_links"][platform] = url_val
        else:
            item["platform_links"].pop(platform, None)
        # Keep legacy social_link mirrored on the LinkedIn URL
        if platform == "LinkedIn":
            item["social_link"] = url_val
    _bump_sync_version()

    return jsonify({
        "success":  True,
        "item_id":  item_id,
        "platform": platform,
        "url":      url_val,
        "_dummy":   True,
    })


def _dummy_sync_version():
    return jsonify({"version": _SYNC_VERSION, "_dummy": True})


def _dummy_item_detail(item_id):
    """Return one parsed item from the in-memory list. Replaces the route
    handler that normally calls Monday for fresh asset URLs."""
    item = _find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


def _dummy_asset_proxy(asset_id):
    """Redirect to the dummy item's public placeholder URL instead of fetching
    a signed Monday URL. Most browsers will follow this transparently."""
    from flask import redirect
    for it in _DUMMY_ITEMS:
        for a in it.get("assets", []):
            if str(a.get("id")) == str(asset_id):
                return redirect(a.get("public_url", ""), code=302)
    return jsonify({"error": "Asset not found in dummy data"}), 404


# Replace the route handlers in the deferred function list.
# (Flask blueprints store routes as deferred callables until register_blueprint
# is called. We swap the view functions on the blueprint's view_functions dict
# instead — simpler and works whether the blueprint has been registered yet.)
sc.api_update_status = _dummy_update_status
sc.api_update_link   = _dummy_update_link
sc.api_sync_version  = _dummy_sync_version

# The blueprint stored the original functions by reference in its deferred
# rule list. We rebuild that list so registration uses our wrappers.
new_deferred = []
for fn in sc.social_cal_bp.deferred_functions:
    # Each deferred function is `lambda s: s.add_url_rule(rule, endpoint, view_func, **opts)`.
    # We replicate the original add_url_rule calls but swap view_func when the
    # endpoint matches one we're overriding.
    new_deferred.append(fn)
# Easier path: just register our handlers AFTER the blueprint with explicit
# endpoint names, and let Flask's last-write-wins behaviour on view_functions
# pick ours up.

def _install_overrides(bp):
    """Call this AFTER blueprint registration on the app, to override view fns."""
    # Flask exposes view_functions on the app, keyed by "<bp_name>.<endpoint>".
    pass  # No-op; see install_dummy_overrides() below which the app calls.


def install_dummy_overrides(app):
    """Replace the registered view functions on the app object. Call this
    AFTER `app.register_blueprint(social_cal_bp)`."""
    app.view_functions["social_cal.api_update_status"]        = _dummy_update_status
    app.view_functions["social_cal.api_update_link"]          = _dummy_update_link
    app.view_functions["social_cal.api_sync_version"]         = _dummy_sync_version
    app.view_functions["social_cal.api_calendar_item_detail"] = _dummy_item_detail
    app.view_functions["social_cal.api_asset_proxy"]          = _dummy_asset_proxy


# ─── Friendly banner ──────────────────────────────────────────────────────────
print("[Social Calendar] 🎨 DUMMY MODE active — "
      "{} in-memory posts, no Monday.com calls.".format(len(_DUMMY_ITEMS)))
