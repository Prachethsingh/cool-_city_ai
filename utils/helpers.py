"""
utils/helpers.py – Shared utility functions for CoolCity AI agents.
"""

import time
import json
import math
import requests
import datetime
from typing import Optional, Dict, Any, Tuple
from functools import wraps

# ─── Simple in-memory cache ────────────────────────────────────────────────────
_cache: Dict[str, Tuple[Any, float]] = {}

def cached(ttl_seconds: int = 1800):
    """Decorator: caches return value of a function for ttl_seconds."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{kwargs}"
            if key in _cache:
                val, ts = _cache[key]
                if time.time() - ts < ttl_seconds:
                    return val
            result = fn(*args, **kwargs)
            _cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator


# ─── Geocoding ─────────────────────────────────────────────────────────────────
@cached(ttl_seconds=86400)
def geocode_city(city: str, country: str = "India") -> Optional[Dict[str, float]]:
    """
    Returns {"lat": float, "lon": float} for a city using Open-Meteo geocoding.
    Falls back to Nominatim (OSM).
    """
    # Try Open-Meteo geocoding first
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        resp = requests.get(url, params={"name": city, "count": 1, "language": "en"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            r = data["results"][0]
            return {"lat": r["latitude"], "lon": r["longitude"], "name": r["name"], "country": r.get("country", country)}
    except Exception:
        pass

    # Fallback: Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        resp = requests.get(
            url,
            params={"q": f"{city}, {country}", "format": "json", "limit": 1},
            headers={"User-Agent": "CoolCityAI/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]), "name": city, "country": country}
    except Exception:
        pass

    # Hardcoded fallback for common Indian cities
    KNOWN_CITIES = {
        "bengaluru": {"lat": 12.9716, "lon": 77.5946},
        "bangalore": {"lat": 12.9716, "lon": 77.5946},
        "mumbai":    {"lat": 19.0760, "lon": 72.8777},
        "delhi":     {"lat": 28.6139, "lon": 77.2090},
        "chennai":   {"lat": 13.0827, "lon": 80.2707},
        "hyderabad": {"lat": 17.3850, "lon": 78.4867},
        "kolkata":   {"lat": 22.5726, "lon": 88.3639},
        "pune":      {"lat": 18.5204, "lon": 73.8567},
        "ahmedabad": {"lat": 23.0225, "lon": 72.5714},
        "jaipur":    {"lat": 26.9124, "lon": 75.7873},
    }
    key = city.lower().strip()
    if key in KNOWN_CITIES:
        c = KNOWN_CITIES[key]
        return {"lat": c["lat"], "lon": c["lon"], "name": city, "country": country}

    return None


# ─── Heat index calculation (Steadman formula) ────────────────────────────────
def heat_index(temp_c: float, humidity_pct: float) -> float:
    """
    Returns apparent ('feels like') temperature in C.
    Uses the Rothfusz regression (works well above 27 C).
    """
    T = temp_c * 9 / 5 + 32   # convert to °F
    R = humidity_pct
    if T < 80:
        hi_f = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + R * 0.094)
    else:
        hi_f = (
            -42.379
            + 2.04901523 * T
            + 10.14333127 * R
            - 0.22475541 * T * R
            - 0.00683783 * T * T
            - 0.05481717 * R * R
            + 0.00122874 * T * T * R
            + 0.00085282 * T * R * R
            - 0.00000199 * T * T * R * R
        )
    return round((hi_f - 32) * 5 / 9, 1)


# ─── Heat alert level ──────────────────────────────────────────────────────────
def get_heat_level(temp_c: float) -> Dict[str, str]:
    from config.settings import HEAT_THRESHOLDS
    for level, info in HEAT_THRESHOLDS.items():
        if temp_c <= info["max"]:
            return {"level": level, "label": info["label"], "color": info["color"]}
    return {"level": "extreme", "label": "Extreme Heat", "color": "purple"}


# ─── UHI zone classifier ──────────────────────────────────────────────────────
def classify_zone(area: str) -> str:
    """Returns the surface type key for a given area string."""
    from config.settings import ZONE_KEYWORDS
    area_lower = area.lower()
    for surface_type, keywords in ZONE_KEYWORDS.items():
        if any(kw.lower() in area_lower for kw in keywords):
            return surface_type
    return "mixed_urban"


# ─── Time helpers ──────────────────────────────────────────────────────────────
def current_hour_ist() -> int:
    """Returns current hour in IST (UTC+5:30)."""
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.hour


def is_peak_heat_hour() -> bool:
    from config.settings import DANGER_HOURS
    return current_hour_ist() in DANGER_HOURS


def format_hour(h: int) -> str:
    if h == 0:   return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h-12} PM"


# ─── Misc ──────────────────────────────────────────────────────────────────────
def wind_direction_name(degrees: float) -> str:
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degrees / 22.5) + 0.5) % 16
    return dirs[idx]


def beautifully_format_number(val: float, unit: str = "") -> str:
    return f"{val:.1f}{unit}"


def safe_get(url: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
    """Safe GET request returning parsed JSON or None."""
    try:
        resp = requests.get(url, params=params or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[HTTP ERROR] {url}: {e}")
        return None
