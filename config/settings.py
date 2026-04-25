"""
CoolCity AI - Configuration Settings
All free/open-source services, no hardware needed.
"""

# ─── Open-Meteo (fully free, no API key needed) ───────────────────────────────
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# ─── Nominatim (free OSM geocoding) ───────────────────────────────────────────
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# ─── Anthropic API (via env) ──────────────────────────────────────────────────
# Set ANTHROPIC_API_KEY in your .env file or environment
import os
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-sonnet-4-20250514"

# ─── App Settings ─────────────────────────────────────────────────────────────
APP_NAME = "CoolCity AI"
APP_VERSION = "1.0.0"
DEFAULT_CITY = "Bengaluru"
DEFAULT_COUNTRY = "India"

# ─── UHI (Urban Heat Island) Heuristics ───────────────────────────────────────
# Surface type → approximate UHI temperature addition (°C)
SURFACE_HEAT_FACTORS = {
    "dense_concrete": 4.5,
    "asphalt_road": 3.8,
    "mixed_urban": 2.5,
    "suburban": 1.5,
    "park_green": -1.0,
    "water_body": -2.0,
}

# Zone classification by density keyword
ZONE_KEYWORDS = {
    "dense_concrete":  ["CBD", "central", "city center", "commercial", "downtown", "MG Road", "Brigade", "Whitefield"],
    "asphalt_road":    ["highway", "ring road", "NH", "flyover", "industrial"],
    "mixed_urban":     ["Koramangala", "Indiranagar", "HSR", "Jayanagar", "BTM", "Marathahalli"],
    "suburban":        ["Sarjapur", "Electronic City", "Kengeri", "Yelahanka", "Devanahalli"],
    "park_green":      ["Cubbon", "Lalbagh", "park", "garden", "forest", "lake view"],
    "water_body":      ["lake", "pond", "Hesaraghatta", "Ulsoor", "Bellandur"],
}

# Cooling interventions → temperature reduction (°C) + description
COOLING_INTERVENTIONS = {
    "plant_trees": {
        "temp_reduction": 1.5,
        "energy_saving_pct": 10,
        "description": "Plant 3–5 native trees near your building",
        "feasibility": "medium-term",
        "cost": "low",
    },
    "green_roof": {
        "temp_reduction": 2.0,
        "energy_saving_pct": 15,
        "description": "Install a green/cool roof",
        "feasibility": "long-term",
        "cost": "medium",
    },
    "reflective_paint": {
        "temp_reduction": 1.0,
        "energy_saving_pct": 8,
        "description": "Paint rooftop/walls with white or cool-reflective paint",
        "feasibility": "short-term",
        "cost": "low",
    },
    "cross_ventilation": {
        "temp_reduction": 0.8,
        "energy_saving_pct": 20,
        "description": "Open opposite windows at dawn/dusk for cross-ventilation",
        "feasibility": "immediate",
        "cost": "zero",
    },
    "shade_curtains": {
        "temp_reduction": 0.5,
        "energy_saving_pct": 12,
        "description": "Use blackout/reflective curtains on south/west-facing windows",
        "feasibility": "immediate",
        "cost": "low",
    },
    "optimise_ac": {
        "temp_reduction": 0.0,
        "energy_saving_pct": 25,
        "description": "Set AC to 24–26°C, pre-cool in off-peak hours (6–8 PM)",
        "feasibility": "immediate",
        "cost": "zero",
    },
    "evaporative_cooling": {
        "temp_reduction": 1.2,
        "energy_saving_pct": 30,
        "description": "Use wet cloth / evaporative pads on windows",
        "feasibility": "immediate",
        "cost": "zero",
    },
    "terrace_garden": {
        "temp_reduction": 1.8,
        "energy_saving_pct": 18,
        "description": "Create a small terrace/balcony garden with potted plants",
        "feasibility": "short-term",
        "cost": "low",
    },
}

# Building types
BUILDING_TYPES = ["apartment", "house", "office", "villa", "hostel", "hospital", "school"]

# Heat alert thresholds (°C)
HEAT_THRESHOLDS = {
    "normal":    {"max": 30, "color": "green",  "label": "Normal"},
    "warm":      {"max": 34, "color": "yellow", "label": "Warm"},
    "hot":       {"max": 38, "color": "orange", "label": "Hot"},
    "very_hot":  {"max": 42, "color": "red",    "label": "Very Hot"},
    "extreme":   {"max": 99, "color": "purple", "label": "Extreme Heat"},
}

# Hours at which outdoor activity is dangerous (Indian summer)
DANGER_HOURS = list(range(11, 17))   # 11 AM – 4 PM
SAFE_HOURS   = list(range(5, 9)) + list(range(19, 22))  # 5–8 AM, 7–9 PM

CACHE_TTL_SECONDS = 1800   # 30 minutes cache for weather data
