"""Fetch app details from a Google Play link and translate them to the dataset's format.

The dataset uses the old Play Store permission labels ("Hardware controls : take pictures and videos (D)").
Current Play Store labels are matched to those columns with the rules below; anything without a counterpart
in the dataset is reported back as unmapped instead of being guessed.
"""
import re
from urllib.parse import parse_qs, urlparse

PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")

# Play Store genreId -> (category key, dataset genre)
GENRE_ID_MAP = {
    "EDUCATION": ("education", "Education"), "BOOKS_AND_REFERENCE": ("education", "Books & Reference"),
    "TOOLS": ("productivity_tools", "Tools"), "BUSINESS": ("productivity_tools", "Business"),
    "FINANCE": ("productivity_tools", "Finance"), "PRODUCTIVITY": ("productivity_tools", "Productivity"),
    "LIBRARIES_AND_DEMO": ("productivity_tools", "Libraries & Demo"),
    "ENTERTAINMENT": ("media_entertainment", "Entertainment"), "VIDEO_PLAYERS": ("media_entertainment", "Media & Video"),
    "MUSIC_AND_AUDIO": ("media_entertainment", "Music & Audio"), "COMICS": ("media_entertainment", "Comics"),
    "PHOTOGRAPHY": ("media_entertainment", "Photography"),
    "SOCIAL": ("social_communication", "Social"), "COMMUNICATION": ("social_communication", "Communication"),
    "NEWS_AND_MAGAZINES": ("social_communication", "News & Magazines"),
    "TRAVEL_AND_LOCAL": ("lifestyle_health", "Travel & Local"), "PERSONALIZATION": ("lifestyle_health", "Personalization"),
    "LIFESTYLE": ("lifestyle_health", "Lifestyle"), "HEALTH_AND_FITNESS": ("lifestyle_health", "Health & Fitness"),
    "SPORTS": ("lifestyle_health", "Sports"), "MAPS_AND_NAVIGATION": ("lifestyle_health", "Transportation"),
    "SHOPPING": ("lifestyle_health", "Shopping"), "MEDICAL": ("lifestyle_health", "Medical"),
    "WEATHER": ("lifestyle_health", "Weather"),
    "GAME_ACTION": ("games", "Arcade & Action"), "GAME_ARCADE": ("games", "Arcade & Action"),
    "GAME_ADVENTURE": ("games", "Arcade & Action"), "GAME_PUZZLE": ("games", "Brain & Puzzle"),
    "GAME_BOARD": ("games", "Brain & Puzzle"), "GAME_TRIVIA": ("games", "Brain & Puzzle"),
    "GAME_WORD": ("games", "Brain & Puzzle"), "GAME_EDUCATIONAL": ("games", "Brain & Puzzle"),
    "GAME_CARD": ("games", "Cards & Casino"), "GAME_CASINO": ("games", "Cards & Casino"),
    "GAME_RACING": ("games", "Racing"), "GAME_SPORTS": ("games", "Sports Games"),
    "GAME_CASUAL": ("games", "Casual"), "GAME_SIMULATION": ("games", "Casual"), "GAME_STRATEGY": ("games", "Casual"),
    "GAME_ROLE_PLAYING": ("games", "Casual"), "GAME_MUSIC": ("games", "Casual"),
}

# Current Play Store permission label (regex, lower case) -> dataset column
PERMISSION_RULES = [
    (r"take pictures and videos", "Hardware controls : take pictures and videos (D)"),
    (r"record audio", "Hardware controls : record audio (D)"),
    (r"precise location", "Your location : fine (GPS) location (D)"),
    (r"approximate location", "Your location : coarse (network-based) location (D)"),
    (r"read your contacts", "Your personal information : read contact data (D)"),
    (r"modify your contacts", "Your personal information : write contact data (D)"),
    (r"find accounts on the device", "Your accounts : discover known accounts (S)"),
    (r"add or remove accounts", "Your accounts : manage the accounts list (D)"),
    (r"use accounts on the device", "Your accounts : use the authentication credentials of an account (D)"),
    (r"read calendar events", "Your personal information : read calendar events (D)"),
    (r"add or modify calendar events", "Your personal information : add or modify calendar events and send email to guests (D)"),
    (r"receive text messages \(sms\)", "Your messages : receive SMS (D)"),
    (r"receive text messages \(mms\)", "Your messages : receive MMS (D)"),
    (r"read your text messages", "Your messages : read SMS or MMS (D)"),
    (r"edit your text messages", "Your messages : edit SMS or MMS (D)"),
    (r"send sms messages", "Services that cost you money : send SMS messages (D)"),
    (r"directly call phone numbers", "Services that cost you money : directly call phone numbers (D)"),
    (r"read phone status and identity", "Phone calls : read phone state and identity (D)"),
    (r"reroute outgoing calls", "Phone calls : intercept outgoing calls (D)"),
    (r"modify phone state", "Phone calls : modify phone state (S)"),
    (r"full network access", "Network communication : full Internet access (D)"),
    (r"receive data from internet", "Network communication : receive data from Internet (S)"),
    (r"view network connections", "Network communication : view network state (S)"),
    (r"view wi-?fi connections", "Network communication : view Wi-Fi state (S)"),
    (r"connect and disconnect from wi-?fi", "System tools : change Wi-Fi state (D)"),
    (r"change network connectivity", "System tools : change network connectivity (D)"),
    (r"pair with bluetooth devices", "Network communication : create Bluetooth connections (D)"),
    (r"access bluetooth settings", "System tools : bluetooth administration (D)"),
    (r"control near field communication", "Network communication : control Near Field Communication (D)"),
    (r"download files without notification", "Network communication : download files without notification (S)"),
    (r"(modify or delete|read) the contents of your (usb|shared) storage",
     "Storage : modify/delete USB storage contents modify/delete SD card contents (D)"),
    (r"prevent (device|phone|tablet) from sleeping", "System tools : prevent device from sleeping (D)"),
    (r"run at startup", "System tools : automatically start at boot (S)"),
    (r"control vibration", "Hardware controls : control vibrator (S)"),
    (r"control flashlight", "Hardware controls : control flashlight (S)"),
    (r"change your audio settings", "Hardware controls : change your audio settings (D)"),
    (r"draw over other apps|display system-level alerts", "System tools : display system-level alerts (D)"),
    (r"disable your screen lock", "System tools : disable keylock (D)"),
    (r"expand/collapse status bar", "System tools : expand/collapse status bar (S)"),
    (r"^set wallpaper$", "System tools : set wallpaper (S)"),
    (r"read sync settings", "System tools : read sync settings (S)"),
    (r"toggle sync on and off", "System tools : write sync settings (D)"),
    (r"read sync statistics", "System tools : read sync statistics (S)"),
    (r"retrieve running apps", "System tools : retrieve running applications (D)"),
    (r"close other apps", "System tools : kill background processes (S)"),
    (r"reorder running apps", "System tools : reorder running applications (D)"),
    (r"modify system settings", "System tools : modify global system settings (D)"),
    (r"set an alarm", "Your personal information : set alarm in alarm clock (S)"),
    (r"read google service configuration", "Your accounts : read Google service configuration (S)"),
    (r"allow wi-?fi multicast reception", "System tools : allow Wi-Fi Multicast reception (D)"),
    (r"set time zone", "System tools : set time zone (D)"),
    (r"read your web bookmarks and history", "Your personal information : read Browser's history and bookmarks (D)"),
    (r"write web bookmarks and history", "Your personal information : write Browser's history and bookmarks (D)"),
    (r"read sensitive log data", "Your personal information : read sensitive log data (D)"),
    (r"measure app storage space", "System tools : measure application storage space (S)"),
    (r"make app always run", "System tools : make application always run (D)"),
    (r"send sticky broadcast", "System tools : send sticky broadcast (S)"),
    (r"update component usage statistics", "Default : update component usage statistics (S)"),
    (r"create accounts and set passwords", "Your accounts : act as an account authenticator (D)"),
]
_COMPILED = [(re.compile(p), col) for p, col in PERMISSION_RULES]


class PlayStoreError(Exception):
    pass


# Reputation: the 2012-era training data has no app with more than ~1.9M ratings, so the classifier is unreliable
# for today's widely used apps. Store signals that the dataset does not contain give a trust level in [0, MAX_TRUST];
# model.CategoryModel.analyze shrinks the classifier risk towards a low value in proportion to it.
MAX_TRUST = 0.85


def reputation(details):
    import math
    from datetime import datetime

    def scale(x, lo, hi):
        return min(max((x - lo) / (hi - lo), 0.0), 1.0)

    installs = float(details.get("minInstalls") or 0)
    ratings = float(details.get("ratings") or 0)
    score = float(details.get("score") or 0)
    try:
        years = (datetime.now() - datetime.strptime(details.get("released") or "", "%b %d, %Y")).days / 365.25
    except ValueError:
        years = 0.0
    parts = {
        "installs": scale(math.log10(installs + 1), 4, 8),      # 10k -> 0, 100M -> 1
        "ratings": scale(math.log10(ratings + 1), 3, 7),        # 1k -> 0, 10M -> 1
        "rating": scale(score, 3.0, 4.5) if ratings else 0.0,
        "age": scale(years, 0, 5),
        "privacy_policy": 1.0 if details.get("privacyPolicy") else 0.0,
        "website": 1.0 if details.get("developerWebsite") else 0.0,
    }
    weights = {"installs": 0.35, "ratings": 0.25, "rating": 0.20, "age": 0.10, "privacy_policy": 0.05, "website": 0.05}
    trust = MAX_TRUST * sum(weights[k] * parts[k] for k in weights)
    return {"trust": round(trust, 4), "signals": {k: round(v, 3) for k, v in parts.items()}}


def extract_package_id(link):
    """Accept a Play Store URL or a bare package id; return the package id."""
    link = (link or "").strip()
    if PACKAGE_RE.match(link):
        return link
    parsed = urlparse(link if "://" in link else "https://" + link)
    if parsed.netloc not in ("play.google.com", "www.play.google.com", "market.android.com"):
        raise PlayStoreError("This is not a Google Play link. Paste a link like "
                             "https://play.google.com/store/apps/details?id=com.example.app")
    app_id = (parse_qs(parsed.query).get("id") or [""])[0]
    if not PACKAGE_RE.match(app_id):
        raise PlayStoreError("The link does not contain a valid app id (the ?id=... part).")
    return app_id


def map_permissions(groups):
    """Play Store permission dict {group: [labels]} -> (dataset columns, unmapped labels)."""
    mapped, unmapped = [], []
    for labels in (groups or {}).values():
        for label in labels:
            text = label.strip().lower()
            hits = [col for rx, col in _COMPILED if rx.search(text)]
            if hits:
                mapped.extend(h for h in hits if h not in mapped)
            elif label not in unmapped:
                unmapped.append(label)
    return mapped, unmapped


def fetch(link, lang="en", country="us"):
    app_id = extract_package_id(link)
    try:
        from google_play_scraper import app as gp_app, permissions as gp_permissions
        from google_play_scraper.exceptions import NotFoundError
    except ImportError as e:  # pragma: no cover
        raise PlayStoreError("google-play-scraper is not installed on the server.") from e
    try:
        details = gp_app(app_id, lang=lang, country=country)
    except NotFoundError:
        raise PlayStoreError(f"No app with id '{app_id}' was found on Google Play.")
    except Exception as e:
        raise PlayStoreError(f"Google Play could not be reached ({type(e).__name__}). Try again or enter details manually.")
    try:
        perm_groups = gp_permissions(app_id, lang=lang, country=country) or {}
        perm_error = None
    except Exception as e:
        perm_groups, perm_error = {}, f"Permissions could not be read from Google Play ({type(e).__name__})."

    genre_id = (details.get("genreId") or "").upper()
    category, genre = GENRE_ID_MAP.get(genre_id, (None, None))
    mapped, unmapped = map_permissions(perm_groups)
    price = details.get("price") or 0.0
    return {
        "app": {
            "app_name": details.get("title") or app_id, "package": app_id,
            "description": details.get("description") or "", "genre": genre, "category": category,
            "rating": float(details.get("score") or 0.0), "num_ratings": float(details.get("ratings") or 0.0),
            "price": float(price) if isinstance(price, (int, float)) else 0.0,
            "related_apps": "", "permissions": mapped, "permission_groups": [],
        },
        "store": {
            "title": details.get("title"), "developer": details.get("developer"), "icon": details.get("icon"),
            "genre": details.get("genre"), "genre_id": genre_id, "installs": details.get("installs"),
            "url": f"https://play.google.com/store/apps/details?id={app_id}",
            "play_permissions": perm_groups, "unmapped_permissions": unmapped, "permission_error": perm_error,
            "category_supported": category is not None,
        },
        "reputation": reputation(details),
    }
