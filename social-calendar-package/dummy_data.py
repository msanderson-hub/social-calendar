"""
Dummy in-memory dataset that mimics what `social_calendar.parse_item()` returns
after pulling from Monday.com. Used by `dummy_patch.py` to drive the Social
Calendar tab without ever calling Monday.

The data shape MUST match parse_item() exactly. Fields:
  id            : str        — Monday item id (string; we just use "d-001" etc.)
  name          : str        — post title
  board_id      : str        — "8806769351" (2026) or "8158522933" (2025)
  board_name    : str        — "2026 Social Media" / "2025 Social Media"
  group_id      : str        — Monday group id (cosmetic for the demo)
  group_name    : str        — group label shown in the Filter Group dropdown
  date          : str        — "YYYY-MM-DD"
  status        : str        — "" | "Working on it" | "Scheduled" | "For Scheduling" | "Posted" | "Need Content"
  status_color  : str        — hex color for the status pill
  social_link   : str        — legacy LinkedIn URL (back-compat)
  platform_links: dict       — { "LinkedIn": url, "Instagram": url, ... }
  post_type     : str        — "Speaker" | "Panel" | "Milestones" | "Video" | ...
  post_type_color: str       — hex color
  platforms     : list[str]  — subset of ["LinkedIn","Instagram","Twitter","TikTok","YT Full Length","YT Shorts","In-App Feed"]
  notes         : str        — free-text notes
  files         : list       — Monday file column metadata (we leave [] for dummy)
  assets        : list       — [{id, name, public_url, extension}, ...]
  has_status_col: bool       — True for both demo boards

Use this as the source of truth for what shape Claude needs to mimic if it
swaps in a different backend later.
"""

from datetime import date, timedelta

# ─── Color palettes (must match social_calendar.py) ───────────────────────────
STATUS_COLORS = {
    "Working on it":  "#fdab3d",
    "Posted":         "#00c875",
    "Need Content":   "#df2f4a",
    "Scheduled":      "#579bfc",
    "For Scheduling": "#faa1f1",
}
POST_TYPE_COLORS = {
    "Speaker":              "#4eccc6",
    "Panel":                "#00c875",
    "Milestones":           "#579bfc",
    "Video":                "#ff7575",
    "Sponsor":              "#74afcc",
    "Partner Event":        "#175a63",
    "Networking Event":     "#ff5ac4",
    "Coffee & Connections": "#757575",
    "Podcast":              "#037f4c",
    "Press Release":        "#ffadad",
    "Report":               "#e484bd",
    "Product Launch":       "#784bd1",
    "Trending Content":     "#ff6d3b",
    "Holiday":              "#7f5347",
    "Announcement":         "#333333",
    "Blog Post":            "#216edf",
    "Testimonial":          "#bda8f9",
    "Meetups":              "#bca58a",
    "Case Study":           "#a9bee8",
    "Media":                "#7f5347",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
TODAY = date.today()

def _day(offset):
    """Date string N days from today."""
    return (TODAY + timedelta(days=offset)).isoformat()

def _make(idx, name, group_name, post_type, platforms, status="",
          date_offset=0, notes="", links=None, with_asset=False,
          board_year="2026"):
    """Helper to construct one parsed-item dict."""
    board_id = "8806769351" if board_year == "2026" else "8158522933"
    board_name = "2026 Social Media" if board_year == "2026" else "2025 Social Media"
    group_id = "group_" + group_name.lower().replace(" ", "_").replace("'", "")
    pl = dict(links or {})
    # legacy social_link mirrors the LinkedIn URL when present
    social_link = pl.get("LinkedIn", "")

    assets = []
    if with_asset:
        # Pretend the asset proxy will resolve later; for the demo we point
        # at a public placeholder so the modal preview has something to show.
        assets.append({
            "id":         "asset_" + str(idx),
            "name":       (name[:32] + ".png").lower().replace(" ", "_"),
            "public_url": "https://placehold.co/1200x675/10102a/7c6fff?text="
                          + name.replace(" ", "+")[:40],
            "extension":  "png",
        })

    return {
        "id":              "d-" + str(idx).zfill(3),
        "name":            name,
        "board_id":        board_id,
        "board_name":      board_name,
        "group_id":        group_id,
        "group_name":      group_name,
        "date":            _day(date_offset),
        "status":          status,
        "status_color":    STATUS_COLORS.get(status, "#555"),
        "social_link":     social_link,
        "platform_links":  pl,
        "post_type":       post_type,
        "post_type_color": POST_TYPE_COLORS.get(post_type, "#555"),
        "platforms":       platforms,
        "notes":           notes,
        "files":           [],
        "assets":          assets,
        "has_status_col":  True,
    }


# ─── The dummy dataset ───────────────────────────────────────────────────────
# A realistic mix: events spanning past + future, varied platforms, every
# status represented, some with assets, some with already-posted URLs, and
# notes that mention real iC marketing details so Claude has rich text to riff on.

ITEMS = [
    # ── GAMI26 — Global Alts Miami 2026 ────────────────────────────────────
    _make(1, "Diplo headlines Tuesday night — drone show announcement",
          "Global Alts Miami 2026", "Networking Event",
          ["LinkedIn", "Instagram", "Twitter"],
          status="Posted", date_offset=-14,
          notes="Tag @MFA on LI, @mfa_alts on IG, @MFAupdates on X. Use #GAMI26 #iConnections.",
          links={
              "LinkedIn":  "https://www.linkedin.com/posts/iconnections-llc_gami26-activity-123",
              "Instagram": "https://www.instagram.com/p/CxYZdiplo123/",
              "Twitter":   "https://twitter.com/iconnections_io/status/1745001",
          },
          with_asset=True),
    _make(2, "GAMI26 — Speaker spotlight: Ray Dalio",
          "Global Alts Miami 2026", "Speaker",
          ["LinkedIn", "Instagram"],
          status="Scheduled", date_offset=2,
          notes="Headshot card, fireside chat angle. Caption max 5 hashtags, #iConnections first.",
          with_asset=True),
    _make(3, "GAMI26 — Panel: Allocator outlook 2026",
          "Global Alts Miami 2026", "Panel",
          ["LinkedIn", "Instagram", "Twitter", "YT Shorts"],
          status="For Scheduling", date_offset=5,
          notes="Confirmed speakers: head of alts at Yale, CIO at CalPERS, MD at GIC.",
          with_asset=True),
    _make(4, "GAMI26 — Countdown: 30 days out",
          "Global Alts Miami 2026", "Milestones",
          ["LinkedIn", "Instagram", "Twitter"],
          status="Working on it", date_offset=7,
          notes="Stat card style. Highlight 1,800+ allocators, 4,500+ meetings."),
    _make(5, "GAMI26 — Sponsorship spotlight: Cabana partners",
          "Global Alts Miami 2026", "Sponsor",
          ["LinkedIn", "Twitter"],
          status="Need Content", date_offset=10,
          notes="Need final sponsor logos from Carol. Cabana inquiries closed at 12 sold."),
    _make(6, "GAMI26 — Tuesday flight schedule reminder",
          "Global Alts Miami 2026", "Milestones",
          ["LinkedIn", "Instagram"],
          status="Scheduled", date_offset=12,
          with_asset=True),

    # ── GANY26 — Global Alts New York 2026 ─────────────────────────────────
    _make(7, "GANY26 — Save the date: Fall 2026",
          "Global Alts New York 2026", "Announcement",
          ["LinkedIn", "Twitter", "Instagram"],
          status="Posted", date_offset=-30,
          notes="Cipriani 42nd. Tag every speaker confirmed so far.",
          links={
              "LinkedIn":  "https://www.linkedin.com/posts/iconnections-llc_gany26-savethe-date",
              "Twitter":   "https://twitter.com/iconnections_io/status/1742999",
              "Instagram": "https://www.instagram.com/p/CxGANY26std/",
          },
          with_asset=True),
    _make(8, "GANY26 — Speaker reveal: Stanley Druckenmiller",
          "Global Alts New York 2026", "Speaker",
          ["LinkedIn", "Instagram"],
          status="Scheduled", date_offset=20,
          notes="Big-name keynote reveal. Use headshot template, NOT panel template.",
          with_asset=True),
    _make(9, "GANY26 — Past attendee testimonial: Bridgewater MD",
          "Global Alts New York 2026", "Testimonial",
          ["LinkedIn", "Instagram"],
          status="Working on it", date_offset=25,
          notes="Quote pulled from 2025 post-event survey. Confirm legal approved the name.",
          with_asset=True),

    # ── F4C26 — Funds 4 Food 2026 ──────────────────────────────────────────
    _make(10, "F4C26 — 6 years of giving: $3.2M raised milestone",
           "Funds 4 Food 2026", "Milestones",
           ["LinkedIn", "Instagram", "Twitter", "YT Full Length"],
           status="Posted", date_offset=-7,
           notes="Throwback compilation video. CTA: donate at funds4food.com.",
           links={
               "LinkedIn":     "https://www.linkedin.com/posts/iconnections-llc_f4c26-milestone",
               "Instagram":    "https://www.instagram.com/p/CxF4C6years/",
               "Twitter":      "https://twitter.com/iconnections_io/status/1744501",
               "YT Full Length":"https://www.youtube.com/watch?v=f4cYearsVid",
           },
           with_asset=True),
    _make(11, "F4C26 — Auction items teaser",
           "Funds 4 Food 2026", "Networking Event",
           ["LinkedIn", "Instagram"],
           status="For Scheduling", date_offset=4,
           notes="Tease 3 of the headliner items: Yankees suite, NBA finals, Patek."),

    # ── Coffee & Connections (recurring) ───────────────────────────────────
    _make(12, "Coffee & Connections — NYC, Tribeca location",
           "Coffee & Connections", "Coffee & Connections",
           ["LinkedIn", "Instagram"],
           status="Scheduled", date_offset=1,
           notes="Hosted by Shelby. Sign-up form attached in description.",
           with_asset=True),
    _make(13, "Coffee & Connections — Chicago debut",
           "Coffee & Connections", "Coffee & Connections",
           ["LinkedIn"],
           status="Working on it", date_offset=14,
           notes="First Chicago C&C. Partner with local family office network."),

    # ── Platform / Product ─────────────────────────────────────────────────
    _make(14, "Platform feature: AI Meeting Match v2",
           "Platform & Product", "Product Launch",
           ["LinkedIn", "Instagram", "Twitter", "YT Full Length"],
           status="Scheduled", date_offset=6,
           notes="No em-dashes. Tagline: 'Better matches, fewer no-shows.'",
           with_asset=True),
    _make(15, "Case study: $4B emerging manager scaled via iC",
           "Platform & Product", "Case Study",
           ["LinkedIn", "Twitter"],
           status="Need Content", date_offset=18,
           notes="Awaiting final approval from manager. Anonymize fund name."),
    _make(16, "Product launch teaser — Roadshow Mode",
           "Platform & Product", "Product Launch",
           ["LinkedIn", "Instagram"],
           status="For Scheduling", date_offset=22,
           notes="Show short demo gif. Drives to platform page."),

    # ── Media / Podcast / Content ──────────────────────────────────────────
    _make(17, "Podcast: Ron Biscardi on Bloomberg Wealth",
           "Media & Podcasts", "Podcast",
           ["LinkedIn", "Twitter", "YT Full Length"],
           status="Posted", date_offset=-3,
           notes="Cross-post Bloomberg's clip. 90-sec teaser for YT.",
           links={
               "LinkedIn":      "https://www.linkedin.com/posts/iconnections-llc_bloomberg-ron",
               "Twitter":       "https://twitter.com/iconnections_io/status/1744988",
               "YT Full Length":"https://www.youtube.com/watch?v=ronBloomberg",
           },
           with_asset=True),
    _make(18, "Allocator Insider — monthly LP roundup",
           "Media & Podcasts", "Blog Post",
           ["LinkedIn"],
           status="Scheduled", date_offset=8,
           notes="Drives to blog. Includes 3 LP quotes anonymized."),
    _make(19, "TikTok trend: 'POV: you're at an alts conference'",
           "Media & Podcasts", "Trending Content",
           ["TikTok", "Instagram"],
           status="Working on it", date_offset=3,
           notes="Riff on a current trending audio. Approved by Molly first.",
           with_asset=True),

    # ── Holiday / Lighter content ──────────────────────────────────────────
    _make(20, "Memorial Day — honor & remember",
           "Holidays", "Holiday",
           ["LinkedIn", "Instagram", "Twitter"],
           status="Scheduled", date_offset=11,
           notes="Tasteful. No event promo overlay. US flag motif.",
           with_asset=True),

    # ── A couple historical 2025 items to show board mixing ────────────────
    _make(21, "GAMI25 — Recap reel (15-sec)",
           "Global Alts Miami 2025", "Video",
           ["LinkedIn", "Instagram", "YT Shorts", "TikTok"],
           status="Posted", date_offset=-180,
           board_year="2025",
           notes="Throwback recap. Drives to GAMI26 RSVP.",
           links={
               "LinkedIn":  "https://www.linkedin.com/posts/iconnections-llc_gami25-recap",
               "Instagram": "https://www.instagram.com/p/CxGAMI25rec/",
               "YT Shorts": "https://www.youtube.com/shorts/gami25recap",
               "TikTok":    "https://www.tiktok.com/@iconnections.io/video/gami25recap",
           },
           with_asset=True),
    _make(22, "GAAS25 — Asia summit closing thank-you",
           "Global Alts Asia 2025", "Announcement",
           ["LinkedIn"],
           status="Posted", date_offset=-150,
           board_year="2025",
           links={"LinkedIn": "https://www.linkedin.com/posts/iconnections-llc_gaas25-thanks"}),
]


# ─── Group list — what populates the Filter Group dropdown ────────────────────
def list_groups():
    """De-duplicated group list across both boards. Same shape as
    social_calendar.get_board_groups()."""
    seen, out = set(), []
    for it in ITEMS:
        if it["group_name"] in seen:
            continue
        seen.add(it["group_name"])
        out.append({
            "id":    it["group_id"],
            "title": it["group_name"],
            "board": it["board_name"],
        })
    return out
