#!/usr/bin/env python3
"""
Social Calendar — iConnections Marketing Dashboard
Vibe Coding Contest Entry — Enhanced UI Edition

Run: python standalone_app.py
     open http://127.0.0.1:8989/
"""

import os
import _envloader  # noqa: F401

USE_DUMMY = os.environ.get("DUMMY", "1") != "0"

if USE_DUMMY:
    import dummy_patch  # noqa: F401

from flask import Flask
from social_calendar import (
    social_cal_bp,
    SOCIAL_CAL_TAB_HTML as _ORIG_HTML,
    SOCIAL_CAL_TAB_JS   as _ORIG_JS,
)

app = Flask(__name__)
app.secret_key = "social-calendar-standalone-demo"
app.register_blueprint(social_cal_bp)

if USE_DUMMY:
    import dummy_patch
    dummy_patch.install_dummy_overrides(app)


# ─── Design System CSS ────────────────────────────────────────────────────────
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

:root {
  --bg:           #06060f;
  --surface:      #0d0d20;
  --surface2:     #111128;
  --surface3:     #181836;
  --border:       #1c1c3e;
  --border2:      #272755;
  --text:         #e2e2f4;
  --text2:        #9494be;
  --muted:        #55557e;
  --purple:       #7c6fff;
  --purple2:      #5a4ed4;
  --purple-glow:  rgba(124,111,255,0.16);
  --teal:         #5eead4;
  --pink:         #f472b6;
  --green:        #4ade80;
  --yellow:       #facc15;
  --orange:       #fb923c;
  --red:          #f87171;
  --radius:       10px;
  --radius-lg:    16px;
  --shadow:       0 4px 24px rgba(0,0,0,0.5);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { color-scheme: dark; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Sans', -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Subtle dot-grid background */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(circle, #1a1a42 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}

/* Radial glow top */
body::after {
  content: '';
  position: fixed;
  top: -200px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 500px;
  background: radial-gradient(ellipse, rgba(124,111,255,0.08) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

main {
  position: relative;
  z-index: 1;
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 32px;
}

/* ── Typography ── */
.page-title {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #fff 20%, var(--purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}
.page-sub {
  color: var(--muted);
  font-size: 0.79rem;
  margin-top: 4px;
  letter-spacing: 0.01em;
}
.page-header { margin-bottom: 22px; }

/* ── Tabs ── */
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.81rem;
  font-weight: 500;
  color: var(--text2);
  border: 1px solid transparent;
  background: transparent;
  transition: all 0.16s ease;
  font-family: inherit;
}
.tab:hover { color: var(--text); background: var(--surface3); }
.tab.active {
  background: var(--purple);
  color: #fff;
  box-shadow: 0 0 20px rgba(124,111,255,0.38);
  border-color: rgba(255,255,255,0.1);
}

/* ── Buttons ── */
button { font-family: inherit; cursor: pointer; }

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 13px;
  border-radius: 8px;
  font-size: 0.81rem;
  font-weight: 500;
  border: 1px solid var(--border2);
  background: var(--surface2);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
  white-space: nowrap;
}
.btn:hover {
  background: var(--surface3);
  border-color: var(--border2);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.btn:active { transform: translateY(0); }

.btn-primary {
  background: var(--purple);
  border-color: rgba(255,255,255,0.12);
  color: #fff;
  box-shadow: 0 0 14px rgba(124,111,255,0.3);
}
.btn-primary:hover {
  background: var(--purple2);
  box-shadow: 0 0 22px rgba(124,111,255,0.5);
}

/* ── Inputs ── */
select, input[type="date"], input[type="text"] {
  background: var(--surface2);
  color: var(--text);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.81rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2355557e'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
}
select:focus, input:focus {
  border-color: var(--purple);
  box-shadow: 0 0 0 3px var(--purple-glow);
}

/* ── Spinner ── */
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--muted);
  padding: 80px;
  font-size: 0.88rem;
}
.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border2);
  border-top-color: var(--purple);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Demo banner ── */
.demo-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin-bottom: 20px;
  border-radius: var(--radius);
  background: linear-gradient(90deg, rgba(124,111,255,0.09), rgba(94,234,212,0.05));
  border: 1px solid rgba(124,111,255,0.2);
  font-size: 0.79rem;
  color: var(--text2);
}
.demo-banner b { color: var(--purple); }

/* ── Calendar day cells ── */
.sc-day-cell {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
  min-height: 120px;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}
.sc-day-cell.today {
  border-color: var(--purple);
  box-shadow: inset 0 0 0 1px var(--purple);
}
.sc-day-cell.drop-hover {
  border-color: var(--teal) !important;
  background: rgba(94,234,212,0.04) !important;
  box-shadow: 0 0 0 2px rgba(94,234,212,0.2) !important;
}

/* ── Post chips ── */
.sc-post-chip {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 7px;
  border-radius: 6px;
  margin-bottom: 3px;
  font-size: 0.685rem;
  font-weight: 500;
  cursor: pointer;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: transform 0.12s ease, box-shadow 0.12s ease, opacity 0.15s;
  border: 1px solid rgba(255,255,255,0.08);
  position: relative;
}
.sc-post-chip:hover {
  transform: translateY(-1px) scale(1.01);
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  z-index: 2;
}
.sc-post-chip.dragging { opacity: 0.3; transform: scale(0.97); }
.sc-post-chip[draggable="true"] { cursor: grab; }
.sc-post-chip[draggable="true"]:active { cursor: grabbing; }
.sc-post-chip-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }

/* Status dot */
.sc-status-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.25);
  flex-shrink: 0;
}

/* ── Month grid ── */
.sc-month-cell {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 5px;
  min-height: 72px;
  transition: border-color 0.15s, background 0.15s;
}
.sc-month-cell.today { border-color: var(--purple); }
.sc-month-cell.other-month { opacity: 0.3; background: rgba(6,6,15,0.5); }
.sc-month-cell.drop-hover {
  border-color: var(--teal) !important;
  background: rgba(94,234,212,0.05) !important;
  box-shadow: 0 0 0 2px rgba(94,234,212,0.18) !important;
}

/* ── Queue cards ── */
.sc-queue-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 15px 18px 14px;
  margin-bottom: 10px;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}
.sc-queue-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--type-color, var(--purple));
}
.sc-queue-card:hover {
  border-color: var(--border2);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

/* ── Platform badges ── */
.plat-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: 5px;
  padding: 2px 7px;
  font-size: 0.66rem;
  font-weight: 500;
  color: var(--text2);
}

/* ── Status pills ── */
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

/* ── Section dividers ── */
.sc-section-divider {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 30px 0 16px;
}
.sc-section-divider::before, .sc-section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
.sc-section-label {
  font-size: 0.67rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  font-weight: 700;
  white-space: nowrap;
}

/* ── Modal ── */
#sc-modal-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 9999;
  overflow-y: auto;
  padding: 40px 16px;
}

#sc-modal-content {
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 20px;
  max-width: 820px;
  margin: 0 auto;
  position: relative;
  overflow: hidden;
  box-shadow: 0 40px 100px rgba(0,0,0,0.8), 0 0 0 1px rgba(124,111,255,0.07);
  animation: modalIn 0.24s cubic-bezier(0.34,1.42,0.64,1);
}

@keyframes modalIn {
  from { transform: scale(0.93) translateY(14px); opacity: 0; }
  to   { transform: scale(1) translateY(0); opacity: 1; }
}

.sc-modal-header {
  padding: 26px 28px 20px;
  position: relative;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg, rgba(124,111,255,0.06), transparent 60%);
}

.sc-modal-body { padding: 22px 28px 28px; }

/* Info tiles */
.sc-info-tile {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
}
.sc-info-tile-label {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  margin-bottom: 6px;
  font-weight: 700;
}

/* Caption preview */
.sc-caption-block {
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 10px;
}
.sc-caption-block-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--purple);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sc-caption-textarea {
  width: 100%;
  min-height: 80px;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border2);
  border-radius: 7px;
  padding: 10px;
  font-size: 0.79rem;
  resize: vertical;
  font-family: 'DM Mono', monospace;
  line-height: 1.6;
  transition: border-color 0.15s;
  outline: none;
}
.sc-caption-textarea:focus { border-color: var(--purple); box-shadow: 0 0 0 2px var(--purple-glow); }

/* Empty states */
.sc-empty {
  text-align: center;
  padding: 30px 20px;
  color: var(--muted);
  font-size: 0.84rem;
  background: var(--surface2);
  border: 1px dashed var(--border2);
  border-radius: var(--radius);
}
.sc-empty-icon { font-size: 1.8rem; margin-bottom: 8px; opacity: 0.45; }

/* Search bar */
.sc-search-wrap {
  position: relative;
  flex: 1;
  min-width: 180px;
  max-width: 300px;
}
.sc-search-wrap svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.4;
  pointer-events: none;
  flex-shrink: 0;
}
#sc-search {
  width: 100%;
  padding: 6px 10px 6px 32px;
  background: var(--surface2);
  color: var(--text);
  border: 1px solid var(--border2);
  border-radius: 8px;
  font-size: 0.81rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
#sc-search:focus {
  border-color: var(--purple);
  box-shadow: 0 0 0 3px var(--purple-glow);
}
#sc-search::placeholder { color: var(--muted); }

/* Search highlight */
.sc-search-match {
  background: rgba(124,111,255,0.28);
  border-radius: 2px;
  color: inherit;
}

/* Drag ghost */
.sc-drag-ghost {
  position: fixed;
  pointer-events: none;
  z-index: 99999;
  padding: 6px 11px;
  border-radius: 7px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 10px 30px rgba(0,0,0,0.6);
  white-space: nowrap;
  max-width: 210px;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.9;
  border: 1px solid rgba(255,255,255,0.12);
}

/* Animations */
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.sc-animate-in { animation: fadeSlideIn 0.26s ease both; }

/* Nav */
.sc-nav-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.sc-nav-label {
  font-weight: 700;
  font-size: 0.98rem;
  min-width: 220px;
  text-align: center;
  letter-spacing: -0.01em;
}

.sc-topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.sc-filter-label {
  font-size: 0.73rem;
  color: var(--muted);
  white-space: nowrap;
}
.sc-view-tabs { display: flex; gap: 4px; margin-bottom: 14px; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* Toast */
#sc-toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}
.sc-toast {
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  padding: 9px 16px;
  font-size: 0.81rem;
  color: var(--text);
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  animation: toastIn 0.22s ease;
  max-width: 300px;
}
.sc-toast.success { border-color: rgba(74,222,128,0.35); }
.sc-toast.error   { border-color: rgba(248,113,113,0.35); }
@keyframes toastIn {
  from { transform: translateX(16px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}
"""

# ─── Enhanced HTML ────────────────────────────────────────────────────────────
ENHANCED_HTML = '''
<div id="sc-toast-container"></div>

<div id="socialcal-view" style="display:none">
  <!-- Page Header -->
  <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;">
    <div>
      <div class="page-title">Social Calendar</div>
      <div class="page-sub">iConnections Marketing &middot; Drag to reschedule &middot; Search &middot; AI caption preview</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <span id="sc-item-count" style="color:var(--muted);font-size:0.75rem;background:var(--surface2);border:1px solid var(--border);padding:4px 10px;border-radius:20px;font-weight:500;"></span>
      <button onclick="scRefresh()" class="btn btn-primary" id="sc-refresh-btn">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
        Refresh
      </button>
    </div>
  </div>

  <!-- Filter Toolbar -->
  <div class="sc-topbar">
    <div class="sc-search-wrap">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="sc-search" placeholder="Search posts…" oninput="scApplyFilters()" />
    </div>
    <div style="display:flex;align-items:center;gap:5px;">
      <span class="sc-filter-label">Group</span>
      <select id="sc-group-filter" onchange="scApplyFilters()"><option value="all">All Groups</option></select>
    </div>
    <div style="display:flex;align-items:center;gap:5px;">
      <span class="sc-filter-label">Type</span>
      <select id="sc-type-filter" onchange="scApplyFilters()"><option value="all">All Types</option></select>
    </div>
    <div style="display:flex;align-items:center;gap:5px;">
      <span class="sc-filter-label">Status</span>
      <select id="sc-status-filter" onchange="scApplyFilters()">
        <option value="all">All Statuses</option>
        <option value="Working on it">Working on it</option>
        <option value="Scheduled">Scheduled</option>
        <option value="For Scheduling">For Scheduling</option>
        <option value="Posted">Posted</option>
        <option value="Need Content">Need Content</option>
        <option value="none">No Status</option>
      </select>
    </div>
  </div>

  <!-- View Toggle + Nav combined -->
  <div class="sc-view-tabs">
    <button class="tab active" onclick="scSwitchCalView('weekly')" id="sc-cal-btn-weekly">Weekly</button>
    <button class="tab" onclick="scSwitchCalView('monthly')" id="sc-cal-btn-monthly">Monthly</button>
  </div>

  <div class="sc-nav-bar">
    <button onclick="scNavPrev()" class="btn" style="padding:6px 12px;">&#9664;</button>
    <span id="sc-cal-label" class="sc-nav-label"></span>
    <button onclick="scNavNext()" class="btn" style="padding:6px 12px;">&#9654;</button>
    <button onclick="scNavToday()" class="btn" style="font-size:0.78rem;">Today</button>
    <input type="date" id="sc-cal-jump" onchange="scJumpToDate()" />
  </div>

  <!-- Calendar Grid -->
  <div id="sc-calendar-grid" style="margin-bottom:40px;"></div>

  <!-- Queue -->
  <div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
      <div style="font-size:0.98rem;font-weight:700;letter-spacing:-0.01em;">Post Queue</div>
      <div style="display:flex;align-items:center;gap:6px;margin-left:8px;">
        <button onclick="scUpcomingPrev()" class="btn" style="padding:5px 10px;">&#9664;</button>
        <span id="sc-upcoming-label" style="font-weight:500;font-size:0.83rem;min-width:180px;text-align:center;color:var(--text2);"></span>
        <button onclick="scUpcomingNext()" class="btn" style="padding:5px 10px;">&#9654;</button>
      </div>
      <button onclick="scUpcomingThisWeek()" class="btn" style="font-size:0.74rem;padding:5px 10px;">This Week</button>
    </div>
    <div id="sc-upcoming-cards"></div>
  </div>

  <!-- Modal -->
  <div id="sc-modal-overlay" onclick="if(event.target===this)scCloseModal()">
    <div id="sc-modal-content"></div>
  </div>
</div>
'''

# ─── Enhanced JS: layered on top of original ─────────────────────────────────
ENHANCED_JS = _ORIG_JS + r"""

// ═══════════════════════════════════════════════════════════
//  ENHANCED UI — SOCIAL CALENDAR GLOW-UP
// ═══════════════════════════════════════════════════════════

// ── Toast ─────────────────────────────────────────────────
function scToast(msg, type='info', ms=2800) {
  const c = document.getElementById('sc-toast-container');
  if (!c) return;
  const el = document.createElement('div');
  el.className = 'sc-toast ' + type;
  const icon = type === 'success' ? '✓ ' : type === 'error' ? '✕ ' : 'ℹ ';
  el.textContent = icon + msg;
  c.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.28s, transform 0.28s';
    el.style.opacity = '0'; el.style.transform = 'translateX(10px)';
    setTimeout(() => el.remove(), 280);
  }, ms);
}

// ── Apply Filters (with search) ────────────────────────────
function scApplyFilters() {
  const gf = document.getElementById('sc-group-filter').value;
  const tf = document.getElementById('sc-type-filter').value;
  const sf = document.getElementById('sc-status-filter').value;
  const sq = ((document.getElementById('sc-search')||{}).value||'').toLowerCase().trim();

  scFilteredItems = scItems.filter(i => {
    if (gf !== 'all' && i.group_name !== gf) return false;
    if (tf !== 'all' && i.post_type !== tf) return false;
    if (sf !== 'all') {
      if (sf === 'none') { if (i.status) return false; }
      else if (i.status !== sf) return false;
    }
    if (sq && !i.name.toLowerCase().includes(sq) && !(i.notes||'').toLowerCase().includes(sq)) return false;
    return true;
  });

  const el = document.getElementById('sc-item-count');
  if (el) el.textContent = scFilteredItems.length + ' of ' + scItems.length + ' posts';
  scRenderCalendar();
  scRenderUpcoming();
}

// ── Weekly calendar (with drag-drop) ──────────────────────
function scRenderWeekly() {
  const ws = scWeekStart(scCalDate), we = scWeekEnd(scCalDate);
  document.getElementById('sc-cal-label').textContent = scFmtRange(ws, we);
  const days = [];
  for (let i=0;i<7;i++){const d=new Date(ws);d.setDate(d.getDate()+i);days.push(d);}
  const today = scFmtDate(new Date());
  const sq = ((document.getElementById('sc-search')||{}).value||'').toLowerCase().trim();

  let html = '<div style="display:grid;grid-template-columns:0.6fr 1fr 1fr 1fr 1fr 1fr 0.6fr;gap:5px;">';
  days.forEach(day => {
    const ds = scFmtDate(day);
    const isToday = ds === today;
    const dayItems = scFilteredItems.filter(it => it.date === ds);
    const dName = day.toLocaleDateString('en-US',{weekday:'short'});
    const dNum  = day.getDate();

    html += `<div class="sc-day-cell${isToday?' today':''}"
      data-date="${ds}"
      ondragover="scDragOver(event,this)"
      ondragleave="scDragLeave(event,this)"
      ondrop="scDrop(event,this,'${ds}')">`;

    html += `<div style="font-size:0.68rem;font-weight:700;color:${isToday?'var(--purple)':'var(--muted)'};margin-bottom:7px;display:flex;justify-content:space-between;align-items:center;">
      <span>${dName}</span>
      <span style="background:${isToday?'var(--purple)':'var(--surface3)'};color:${isToday?'#fff':'var(--text2)'};border-radius:5px;padding:1px 5px;font-size:0.65rem;">${dNum}</span>
    </div>`;

    dayItems.forEach(it => {
      const bg = SC_POST_TYPE_COLORS[it.post_type]||'#555';
      const fg = scContrastColor(bg);
      const sc = SC_STATUS_COLORS[it.status]||'transparent';
      const nameHtml = sq && it.name.toLowerCase().includes(sq)
        ? it.name.replace(new RegExp(sq.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'), m=>`<mark class="sc-search-match">${m}</mark>`)
        : scEsc(it.name);
      html += `<div class="sc-post-chip"
        draggable="true" data-id="${it.id}" data-date="${it.date}"
        style="background:${bg};color:${fg};"
        onclick="scShowItem('${it.id}');event.stopPropagation();"
        ondragstart="scDragStart(event,'${it.id}','${it.date}')"
        ondragend="scDragEnd(event,this)"
        title="${scEsc(it.name)} · ${scEsc(it.post_type)}${it.status?' · '+scEsc(it.status):''}">
        <span class="sc-status-dot" style="background:${sc};"></span>
        <span class="sc-post-chip-text">${nameHtml}</span>
      </div>`;
    });

    if (!dayItems.length) {
      html += `<div style="font-size:0.6rem;color:var(--muted);opacity:0.3;text-align:center;padding-top:14px;">—</div>`;
    }
    html += '</div>';
  });
  html += '</div>';
  document.getElementById('sc-calendar-grid').innerHTML = html;
}

// ── Monthly calendar (with drag-drop) ─────────────────────
function scRenderMonthly() {
  const ms = scMonthStart(scCalDate);
  document.getElementById('sc-cal-label').textContent = scFmtMonth(scCalDate);
  const calStart = scWeekStart(ms);
  const today = scFmtDate(new Date());
  const sq = ((document.getElementById('sc-search')||{}).value||'').toLowerCase().trim();

  let html = '<div style="display:grid;grid-template-columns:0.65fr 1fr 1fr 1fr 1fr 1fr 0.65fr;gap:3px;">';
  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
    html += `<div style="text-align:center;font-size:0.63rem;color:var(--muted);font-weight:700;padding:5px 0;letter-spacing:0.07em;text-transform:uppercase;">${d}</div>`;
  });

  const cur = new Date(calStart);
  for (let w=0;w<6;w++){
    for (let d=0;d<7;d++){
      const ds = scFmtDate(cur);
      const isToday = ds === today;
      const inMonth = cur.getMonth() === scCalDate.getMonth();
      const dayItems = scFilteredItems.filter(it => it.date === ds);

      html += `<div class="sc-month-cell${isToday?' today':''}${!inMonth?' other-month':''}"
        data-date="${ds}"
        ondragover="scDragOver(event,this)"
        ondragleave="scDragLeave(event,this)"
        ondrop="scDrop(event,this,'${ds}')">`;

      html += `<div style="font-size:0.63rem;font-weight:${isToday?'800':'400'};color:${isToday?'var(--purple)':'var(--muted)'};margin-bottom:2px;display:flex;justify-content:space-between;">
        <span style="${isToday?'background:var(--purple);color:#fff;border-radius:3px;padding:0 3px;':''}">${cur.getDate()}</span>
        ${dayItems.length>2?`<span style="font-size:0.57rem;cursor:pointer;opacity:0.6;" onclick="scCalDate=scParseDate('${ds}');scSwitchCalView('weekly')">+${dayItems.length-2}</span>`:''}
      </div>`;

      dayItems.slice(0,2).forEach(it=>{
        const bg = SC_POST_TYPE_COLORS[it.post_type]||'#555';
        const fg = scContrastColor(bg);
        const sc2 = SC_STATUS_COLORS[it.status]||'transparent';
        const nameHtml = sq && it.name.toLowerCase().includes(sq)
          ? it.name.replace(new RegExp(sq.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'),m=>`<mark class="sc-search-match">${m}</mark>`)
          : scEsc(it.name);
        html += `<div class="sc-post-chip"
          draggable="true" data-id="${it.id}" data-date="${it.date}"
          style="background:${bg};color:${fg};padding:2px 5px;font-size:0.6rem;"
          onclick="scShowItem('${it.id}');event.stopPropagation();"
          ondragstart="scDragStart(event,'${it.id}','${it.date}')"
          ondragend="scDragEnd(event,this)"
          title="${scEsc(it.name)}">
          <span class="sc-status-dot" style="background:${sc2};width:4px;height:4px;"></span>
          <span class="sc-post-chip-text">${nameHtml}</span>
        </div>`;
      });
      html += '</div>';
      cur.setDate(cur.getDate()+1);
    }
    if (cur.getMonth()>scCalDate.getMonth()&&cur.getFullYear()>=scCalDate.getFullYear()&&w>=3) break;
  }
  html += '</div>';
  document.getElementById('sc-calendar-grid').innerHTML = html;
}

// ── Drag and Drop ──────────────────────────────────────────
let scDragItemId = null, scDragOrigDate = null, scDragGhost = null;

function scDragStart(event, itemId, origDate) {
  scDragItemId = itemId; scDragOrigDate = origDate;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', itemId);

  // Blank drag image
  const blank = document.createElement('canvas');
  blank.width=1; blank.height=1;
  event.dataTransfer.setDragImage(blank, 0, 0);

  const item = scItems.find(i => i.id === itemId);
  if (item) {
    const g = document.createElement('div');
    g.className = 'sc-drag-ghost';
    g.style.background = SC_POST_TYPE_COLORS[item.post_type]||'#555';
    g.style.color = scContrastColor(SC_POST_TYPE_COLORS[item.post_type]||'#555');
    g.textContent = item.name;
    document.body.appendChild(g);
    scDragGhost = g;
    g.style.left = (event.clientX+14)+'px';
    g.style.top  = (event.clientY-12)+'px';
  }
  setTimeout(() => { if(event.target) event.target.classList.add('dragging'); }, 0);
  document.addEventListener('dragover', _scGhostMove, {passive:true});
}

function _scGhostMove(e) {
  if (scDragGhost) {
    scDragGhost.style.left = (e.clientX+14)+'px';
    scDragGhost.style.top  = (e.clientY-12)+'px';
  }
}

function scDragEnd(event, el) {
  if (scDragGhost) { scDragGhost.remove(); scDragGhost = null; }
  document.removeEventListener('dragover', _scGhostMove);
  if (el) el.classList.remove('dragging');
  document.querySelectorAll('.drop-hover').forEach(c=>c.classList.remove('drop-hover'));
}

function scDragOver(event, cell) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  cell.classList.add('drop-hover');
}

function scDragLeave(event, cell) {
  if (!cell.contains(event.relatedTarget)) cell.classList.remove('drop-hover');
}

async function scDrop(event, cell, newDate) {
  event.preventDefault();
  cell.classList.remove('drop-hover');

  const itemId = scDragItemId, origDate = scDragOrigDate;
  scDragItemId = null; scDragOrigDate = null;

  if (!itemId || origDate === newDate) return;

  const item = scItems.find(i => i.id === itemId);
  if (!item) return;

  // Optimistic update
  item.date = newDate;
  scApplyFilters();
  const newLabel = scParseDate(newDate).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  scToast(`"${item.name.slice(0,30)}…" → ${newLabel}`, 'success');

  // Writeback (dummy mode: fire and forget)
  try {
    await fetch('/api/social-calendar/update-status', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id:itemId, status_label:item.status||'', board_id:item.board_id, new_date:newDate})
    });
  } catch(e) { /* dummy mode — fine */ }
}

// ── Upcoming queue renderer ────────────────────────────────
function scRenderUpcoming() {
  const ws = scWeekStart(scUpcomingDate), we = scWeekEnd(scUpcomingDate);
  document.getElementById('sc-upcoming-label').textContent = scFmtRange(ws, we);
  const ws2=scFmtDate(ws), we2=scFmtDate(we);
  const weekItems = scFilteredItems.filter(it=>it.date>=ws2&&it.date<=we2);
  weekItems.sort((a,b)=>a.date.localeCompare(b.date));

  const needs = weekItems.filter(it=>it.status!=='Scheduled'&&it.status!=='Posted');
  const sched = weekItems.filter(it=>it.status==='Scheduled');
  const posted = weekItems.filter(it=>it.status==='Posted');

  const mkSection = (label, items, icon) => {
    let h = `<div class="sc-section-divider"><span class="sc-section-label">${icon} ${label} <span style="opacity:0.45;">(${items.length})</span></span></div>`;
    if (!items.length) {
      h += `<div class="sc-empty"><div class="sc-empty-icon">${icon}</div><div>${label==='Needs Scheduling'?'All caught up this week!':'Nothing here.'}</div></div>`;
    } else {
      items.forEach(it => { h += scRenderUpcomingCard(it); });
    }
    return h;
  };

  document.getElementById('sc-upcoming-cards').innerHTML =
    mkSection('Needs Scheduling', needs, '📋') +
    mkSection('Scheduled', sched, '✅') +
    mkSection('Posted', posted, '📤');

  document.querySelectorAll('.sc-queue-card').forEach((el,i)=>{
    el.style.animationDelay = (i*0.035)+'s';
    el.classList.add('sc-animate-in');
  });

  weekItems.forEach(it => {
    if (scCaptionCache[it.id]) scRenderCaptions(it.id, scCaptionCache[it.id]);
  });
}

// ── Queue card ─────────────────────────────────────────────
function scRenderUpcomingCard(it) {
  const ptColor = SC_POST_TYPE_COLORS[it.post_type]||'#555';
  const stColor = SC_STATUS_COLORS[it.status]||'#444';
  const dateLabel = scParseDate(it.date).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  const itLinks = it.platform_links||{};
  const sq = ((document.getElementById('sc-search')||{}).value||'').toLowerCase().trim();

  const platBadges = it.platforms.map(p=>{
    const lk = p==='YT Full Length'?'YT Full':p==='YT Shorts'?'YT Short':p;
    const lv = itLinks[lk];
    const li = (it.status==='Posted'&&p!=='In-app Feed')?(lv==='ig-story'?' 📖':lv?' ✓':' !'):'';
    const lc = (it.status==='Posted'&&p!=='In-app Feed')?(lv?'rgba(74,222,128,0.3)':lv==='ig-story'?'':'rgba(248,113,113,0.3)'):'';
    return `<span class="plat-badge" style="${lc?'border-color:'+lc:''}">${scEsc(p)}${li}</span>`;
  }).join('');

  const nameHtml = sq && it.name.toLowerCase().includes(sq)
    ? it.name.replace(new RegExp(sq.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'),m=>`<mark class="sc-search-match">${m}</mark>`)
    : scEsc(it.name);

  let h = `<div class="sc-queue-card" style="--type-color:${ptColor};" onclick="scShowItem('${it.id}')" title="Click to view details">`;
  h += `<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
    <div style="flex:1;min-width:0;">
      <div style="font-weight:600;font-size:0.9rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:2px;">${nameHtml}</div>
      <div style="font-size:0.71rem;color:var(--text2);">${scEsc(it.group_name)} &middot; ${dateLabel}${it.board_name!=='2026 Social Media'?' &middot; <span style="opacity:0.6;">'+scEsc(it.board_name)+'</span>':''}</div>
    </div>
    <div style="display:flex;gap:4px;align-items:center;flex-shrink:0;">
      <span class="status-pill" style="background:${ptColor}20;color:${ptColor};">${scEsc(it.post_type)}</span>
      ${it.status?`<span class="status-pill" style="background:${stColor}20;color:${stColor};">${scEsc(it.status)}</span>`:''}
    </div>
  </div>`;

  if (it.platforms.length) h += `<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:8px;">${platBadges}</div>`;

  if (it.notes) h += `<div style="font-size:0.74rem;color:var(--muted);margin-bottom:8px;padding:7px 10px;background:var(--bg);border-radius:6px;border-left:2px solid var(--border2);">${scEsc(it.notes)}</div>`;

  // Asset thumb
  if (it.assets&&it.assets.length) {
    it.assets.forEach(a=>{
      if(['.png','.jpg','.jpeg','.gif','.webp'].includes((a.extension||'').toLowerCase())){
        h+=`<div style="margin-bottom:8px;"><img src="/api/social-calendar/asset/${a.id}" style="max-width:160px;max-height:90px;border-radius:7px;border:1px solid var(--border);display:block;" loading="lazy"/></div>`;
      }
    });
  }

  // Caption section
  if (it.platforms.length && it.status!=='Scheduled' && it.status!=='Posted') {
    h += `<div style="border-top:1px solid var(--border);padding-top:10px;margin-top:8px;" onclick="event.stopPropagation()">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer;" onclick="scToggleCaptions('${it.id}',this)">
        <span id="sc-cap-arrow-${it.id}" style="font-size:0.65rem;transition:transform 0.2s;color:var(--muted);">&#9654;</span>
        <span style="font-size:0.76rem;font-weight:600;color:var(--text2);">&#10024; AI Caption Preview</span>
      </div>
      <div id="sc-cap-panel-${it.id}" style="display:none;">
        <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;">`;
    it.platforms.filter(p=>p!=='In-app Feed').forEach(p=>{
      h+=`<button onclick="scQuickGenCaption('${it.id}','${scEsc(p)}')" class="btn" style="font-size:0.7rem;padding:4px 9px;">Generate ${scEsc(p)}</button>`;
    });
    h += `</div><div id="sc-captions-${it.id}"></div></div></div>`;
  }

  // Action buttons
  if (it.has_status_col) {
    h += `<div style="display:flex;gap:5px;margin-top:10px;padding-top:10px;border-top:1px solid var(--border);" onclick="event.stopPropagation()">`;
    if (it.status!=='Scheduled'&&it.status!=='Posted')
      h+=`<button onclick="scMarkScheduled('${it.id}',this)" class="btn" style="font-size:0.72rem;padding:4px 10px;">&#10003; Schedule</button>`;
    if (it.status!=='Posted')
      h+=`<button onclick="scMarkPosted('${it.id}',this)" class="btn" style="font-size:0.72rem;padding:4px 10px;border-color:rgba(74,222,128,0.25);color:var(--green);">&#128228; Mark Posted</button>`;
    h+=`<button onclick="scShowItem('${it.id}')" class="btn" style="font-size:0.72rem;padding:4px 10px;margin-left:auto;">Details &rarr;</button>`;
    h+='</div>';
  }
  h += '</div>';
  return h;
}

// ── Quick caption gen from queue ───────────────────────────
function scBuildDummyCaption(item, platform) {
  const tag = '#iConnections #' + (item.group_name||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,14);
  if (platform==='Twitter') return `${item.name} ${tag} #AltsInvesting`.slice(0,280);
  return `${item.name}${item.notes?'\n\n'+item.notes:''}\n\n${tag} #AlternativeInvestments`;
}

async function scQuickGenCaption(itemId, platform) {
  const btn = event.target;
  const orig = btn.textContent;
  btn.textContent = '⏳ Generating…'; btn.disabled = true;
  const item = scItems.find(i=>i.id===itemId);
  if (!item) { btn.textContent=orig; btn.disabled=false; return; }

  try {
    const res = await fetch('/api/social-calendar/generate-caption', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id:itemId, platforms:[platform], post_type:item.post_type, item_name:item.name, group_name:item.group_name, notes:item.notes||''})
    });
    const data = await res.json();
    if (!scCaptionCache[itemId]) scCaptionCache[itemId]={};
    if (data.captions) Object.assign(scCaptionCache[itemId], data.captions);
    else scCaptionCache[itemId][platform] = scBuildDummyCaption(item, platform);
    scRenderCaptions(itemId, scCaptionCache[itemId]);
  } catch(e) {
    if (!scCaptionCache[itemId]) scCaptionCache[itemId]={};
    scCaptionCache[itemId][platform] = scBuildDummyCaption(item, platform);
    scRenderCaptions(itemId, scCaptionCache[itemId]);
  }
  btn.textContent = '&#10003; ' + platform;
  btn.style.color = 'var(--green)';
  btn.style.borderColor = 'rgba(74,222,128,0.3)';
}

// ── Caption renderer (enhanced) ────────────────────────────
function scRenderCaptions(itemId, captions) {
  const el = document.getElementById('sc-captions-'+itemId);
  if (!el) return;
  let html = '';
  Object.entries(captions).forEach(([platform, caption]) => {
    if (caption && typeof caption==='object' && caption._multi) {
      html += `<div class="sc-caption-block">
        <div class="sc-caption-block-label">${scEsc(platform)} <span style="font-size:0.62rem;background:var(--purple);color:#fff;padding:1px 6px;border-radius:10px;">3 variants</span></div>`;
      ['tweet_with_graphic','reply_cta','text_only_suggestion'].forEach(vk=>{
        const meta = _twitterVariantMeta[vk]||{};
        const vid = 'sc-cap-'+itemId+'-Twitter-'+vk;
        html += `<div style="margin-bottom:10px;border-left:2px solid ${meta.color||'var(--border2)'};padding-left:10px;">
          <div style="font-size:0.67rem;font-weight:700;color:${meta.color||'var(--text)'};margin-bottom:3px;">${meta.label||vk}</div>
          <textarea id="${vid}" class="sc-caption-textarea">${scEsc(caption[vk]||'')}</textarea>
          <div style="display:flex;gap:5px;margin-top:5px;">
            <button onclick="scCopyCap('${vid}')" class="btn" style="font-size:0.67rem;padding:3px 8px;">Copy</button>
          </div>
        </div>`;
      });
      html += '</div>';
    } else {
      const cid = 'sc-cap-'+itemId+'-'+platform.replace(/[^a-zA-Z]/g,'');
      html += `<div class="sc-caption-block">
        <div class="sc-caption-block-label">${scEsc(platform)}</div>
        <textarea id="${cid}" class="sc-caption-textarea" onchange="scCaptionEdited('${itemId}','${scEsc(platform)}',this.value)">${scEsc(caption||'')}</textarea>
        <div style="display:flex;gap:5px;margin-top:5px;">
          <button onclick="scRefineCaptionPrompt('${itemId}','${scEsc(platform)}','${cid}')" class="btn" style="font-size:0.67rem;padding:3px 8px;">&#128260; Refine</button>
          <button onclick="scCopyCap('${cid}')" class="btn" style="font-size:0.67rem;padding:3px 8px;">Copy</button>
        </div>
      </div>`;
    }
  });
  el.innerHTML = html;
}

// ── Enhanced modal ─────────────────────────────────────────
async function scShowItem(itemId) {
  const modal = document.getElementById('sc-modal-overlay');
  const content = document.getElementById('sc-modal-content');
  content.innerHTML = `<div style="padding:70px;text-align:center;">
    <div class="spinner" style="margin:0 auto 14px;width:26px;height:26px;border-width:3px;"></div>
    <div style="color:var(--muted);font-size:0.83rem;">Loading post details…</div>
  </div>`;
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';

  try {
    const res = await fetch('/api/social-calendar/item/'+itemId);
    const item = await res.json();
    if (item.error) { content.innerHTML='<div style="padding:40px;text-align:center;color:var(--muted);">Error loading post.</div>'; return; }

    const ptColor = SC_POST_TYPE_COLORS[item.post_type]||'#555';
    const stColor = SC_STATUS_COLORS[item.status]||'#555';
    const dateLabel = item.date
      ? scParseDate(item.date).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'})
      : 'No date';
    const pLinks = item.platform_links||{};

    let html = `
      <button onclick="scCloseModal()" style="position:absolute;top:14px;right:14px;background:var(--surface3);border:1px solid var(--border2);border-radius:8px;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:1rem;cursor:pointer;color:var(--text2);z-index:10;transition:all 0.14s;" onmouseover="this.style.background='var(--surface2)'" onmouseout="this.style.background='var(--surface3)'">&#10005;</button>

      <div class="sc-modal-header">
        <div style="display:flex;align-items:flex-start;gap:12px;">
          <div style="width:3px;border-radius:3px;align-self:stretch;background:${ptColor};flex-shrink:0;"></div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:1.12rem;font-weight:700;letter-spacing:-0.015em;margin-bottom:3px;">${scEsc(item.name)}</div>
            <div style="font-size:0.76rem;color:var(--text2);">${scEsc(item.group_name)}${item.board_name!=='2026 Social Media'?' &middot; '+scEsc(item.board_name):''}</div>
          </div>
        </div>
        <div style="display:flex;gap:6px;margin-top:14px;flex-wrap:wrap;">
          <span class="status-pill" style="background:${ptColor}20;color:${ptColor};padding:4px 12px;">${scEsc(item.post_type||'No type')}</span>
          ${item.status?`<span class="status-pill" style="background:${stColor}20;color:${stColor};padding:4px 12px;">${scEsc(item.status)}</span>`:''}
          <span class="status-pill" style="background:var(--surface3);color:var(--text2);padding:4px 12px;">&#128197; ${dateLabel}</span>
        </div>
      </div>
      <div class="sc-modal-body">
    `;

    // Platforms + board grid
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px;">';
    if (item.platforms&&item.platforms.length) {
      const pb = item.platforms.map(p=>`<span class="plat-badge">${scEsc(p)}</span>`).join(' ');
      html += `<div class="sc-info-tile"><div class="sc-info-tile-label">Platforms</div><div style="display:flex;flex-wrap:wrap;gap:4px;">${pb}</div></div>`;
    }
    html += `<div class="sc-info-tile"><div class="sc-info-tile-label">Board</div><div style="font-size:0.84rem;">${scEsc(item.board_name||'—')}</div></div>`;
    html += '</div>';

    // Platform links
    const linkablePlats = (item.platforms||[]).filter(p=>p!=='In-app Feed');
    if (linkablePlats.length) {
      html += `<div class="sc-info-tile" style="margin-bottom:18px;"><div class="sc-info-tile-label">Post Links</div><div style="display:flex;flex-direction:column;gap:6px;margin-top:2px;">`;
      linkablePlats.forEach(p=>{
        const lk = p==='YT Full Length'?'YT Full':p==='YT Shorts'?'YT Short':p;
        const url = pLinks[lk]||pLinks[p]||'';
        const inputId = 'sc-link-edit-'+item.id+'-'+p.replace(/[^a-zA-Z]/g,'');
        const suggestId = 'sc-suggest-'+item.id+'-'+p.replace(/[^a-zA-Z]/g,'');
        html += `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span class="plat-badge" style="min-width:86px;justify-content:center;">${scEsc(p)}</span>`;
        if (url==='ig-story') {
          html+=`<span style="font-size:0.77rem;color:var(--pink);">&#128214; Instagram Story</span>
            <button onclick="scEditLink('${item.id}','${scEsc(p)}','${scEsc(item.board_id)}','${inputId}','')" style="background:none;border:none;cursor:pointer;font-size:0.75rem;color:var(--muted);">&#9998;</button>`;
        } else if (url) {
          html+=`<a href="${scEsc(url)}" target="_blank" style="color:var(--purple);font-size:0.77rem;text-decoration:none;border-bottom:1px solid rgba(124,111,255,0.3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:360px;">${scEsc(url)} &#8599;</a>
            <button onclick="scEditLink('${item.id}','${scEsc(p)}','${scEsc(item.board_id)}','${inputId}','${scEsc(url)}')" style="background:none;border:none;cursor:pointer;font-size:0.75rem;color:var(--muted);">&#9998;</button>`;
        } else {
          html+=`<span style="font-size:0.77rem;color:var(--red);">Not posted yet</span>
            <button onclick="scSuggestLinks('${item.id}','${scEsc(p)}','${scEsc(item.board_id)}','${suggestId}')" style="background:none;border:none;cursor:pointer;font-size:0.75rem;color:var(--muted);" title="Find link">&#128269;</button>
            <button onclick="scEditLink('${item.id}','${scEsc(p)}','${scEsc(item.board_id)}','${inputId}','')" style="background:none;border:none;cursor:pointer;font-size:0.75rem;color:var(--muted);" title="Paste link">&#9998;</button>
            <div id="${suggestId}" style="display:none;width:100%;margin-top:4px;"></div>`;
        }
        html+=`<div id="${inputId}" style="display:none;width:100%;margin-top:4px;"></div></div>`;
      });
      html += '</div></div>';
    }

    // Notes
    if (item.notes) {
      html+=`<div class="sc-info-tile" style="margin-bottom:18px;"><div class="sc-info-tile-label">Notes</div><div style="font-size:0.84rem;line-height:1.65;white-space:pre-wrap;">${scEsc(item.notes)}</div></div>`;
    }

    // Assets
    if (item.assets&&item.assets.length) {
      html+=`<div style="margin-bottom:18px;"><div class="sc-info-tile-label" style="margin-bottom:10px;">Attached Files</div>`;
      item.assets.forEach(a=>{
        const isImg = ['.png','.jpg','.jpeg','.gif','.webp'].includes((a.extension||'').toLowerCase());
        if (isImg) {
          html+=`<div style="position:relative;display:inline-block;margin-bottom:8px;border-radius:12px;overflow:hidden;border:1px solid var(--border);">
            <img src="/api/social-calendar/asset/${a.id}" style="max-width:100%;max-height:340px;display:block;" loading="lazy"/>
            <a href="/api/social-calendar/asset/${a.id}?download=1" download="${scEsc(a.name)}" style="position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,0.75);color:#fff;border-radius:7px;padding:5px 12px;font-size:0.71rem;text-decoration:none;">&#11015;&#65039; Download</a>
          </div>`;
        } else {
          html+=`<div style="display:flex;align-items:center;gap:8px;background:var(--surface2);padding:8px 12px;border-radius:8px;border:1px solid var(--border);margin-bottom:4px;font-size:0.81rem;">
            <span>&#128206; ${scEsc(a.name)}</span>
            <a href="/api/social-calendar/asset/${a.id}?download=1" download="${scEsc(a.name)}" style="color:var(--purple);font-size:0.71rem;text-decoration:none;margin-left:auto;">&#11015;&#65039; Download</a>
          </div>`;
        }
      });
      html += '</div>';
    }

    // Caption section in modal
    if (item.platforms&&item.platforms.length&&item.status!=='Posted') {
      html += `<div class="sc-info-tile" style="margin-bottom:18px;">
        <div class="sc-info-tile-label">&#10024; AI Caption Preview</div>
        <div style="display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 12px;">`;
      item.platforms.filter(p=>p!=='In-app Feed').forEach(p=>{
        html+=`<button onclick="scModalGenCaption('${item.id}','${scEsc(p)}',this)" class="btn" style="font-size:0.73rem;">Generate ${scEsc(p)}</button>`;
      });
      html += `</div><div id="sc-modal-captions-${item.id}"></div></div>`;
    }

    // Actions
    html += `<div style="display:flex;gap:7px;flex-wrap:wrap;padding-top:16px;border-top:1px solid var(--border);">`;
    if (item.has_status_col) {
      if (item.status!=='Scheduled'&&item.status!=='Posted')
        html+=`<button onclick="scMarkScheduled('${item.id}',this);scCloseModal();" class="btn btn-primary" style="font-size:0.81rem;">&#10003; Mark as Scheduled</button>`;
      if (item.status!=='Posted')
        html+=`<button onclick="scMarkPosted('${item.id}',this);scCloseModal();" class="btn" style="font-size:0.81rem;border-color:rgba(74,222,128,0.25);color:var(--green);">&#128228; Mark as Posted</button>`;
    }
    html += '</div>';
    html += '</div>';

    content.innerHTML = html;

    // Restore cached captions in modal
    if (scCaptionCache[item.id]) {
      const el = document.getElementById('sc-modal-captions-'+item.id);
      if (el) scRenderModalCaptions(item.id, scCaptionCache[item.id], el);
    }
  } catch(e) {
    content.innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted);">Error loading post details.</div>';
    console.error(e);
  }
}

async function scModalGenCaption(itemId, platform, btn) {
  btn.textContent = '&#9203; Generating…'; btn.disabled = true;
  const item = scItems.find(i=>i.id===itemId);
  if (!item) { btn.textContent = 'Generate '+platform; btn.disabled=false; return; }
  try {
    const res = await fetch('/api/social-calendar/generate-caption',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id:itemId, platforms:[platform], post_type:item.post_type, item_name:item.name, group_name:item.group_name, notes:item.notes||''})
    });
    const data = await res.json();
    if (!scCaptionCache[itemId]) scCaptionCache[itemId]={};
    if (data.captions) Object.assign(scCaptionCache[itemId], data.captions);
    else scCaptionCache[itemId][platform] = scBuildDummyCaption(item, platform);
    const el = document.getElementById('sc-modal-captions-'+itemId);
    if (el) scRenderModalCaptions(itemId, scCaptionCache[itemId], el);
  } catch(e) {
    if (!scCaptionCache[itemId]) scCaptionCache[itemId]={};
    scCaptionCache[itemId][platform] = scBuildDummyCaption(item, platform);
    const el = document.getElementById('sc-modal-captions-'+itemId);
    if (el) scRenderModalCaptions(itemId, scCaptionCache[itemId], el);
  }
  btn.textContent = '&#10003; ' + platform;
  btn.style.color = 'var(--green)';
  btn.style.borderColor = 'rgba(74,222,128,0.3)';
  btn.disabled = false;
}

function scRenderModalCaptions(itemId, captions, container) {
  let html = '';
  Object.entries(captions).forEach(([platform, caption]) => {
    const id = 'sc-modal-cap-'+itemId+'-'+platform.replace(/[^a-zA-Z]/g,'');
    const capText = caption && typeof caption==='object' ? JSON.stringify(caption,null,2) : (caption||'');
    html += `<div class="sc-caption-block">
      <div class="sc-caption-block-label">${scEsc(platform)}</div>
      <textarea id="${id}" class="sc-caption-textarea">${scEsc(capText)}</textarea>
      <div style="display:flex;gap:5px;margin-top:5px;">
        <button onclick="scCopyCap('${id}')" class="btn" style="font-size:0.71rem;padding:3px 9px;">Copy</button>
      </div>
    </div>`;
  });
  container.innerHTML = html;
}

// ── Status update with toast ───────────────────────────────
async function scUpdateStatus(itemId, label, btn) {
  if (!confirm('Mark this post as "'+label+'"?')) return;
  const item = scItems.find(i=>i.id===itemId);
  if (btn) { btn.disabled=true; btn.textContent='Updating…'; }
  try {
    const res = await fetch('/api/social-calendar/update-status',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id:itemId, status_label:label, board_id:item?item.board_id:''})
    });
    const data = await res.json();
    if (data.success) {
      scToast('Status updated → '+label, 'success');
      await scLoadData(true);
    } else {
      scToast('Error: '+(data.error||'Unknown'), 'error');
      if (btn) { btn.disabled=false; btn.textContent=label; }
    }
  } catch(e) {
    scToast('Error updating status', 'error');
    if (btn) { btn.disabled=false; btn.textContent=label; }
  }
}

// ── Animated close modal ────────────────────────────────────
function scCloseModal() {
  const overlay = document.getElementById('sc-modal-overlay');
  const content = document.getElementById('sc-modal-content');
  content.style.transition = 'transform 0.17s ease, opacity 0.17s ease';
  content.style.transform = 'scale(0.95) translateY(8px)';
  content.style.opacity = '0';
  setTimeout(() => {
    overlay.style.display = 'none';
    content.style.cssText = '';
    document.body.style.overflow = '';
  }, 170);
}

// ── Refresh button animation ────────────────────────────────
const _origLoadData = scLoadData;
async function scLoadData(force) {
  const btn = document.getElementById('sc-refresh-btn');
  if (btn && force) {
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 0.6s linear infinite"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> Refreshing…`;
    btn.disabled = true;
  }
  await _origLoadData(force);
  if (btn) {
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> Refresh`;
    btn.disabled = false;
  }
}

// ── Escape key ─────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const o = document.getElementById('sc-modal-overlay');
    if (o && o.style.display !== 'none') scCloseModal();
  }
});

// Re-define scInit so it uses our patched scLoadData
function scInit() {
  if (scLoaded) {
    scApplyFilters();
    scStartSyncPolling();
    return;
  }
  scLoaded = true;
  scLoadData(false);
  scStartSyncPolling();
}

console.log('%c Social Calendar Enhanced UI v2 ✨ ', 'background:#7c6fff;color:#fff;border-radius:4px;padding:2px 8px;font-weight:700;');
"""

HOST_JS = """
function switchMainTab(tab) {
  document.getElementById('socialcal-view').style.display = (tab === 'socialcal') ? '' : 'none';
  if (tab === 'socialcal' && typeof scInit === 'function') scInit();
}
window.addEventListener('DOMContentLoaded', function() {
  switchMainTab('socialcal');
  // Fallback: if data didn't load, fetch it directly
  setTimeout(function() {
    if (typeof scItems !== 'undefined' && scItems.length === 0) {
      console.log('[SC] Fallback data load triggered');
      fetch('/api/social-calendar/items')
        .then(function(r) { return r.json(); })
        .then(function(data) {
          scItems = data.items || [];
          scAllGroups = data.all_groups || [];
          if (typeof scPopulateFilters === 'function') scPopulateFilters();
          if (typeof scApplyFilters === 'function') scApplyFilters();
          console.log('[SC] Fallback loaded ' + scItems.length + ' items');
        })
        .catch(function(e) { console.error('[SC] Fallback load error:', e); });
    }
  }, 1200);
});
"""

BANNER = (
    '<div class="demo-banner">'
    '&#127912; <b>Demo mode</b> — 22 in-memory posts across 9 groups. '
    'Drag posts on calendar to reschedule. Click cards to open modal. '
    'Status toggles update live. Restart to reset.'
    '</div>'
) if USE_DUMMY else ''


@app.route("/")
def index():
    return (
        "<!doctype html><html lang='en'><head>"
        "<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>iConnections Social Calendar</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<style>" + BASE_CSS + "</style>"
        "</head><body><main>"
        + BANNER
        + ENHANCED_HTML
        + "</main>"
        "<script>" + HOST_JS + "</script>"
        "<script>" + ENHANCED_JS + "</script>"
        "</body></html>"
    )


if __name__ == "__main__":
    mode = "DUMMY" if USE_DUMMY else "LIVE (Monday.com)"
    port = int(os.environ.get("PORT", 8989))
    host = "0.0.0.0"
    print("┌──────────────────────────────────────────────────────────")
    print(f"│  iConnections Social Calendar — {mode}")
    print(f"│  ✨ Enhanced UI — drag, search, captions, animations")
    print(f"│  → http://{host}:{port}/")
    print("└──────────────────────────────────────────────────────────")
    app.run(host=host, port=port, debug=False)
