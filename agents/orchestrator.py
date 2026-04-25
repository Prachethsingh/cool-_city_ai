"""
agents/orchestrator.py – Central Orchestrator

The single entry-point for the CoolCity AI system.
Handles:
  - Input validation
  - Agent coordination with error recovery
  - Caching of full results
  - Logging
"""

from __future__ import annotations
import time
import json
import hashlib
from typing import Dict, Any, Optional

from agents.user_assistant import UserAssistantAgent
from agents.base_agent import AgentResult


# Simple in-memory result cache (key = request hash)
_result_cache: Dict[str, tuple] = {}
CACHE_TTL = 1800  # 30 min


class Orchestrator:
    """
    CoolCity AI orchestrator.

    Usage:
        orch = Orchestrator()
        result = orch.analyse(
            city="Bengaluru",
            area="Koramangala",
            building_type="apartment",
            has_ac=True,
            floor_number=4,
            facing="west",
            num_people=3,
            area_sqft=900,
        )
        # result is a dict with keys: weather, uhi, plan, narrative, meta
    """

    def __init__(self):
        self.assistant = UserAssistantAgent()

    def analyse(
        self,
        city:          str  = "Bengaluru",
        area:          str  = "Koramangala",
        building_type: str  = "apartment",
        has_ac:        bool = True,
        floor_number:  int  = 3,
        facing:        str  = "south",
        num_people:    int  = 3,
        area_sqft:     int  = 1000,
        use_cache:     bool = True,
    ) -> Dict[str, Any]:
        """
        Full pipeline: weather → UHI → cooling plan → narrative.
        Returns a dict or raises on critical failure.
        """
        params = {
            "city": city.strip().title(),
            "area": area.strip(),
            "building_type": building_type,
            "has_ac": has_ac,
            "floor_number": floor_number,
            "facing": facing,
            "num_people": num_people,
            "area_sqft": area_sqft,
        }

        # Cache check
        cache_key = _hash_params(params)
        if use_cache and cache_key in _result_cache:
            val, ts = _result_cache[cache_key]
            if time.time() - ts < CACHE_TTL:
                print(f"  [cache hit] returning cached result for {area}, {city}")
                return val

        # Run pipeline
        result: AgentResult = self.assistant.run(**params)

        if not result.success:
            # Return partial data with error info
            return {
                "error": result.error,
                "success": False,
                "data": result.data,
            }

        output = {
            "success":   True,
            "elapsed_ms": result.elapsed_ms,
            **result.data,
        }

        # Store in cache
        _result_cache[cache_key] = (output, time.time())
        return output

    def quick_weather(self, city: str, area: str = "") -> Dict:
        """Lightweight weather-only check."""
        from agents.weather_monitor import WeatherMonitorAgent
        r = WeatherMonitorAgent().run(city=city, area=area)
        return r.data if r.success else {"error": r.error}

    def city_heat_map(self, city: str, base_temp: float = 40.0) -> Dict:
        """UHI-only heat map for a full city."""
        from agents.urban_heat_map import UrbanHeatMapAgent
        r = UrbanHeatMapAgent().run(city=city, base_temp=base_temp)
        return r.data if r.success else {"error": r.error}


def _hash_params(params: dict) -> str:
    raw = json.dumps(params, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()
