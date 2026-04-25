"""
agents/urban_heat_map.py – Agent 2: Urban Heat Island (UHI) Mapping Agent

Software-only UHI analysis using:
  - Surface type heuristics (from config/settings.py)
  - Open building/land-cover data patterns
  - City-specific zone databases for major Indian cities
  - Physics-based UHI estimation formulas

No hardware or paid APIs needed.
"""

from __future__ import annotations
import math
import json
from typing import Dict, List, Any, Optional, Tuple

from agents.base_agent import BaseAgent, AgentResult
from utils.helpers import classify_zone, heat_index
from config.settings import SURFACE_HEAT_FACTORS, ZONE_KEYWORDS


# ─── Indian city zone databases (curated open data) ──────────────────────────
CITY_ZONE_DATA: Dict[str, List[Dict]] = {
    "bengaluru": [
        {"name": "Koramangala",     "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 12},
        {"name": "Indiranagar",     "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 15},
        {"name": "HSR Layout",      "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 10},
        {"name": "Whitefield",      "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 8},
        {"name": "MG Road",         "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 5},
        {"name": "Electronic City", "type": "asphalt_road",   "pop_density": "high",   "green_cover_pct": 9},
        {"name": "Marathahalli",    "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 7},
        {"name": "Jayanagar",       "type": "suburban",       "pop_density": "medium", "green_cover_pct": 22},
        {"name": "Malleswaram",     "type": "suburban",       "pop_density": "medium", "green_cover_pct": 20},
        {"name": "Cubbon Park",     "type": "park_green",     "pop_density": "low",    "green_cover_pct": 85},
        {"name": "Lalbagh",         "type": "park_green",     "pop_density": "low",    "green_cover_pct": 90},
        {"name": "Ulsoor Lake",     "type": "water_body",     "pop_density": "low",    "green_cover_pct": 40},
        {"name": "Hebbal",          "type": "suburban",       "pop_density": "medium", "green_cover_pct": 18},
        {"name": "Sarjapur",        "type": "suburban",       "pop_density": "low",    "green_cover_pct": 25},
        {"name": "BTM Layout",      "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 11},
        {"name": "Banashankari",    "type": "suburban",       "pop_density": "medium", "green_cover_pct": 19},
        {"name": "Yeshwanthpur",    "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 13},
        {"name": "Rajajinagar",     "type": "suburban",       "pop_density": "medium", "green_cover_pct": 16},
        {"name": "KR Puram",        "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 10},
        {"name": "Bellandur",       "type": "water_body",     "pop_density": "medium", "green_cover_pct": 30},
    ],
    "mumbai": [
        {"name": "Dharavi",         "type": "dense_concrete", "pop_density": "extreme","green_cover_pct": 2},
        {"name": "Andheri",         "type": "mixed_urban",    "pop_density": "very_high","green_cover_pct": 8},
        {"name": "BKC",             "type": "dense_concrete", "pop_density": "high",   "green_cover_pct": 5},
        {"name": "Powai",           "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 25},
        {"name": "Borivali",        "type": "suburban",       "pop_density": "high",   "green_cover_pct": 35},
        {"name": "Marine Drive",    "type": "water_body",     "pop_density": "low",    "green_cover_pct": 10},
        {"name": "Sanjay Gandhi NP","type": "park_green",     "pop_density": "very_low","green_cover_pct": 95},
    ],
    "delhi": [
        {"name": "Connaught Place", "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 5},
        {"name": "Lajpat Nagar",    "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 10},
        {"name": "Dwarka",          "type": "suburban",       "pop_density": "high",   "green_cover_pct": 18},
        {"name": "Lodhi Garden",    "type": "park_green",     "pop_density": "low",    "green_cover_pct": 80},
        {"name": "Yamuna bank",     "type": "water_body",     "pop_density": "low",    "green_cover_pct": 20},
        {"name": "Rohini",          "type": "suburban",       "pop_density": "high",   "green_cover_pct": 15},
        {"name": "Noida Sec 62",    "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 12},
    ],
    "chennai": [
        {"name": "T. Nagar",        "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 4},
        {"name": "Anna Nagar",      "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 14},
        {"name": "Besant Nagar",    "type": "mixed_urban",    "pop_density": "medium", "green_cover_pct": 20},
        {"name": "Marina Beach",    "type": "water_body",     "pop_density": "low",    "green_cover_pct": 5},
        {"name": "Guindy",          "type": "park_green",     "pop_density": "low",    "green_cover_pct": 75},
    ],
    "hyderabad": [
        {"name": "Hitech City",     "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 8},
        {"name": "Banjara Hills",   "type": "suburban",       "pop_density": "medium", "green_cover_pct": 25},
        {"name": "Old City",        "type": "dense_concrete", "pop_density": "very_high","green_cover_pct": 3},
        {"name": "Hussain Sagar",   "type": "water_body",     "pop_density": "low",    "green_cover_pct": 15},
        {"name": "Gachibowli",      "type": "mixed_urban",    "pop_density": "high",   "green_cover_pct": 18},
    ],
}

# ─── Surface albedo values ────────────────────────────────────────────────────
ALBEDO = {
    "dense_concrete": 0.25,
    "asphalt_road":   0.10,
    "mixed_urban":    0.20,
    "suburban":       0.25,
    "park_green":     0.35,
    "water_body":     0.08,
}


class UrbanHeatMapAgent(BaseAgent):
    """
    Software-only Urban Heat Island analysis.

    For a given city + area, computes:
      - UHI intensity (°C above rural baseline)
      - Surface heat factor
      - Green cover analysis
      - Hotspot ranking of all zones in the city
      - Heat map data (lat/lon grid approximation for visualisation)
    """

    name = "UrbanHeatMapAgent"
    description = "Analyses Urban Heat Island effect using open heuristics. No hardware needed."

    def _run(
        self,
        city: str = "Bengaluru",
        area: str = "",
        base_temp: float = 38.0,
    ) -> AgentResult:

        city_key = city.lower().strip()

        # Resolve zones for this city
        zones = CITY_ZONE_DATA.get(city_key, [])
        if not zones:
            # Generic fallback for unknown cities
            zones = self._generic_zones(city)

        # Classify user's area
        user_area_type = classify_zone(area) if area else "mixed_urban"

        # Compute UHI for every zone
        zone_analysis = [self._analyse_zone(z, base_temp) for z in zones]

        # Sort hottest first
        zone_analysis_sorted = sorted(zone_analysis, key=lambda z: z["uhi_temp"], reverse=True)

        # Find user's zone
        user_zone = self._find_user_zone(zone_analysis, area)
        if not user_zone and zone_analysis:
            # Fall back to synthesised data for the user's area type
            user_zone = self._analyse_zone(
                {"name": area or "Your Area", "type": user_area_type, "pop_density": "high", "green_cover_pct": 12},
                base_temp,
            )

        # Compute city average UHI
        avg_uhi = sum(z["uhi_delta"] for z in zone_analysis) / max(len(zone_analysis), 1)
        max_uhi = max(z["uhi_delta"] for z in zone_analysis) if zone_analysis else 0
        min_uhi = min(z["uhi_delta"] for z in zone_analysis) if zone_analysis else 0

        # Top 5 hottest and coolest zones
        top_hot  = zone_analysis_sorted[:5]
        top_cool = zone_analysis_sorted[-5:][::-1]

        # Intervention potential for user's zone
        interventions = self._recommend_interventions(user_zone)

        data = {
            "city": city,
            "base_temp": base_temp,
            "city_uhi_summary": {
                "avg_delta":      round(avg_uhi, 2),
                "max_delta":      round(max_uhi, 2),
                "min_delta":      round(min_uhi, 2),
                "zones_analysed": len(zone_analysis),
            },
            "all_zones":     zone_analysis_sorted,
            "top_hotspots":  top_hot,
            "top_cool_zones": top_cool,
            "user_zone":     user_zone,
            "interventions": interventions,
        }

        msg = (
            f"{city} UHI: avg +{avg_uhi:.1f} C, "
            f"hottest zone: {top_hot[0]['name'] if top_hot else 'N/A'} (+{max_uhi:.1f} C)"
        )
        return self._ok(data, msg)

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _analyse_zone(self, zone: dict, base_temp: float) -> dict:
        surface_type   = zone.get("type", "mixed_urban")
        green_cover    = zone.get("green_cover_pct", 15)
        pop_density    = zone.get("pop_density", "medium")

        # UHI delta from surface factor
        uhi_delta = SURFACE_HEAT_FACTORS.get(surface_type, 2.5)

        # Reduce UHI with green cover
        green_reduction = (green_cover / 100) * 3.0
        uhi_delta = max(uhi_delta - green_reduction, -2.5)

        # Population density bonus
        density_bonus = {"extreme": 0.8, "very_high": 0.5, "high": 0.3, "medium": 0.1, "low": 0.0, "very_low": -0.2}
        uhi_delta += density_bonus.get(pop_density, 0.1)

        uhi_temp  = round(base_temp + uhi_delta, 1)
        risk      = _risk_level(uhi_delta)
        albedo    = ALBEDO.get(surface_type, 0.20)

        return {
            "name":          zone["name"],
            "surface_type":  surface_type,
            "green_cover_pct": green_cover,
            "pop_density":   pop_density,
            "uhi_delta":     round(uhi_delta, 2),
            "uhi_temp":      uhi_temp,
            "risk":          risk,
            "albedo":        albedo,
        }

    def _find_user_zone(self, zones: List[dict], area: str) -> Optional[dict]:
        if not area:
            return None
        area_lower = area.lower()
        for z in zones:
            if z["name"].lower() in area_lower or area_lower in z["name"].lower():
                return z
        return None

    def _generic_zones(self, city: str) -> List[dict]:
        """Synthetic zones for cities not in our database."""
        return [
            {"name": f"{city} Central",    "type": "dense_concrete", "pop_density": "very_high", "green_cover_pct": 5},
            {"name": f"{city} Old City",   "type": "mixed_urban",    "pop_density": "high",      "green_cover_pct": 10},
            {"name": f"{city} Suburbs",    "type": "suburban",       "pop_density": "medium",    "green_cover_pct": 25},
            {"name": f"{city} Industrial", "type": "asphalt_road",   "pop_density": "high",      "green_cover_pct": 6},
            {"name": f"{city} Park",       "type": "park_green",     "pop_density": "low",       "green_cover_pct": 80},
        ]

    def _recommend_interventions(self, user_zone: Optional[dict]) -> List[dict]:
        if not user_zone:
            return []
        from config.settings import COOLING_INTERVENTIONS
        surface = user_zone.get("surface_type", "mixed_urban")
        green   = user_zone.get("green_cover_pct", 15)

        # Always recommend these
        recs = []
        for key, info in COOLING_INTERVENTIONS.items():
            score = 0
            if surface in ("dense_concrete", "asphalt_road") and key in ("reflective_paint", "green_roof", "plant_trees"):
                score += 3
            if green < 10 and key in ("plant_trees", "terrace_garden"):
                score += 2
            if key in ("shade_curtains", "cross_ventilation", "optimise_ac", "evaporative_cooling"):
                score += 1   # always useful

            recs.append({
                "key":           key,
                "score":         score,
                "description":   info["description"],
                "temp_reduction": info["temp_reduction"],
                "energy_saving_pct": info["energy_saving_pct"],
                "feasibility":   info["feasibility"],
                "cost":          info["cost"],
            })

        recs.sort(key=lambda r: r["score"], reverse=True)
        return recs[:6]   # Top 6 most relevant


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _risk_level(delta: float) -> str:
    if delta >= 4:    return "critical"
    if delta >= 2.5:  return "high"
    if delta >= 1.0:  return "moderate"
    if delta >= 0:    return "low"
    return "cool"
