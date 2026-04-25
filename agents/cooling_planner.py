"""
agents/cooling_planner.py – Agent 3: Cooling Planner Agent

Takes weather data + UHI data + user context and generates:
  1. Personalised cooling plan (daily schedule)
  2. Building-specific recommendations
  3. Energy-saving strategy
  4. Short-term vs long-term action plans
  5. Community-level interventions

Uses rule-based simulation + optional LLM enrichment (Anthropic Claude).
"""

from __future__ import annotations
import math
import json
import datetime
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent, AgentResult
from utils.helpers import current_hour_ist, format_hour, is_peak_heat_hour
from config.settings import (
    COOLING_INTERVENTIONS, DANGER_HOURS, SAFE_HOURS,
    BUILDING_TYPES, LLM_MODEL
)


class CoolingPlannerAgent(BaseAgent):
    """
    Generates a comprehensive, personalised cooling plan.

    Inputs (via run(**kwargs)):
        weather_data  – dict from WeatherMonitorAgent
        uhi_data      – dict from UrbanHeatMapAgent
        building_type – "apartment" | "house" | "office" | ...
        has_ac        – bool
        floor_number  – int (for apartments)
        facing        – "north" | "south" | "east" | "west" | "mixed"
    """

    name = "CoolingPlannerAgent"
    description = "Generates personalised cooling schedules and building-specific action plans."

    def _run(
        self,
        weather_data:  Dict  = None,
        uhi_data:      Dict  = None,
        building_type: str   = "apartment",
        has_ac:        bool  = True,
        floor_number:  int   = 3,
        facing:        str   = "south",
        num_people:    int   = 3,
        area_sqft:     int   = 1000,
    ) -> AgentResult:

        weather_data = weather_data or {}
        uhi_data     = uhi_data     or {}

        # Pull key metrics
        current_temp  = weather_data.get("current", {}).get("temperature",  38)
        feels_like    = weather_data.get("current", {}).get("feels_like",   40)
        humidity      = weather_data.get("current", {}).get("humidity",     60)
        today_max     = weather_data.get("today",   {}).get("max",          42)
        today_min     = weather_data.get("today",   {}).get("min",          28)
        uhi_delta     = uhi_data.get("user_zone",  {}).get("uhi_delta",     2.5)
        interventions = uhi_data.get("interventions", [])
        city          = uhi_data.get("city", weather_data.get("location", {}).get("city", "your city"))
        area_display  = weather_data.get("location", {}).get("display", city)

        # Effective indoor temp (rough estimate)
        indoor_temp = _estimate_indoor_temp(current_temp, building_type, floor_number, facing, has_ac, uhi_delta)

        # 1. Daily cooling schedule
        schedule = self._build_daily_schedule(
            today_max, today_min, has_ac, building_type, facing
        )

        # 2. Immediate actions (do right now)
        immediate = self._immediate_actions(current_temp, humidity, has_ac, facing)

        # 3. Short-term actions (this week)
        short_term = self._short_term_actions(building_type, facing, floor_number, uhi_delta, interventions)

        # 4. Long-term actions (this season / year)
        long_term = self._long_term_actions(building_type, uhi_delta, interventions)

        # 5. Energy savings estimate
        energy = self._energy_savings(has_ac, building_type, area_sqft, num_people, interventions)

        # 6. Community actions
        community = self._community_actions(uhi_delta)

        # 7. Health alerts
        health = self._health_alerts(today_max, humidity, num_people)

        # 8. Simulate temperature reductions from top interventions
        simulation = self._simulate_reduction(current_temp, uhi_delta, interventions)

        data = {
            "summary": {
                "city":           city,
                "area":           area_display,
                "current_temp":   current_temp,
                "feels_like":     feels_like,
                "today_max":      today_max,
                "indoor_temp":    indoor_temp,
                "uhi_delta":      uhi_delta,
                "building_type":  building_type,
                "has_ac":         has_ac,
                "floor":          floor_number,
                "facing":         facing,
            },
            "daily_schedule":    schedule,
            "immediate_actions": immediate,
            "short_term":        short_term,
            "long_term":         long_term,
            "energy_savings":    energy,
            "community_actions": community,
            "health_alerts":     health,
            "simulation":        simulation,
        }

        msg = (
            f"Plan for {building_type} in {area_display}: "
            f"indoor ~{indoor_temp} C, {len(immediate)} immediate actions"
        )
        return self._ok(data, msg)

    # ─── Schedule builder ────────────────────────────────────────────────────
    def _build_daily_schedule(
        self, max_temp: float, min_temp: float,
        has_ac: bool, btype: str, facing: str
    ) -> List[Dict]:
        """Returns hourly cooling schedule for the day."""
        schedule = []
        slots = [
            (5,  6,  "Dawn",        "Pre-cool", True),
            (6,  8,  "Early morn",  "Exercise",  True),
            (8,  10, "Morning",     "Prep",      False),
            (10, 13, "Late morning","Danger zone",False),
            (13, 17, "Afternoon",   "Peak heat", False),
            (17, 19, "Evening",     "Cool down", False),
            (19, 21, "Night",       "Best AC",   True),
            (21, 24, "Late night",  "Natural",   True),
        ]
        for start, end, period, label, is_safe in slots:
            actions = _hour_range_actions(start, has_ac, btype, facing, max_temp, min_temp)
            schedule.append({
                "start":   start,
                "end":     end,
                "period":  period,
                "label":   label,
                "is_safe": is_safe,
                "actions": actions,
                "temp_estimate": _period_temp(start, max_temp, min_temp),
            })
        return schedule

    def _immediate_actions(self, temp: float, humidity: float, has_ac: bool, facing: str) -> List[str]:
        actions = []
        if temp >= 40:
            actions.append("[ALERT] Stay indoors - heat is extreme right now")
        if humidity > 70:
            actions.append("[HYDRATE] Drink water every 30 minutes - humidity raises heat stress")
        actions.append("Close all south/west-facing windows immediately")
        actions.append("Draw blackout or reflective curtains on sun-facing windows")
        if has_ac:
            actions.append("Set AC to 24-26 C (not lower - this is optimal for savings + comfort)")
        else:
            actions.append("Place a wet cloth/towel in front of your fan for 3-5 C feel cooler")
        actions.append("Mist your indoor plants - they naturally cool the air")
        if facing in ("south", "west"):
            actions.append("Hang a light-coloured sheet/tarpaulin outside your south/west wall")
        return actions

    def _short_term_actions(self, btype: str, facing: str, floor: int, uhi: float, interventions: list) -> List[Dict]:
        items = []
        # From interventions list (already sorted by relevance)
        for inv in interventions[:4]:
            items.append({
                "action":      inv["description"],
                "impact":      f"-{inv['temp_reduction']} C, {inv['energy_saving_pct']}% energy saved",
                "temp_reduction": inv["temp_reduction"],
                "energy_saving_pct": inv["energy_saving_pct"],
                "feasibility": inv["feasibility"],
                "cost":        inv["cost"],
            })
        # Building-specific
        if btype == "apartment" and floor >= 4:
            items.append({
                "action": "Apply 3M window solar film to upper-floor windows",
                "impact": "-1-2 C indoors, reduces glare",
                "feasibility": "this week",
                "cost": "low",
            })
        if btype in ("house", "villa"):
            items.append({
                "action": "Create a terrace shading structure with bamboo/palm fronds",
                "impact": "-2-3 C on top floor",
                "feasibility": "this weekend",
                "cost": "low",
            })
        return items

    def _long_term_actions(self, btype: str, uhi: float, interventions: list) -> List[Dict]:
        items = []
        if uhi >= 3:
            items.append({
                "action": "Lobby your Resident Welfare Association (RWA) to paint the building roof white",
                "impact": "-1.5 C for entire building",
                "timeline": "1-2 months",
            })
            items.append({
                "action": "Work with BBMP / municipal body to plant trees on the street in front",
                "impact": "-1-2 C street temperature over 2-3 years",
                "timeline": "3-6 months",
            })
        if btype in ("house", "villa"):
            items.append({
                "action": "Install a green roof or terrace garden with drought-resistant plants",
                "impact": "-2-3 C on top floor, 15% AC energy savings",
                "timeline": "1-3 months",
            })
        items.append({
            "action": "Switch to energy-star rated inverter AC (5-star BEE rating)",
            "impact": "35–40% reduction in cooling energy",
            "timeline": "next purchase cycle",
        })
        items.append({
            "action": "Install solar panels to power AC using clean energy",
            "impact": "Near-zero carbon cooling; 80% electricity cost reduction",
            "timeline": "6-12 months",
        })
        return items

    def _energy_savings(self, has_ac, btype, area_sqft, people, interventions) -> Dict:
        base_kwh_per_day = (area_sqft / 200) * (1.5 if has_ac else 0.2) * (people / 2)
        total_saving_pct = 0
        for inv in interventions[:5]:
            total_saving_pct += inv.get("energy_saving_pct", 0) * 0.6  # overlap discount
        total_saving_pct = min(total_saving_pct, 60)
        saved_kwh = base_kwh_per_day * (total_saving_pct / 100)
        cost_per_kwh = 6.5  # INR average (Karnataka BESCOM rate)
        return {
            "base_kwh_per_day":  round(base_kwh_per_day, 1),
            "saving_pct":        round(total_saving_pct, 1),
            "saved_kwh_per_day": round(saved_kwh, 2),
            "saved_inr_per_day": round(saved_kwh * cost_per_kwh, 1),
            "saved_inr_per_month": round(saved_kwh * cost_per_kwh * 30, 0),
            "co2_saved_kg_month": round(saved_kwh * 0.82 * 30, 1),
        }

    def _community_actions(self, uhi: float) -> List[str]:
        actions = [
            "Organise a neighbourhood tree-planting drive with your apartment community",
            "Petition your RWA to apply cool-roof paint on all building terraces",
            "Use greywater to water plants and trees in common areas",
            "Share this cooling plan with elderly neighbours - they are most vulnerable",
            "Report illegal tree-cutting to BBMP Tree Officer (helpline: 080-22221188)",
        ]
        if uhi >= 3.5:
            actions.insert(0, "Request your ward office to set up a Community Cooling Centre (open public space with fans/AC)")
        return actions

    def _health_alerts(self, max_temp: float, humidity: float, people: int) -> List[Dict]:
        alerts = []
        heat_idx = max_temp + (humidity - 40) * 0.1  # simplified
        if heat_idx >= 44:
            alerts.append({
                "severity": "critical",
                "icon": "ALERT",
                "message": "Heat stroke risk is HIGH today. Keep elderly/children fully indoors 10 AM-6 PM.",
            })
        elif heat_idx >= 40:
            alerts.append({
                "severity": "high",
                "icon": "WARNING",
                "message": "High heat alert. Limit outdoor activity. Drink 3-4 litres of water.",
            })
        alerts.append({
            "severity": "info",
            "icon": "WATER",
            "message": "Every person needs at least 3 litres of water today. Set phone reminders.",
        })
        alerts.append({
            "severity": "info",
            "icon": "CLOTHING",
            "message": "Wear light-coloured, loose cotton or linen clothing.",
        })
        if people >= 5:
            alerts.append({
                "severity": "warning",
                "icon": "DENSITY",
                "message": "More people = more body heat indoors. Stagger kitchen/cooking times to reduce indoor heat load.",
            })
        return alerts

    def _simulate_reduction(self, base_temp: float, uhi: float, interventions: list) -> Dict:
        """Simulate temperature if top 3 interventions are applied."""
        top3 = [i for i in interventions if i.get("temp_reduction", 0) > 0][:3]
        total_reduction = sum(i["temp_reduction"] for i in top3)
        simulated_temp  = round(base_temp - total_reduction, 1)
        return {
            "current_temp":  base_temp,
            "top_3_actions": [i["description"] for i in top3],
            "total_reduction": round(total_reduction, 1),
            "simulated_temp":  simulated_temp,
            "note": f"Combining these three interventions could reduce your local temperature by ~{total_reduction:.1f} C over time.",
        }


# ─── Pure helper functions ─────────────────────────────────────────────────────

def _estimate_indoor_temp(
    outdoor: float, btype: str, floor: int, facing: str, has_ac: bool, uhi: float
) -> float:
    indoor = outdoor + uhi * 0.3   # partial UHI bleed-in
    if floor >= 5:    indoor += 1.5
    elif floor >= 3:  indoor += 0.8
    if facing in ("south", "west"): indoor += 1.2
    if btype == "apartment":        indoor -= 0.5  # shared walls reduce exposure
    if has_ac:                      indoor  = min(indoor, outdoor - 6)
    return round(indoor, 1)


def _period_temp(hour: int, max_t: float, min_t: float) -> float:
    """Sinusoidal day-temperature model. Peak at 14:00."""
    phase = (hour - 14) / 12 * math.pi
    temp = min_t + (max_t - min_t) * (0.5 - 0.5 * math.cos(phase + math.pi))
    return round(temp, 1)


def _hour_range_actions(hour: int, has_ac: bool, btype: str, facing: str, max_t: float, min_t: float) -> List[str]:
    actions = []
    if 5 <= hour < 8:
        actions.append("Open all windows – coolest air of the day")
        actions.append("Run fans to flush out overnight warm air")
        if btype in ("house", "villa"):
            actions.append("Water your garden / terrace plants")
    elif 8 <= hour < 11:
        actions.append("Start closing windows as temperature rises")
        actions.append("Pre-cool rooms if you have AC (brief blast then off)")
    elif 11 <= hour < 17:
        actions.append("Keep all windows and curtains fully closed")
        if has_ac:
            actions.append("Run AC at 25°C with fan mode")
        else:
            actions.append("Use wet towel in front of fan + stay on lower floors")
        if facing in ("south", "west"):
            actions.append("Block direct sunlight on south/west windows")
    elif 17 <= hour < 19:
        actions.append("Gradually open east-facing windows as sun shifts")
        actions.append("This is a good time to cook (before peak evening heat)")
    elif 19 <= hour < 22:
        actions.append("Open all windows - evening breeze begins")
        if has_ac:
            actions.append("Ideal AC time: 24 C for 2-3 hrs to cool room for sleep")
        actions.append("Light, cold evening meal – avoid generating kitchen heat")
    else:
        actions.append("Sleep with a thin wet sheet or light cotton")
        actions.append("Point fan across your body (not directly at face)")
    return actions



