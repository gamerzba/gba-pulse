"""Runtime configuration for G.ba Pulse.

Keep site URLs and confirmed Gamerz.ba response mappings in one place.
"""
from __future__ import annotations

APP_NAME = "G.ba Pulse"
APP_ID = "GbaPulse"
FORUM_URL = "https://www.gamerz.ba/"
RSS_URL = "https://www.gamerz.ba/rss"
LOGO_URL = "https://www.gamerz.ba/assets/v5/images/logo-mark-mRsiQoL.svg"
MESSAGES_URL = "https://www.gamerz.ba/api/poruke/broj/"
POINTS_URL = "https://www.gamerz.ba/api/bodovi/promjena/"

DEFAULT_REFRESH_SECONDS = 60
ALLOWED_REFRESH_SECONDS = (30, 60, 300)
MAX_FEED_ITEMS = 5
MAX_RESPONSE_BYTES = 120_000

# User-specified colors, with a few neutrals for readable contrast.
COLORS = {
    "background": "#060911",
    "surface": "#0B101B",
    "surface_raised": "#101725",
    "surface_hover": "#171F2E",
    "border": "#202838",
    "text": "#E9EDF5",
    "muted": "#8E98AA",
    "muted_2": "#626D81",
    "accent": "#FB9524",
    "accent_soft": "#3C2817",
    "accent_2": "#8CBF2B",
    "danger": "#E06B69",
    "white": "#FFFFFF",
}
