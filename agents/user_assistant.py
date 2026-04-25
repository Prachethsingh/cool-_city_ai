"""
agents/user_assistant.py – Agent 4: User Assistant Agent

The friendly, conversational front-end agent.
  - Collects user context (city, area, building type, etc.)
  - Orchestrates the other three agents
  - Uses Anthropic Claude API to generate plain-language summaries
  - Returns structured data + a human-friendly narrative
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional

import requests

from agents.base_agent import BaseAgent, AgentResult
from agents.weather_monitor import WeatherMonitorAgent
from agents.urban_heat_map import UrbanHeatMapAgent
from agents.cooling_planner import CoolingPlannerAgent
from config.settings import LLM_MODEL, ANTHROPIC_API_KEY


SYSTEM_PROMPT = """You are CoolCity AI, an expert urban climate advisor helping people in India 
survive and reduce the extreme 2026 summer heatwave.

You have access to real weather data, Urban Heat Island analysis, and personalised cooling plans.
Your job is to write a warm, practical, clear summary for a regular person (not a scientist).

Guidelines:
- Write in second person ("you", "your area")
- Use simple English; add Hindi words sparingly if natural (e.g., "paani peete raho")
- Include specific temperature numbers from the data
- Give 3–5 most important actions first, then the full plan
- Add encouragement — heatwaves are hard, be supportive
- Format with clear sections using emojis as section markers
- Keep it under 500 words total
- At the end, add: "🤖 Powered by CoolCity AI | Data: Open-Meteo | Analysis: Anthropic Claude"
"""


class UserAssistantAgent(BaseAgent):
    """
    Orchestrates all agents and synthesises a user-friendly response.

    Usage:
        agent = UserAssistantAgent()
        result = agent.run(
            city="Bengaluru",
            area="Koramangala",
            building_type="apartment",
            has_ac=True,
            floor_number=4,
            facing="west",
            num_people=3,
        )
    """

    name = "UserAssistantAgent"
    description = "Orchestrates all agents and generates a user-friendly cooling plan narrative."

    def __init__(self):
        self.weather_agent  = WeatherMonitorAgent()
        self.uhi_agent      = UrbanHeatMapAgent()
        self.planner_agent  = CoolingPlannerAgent()

    def _run(
        self,
        city:          str  = "Bengaluru",
        area:          str  = "Koramangala",
        building_type: str  = "apartment",
        has_ac:        bool = True,
        floor_number:  int  = 3,
        facing:        str  = "south",
        num_people:    int  = 3,
        area_sqft:     int  = 1000,
    ) -> AgentResult:

        print(f"\n{'='*60}")
        print(f"  CoolCity AI - Analysing: {area}, {city}")
        print(f"{'='*60}")

        # ── Step 1: Weather ──────────────────────────────────────────────────
        print("\n[1/4] Weather Monitor Agent...")
        weather_result = self.weather_agent.run(city=city, area=area)
        if not weather_result.success:
            return self._fail(f"Weather data unavailable: {weather_result.error}")
        weather_data = weather_result.data

        # ── Step 2: UHI Analysis ─────────────────────────────────────────────
        print("[2/4] Urban Heat Map Agent...")
        base_temp = weather_data.get("today", {}).get("max", 40)
        uhi_result = self.uhi_agent.run(city=city, area=area, base_temp=base_temp)
        uhi_data = uhi_result.data if uhi_result.success else {}

        # ── Step 3: Cooling Plan ─────────────────────────────────────────────
        print("[3/4] Cooling Planner Agent...")
        plan_result = self.planner_agent.run(
            weather_data=weather_data,
            uhi_data=uhi_data,
            building_type=building_type,
            has_ac=has_ac,
            floor_number=floor_number,
            facing=facing,
            num_people=num_people,
            area_sqft=area_sqft,
        )
        plan_data = plan_result.data if plan_result.success else {}

        # ── Step 4: LLM Narrative ────────────────────────────────────────────
        print("[4/4] Generating narrative (Anthropic Claude)...")
        narrative = self._generate_narrative(weather_data, uhi_data, plan_data)

        # ── Assemble full result ─────────────────────────────────────────────
        full_data = {
            "weather":   weather_data,
            "uhi":       uhi_data,
            "plan":      plan_data,
            "narrative": narrative,
            "meta": {
                "city":          city,
                "area":          area,
                "building_type": building_type,
                "has_ac":        has_ac,
                "floor":         floor_number,
                "facing":        facing,
                "num_people":    num_people,
            },
        }

        current_temp = weather_data.get("current", {}).get("temperature", 0)
        msg = f"Complete analysis ready for {area}, {city} ({current_temp} C)"
        print(f"\n[DONE] {msg}\n")
        return self._ok(full_data, msg)

    def _generate_narrative(
        self, weather: Dict, uhi: Dict, plan: Dict
    ) -> str:
        """Calls Anthropic Claude API to generate a human-friendly summary."""

        if not ANTHROPIC_API_KEY:
            return self._fallback_narrative(weather, uhi, plan)

        # Build compact context for the LLM
        context = {
            "city":           weather.get("location", {}).get("city", ""),
            "area":           weather.get("location", {}).get("display", ""),
            "current_temp_c": weather.get("current", {}).get("temperature"),
            "feels_like_c":   weather.get("current", {}).get("feels_like"),
            "today_max_c":    weather.get("today",   {}).get("max"),
            "humidity_pct":   weather.get("current", {}).get("humidity"),
            "uhi_delta_c":    uhi.get("user_zone", {}).get("uhi_delta", 2.5),
            "top_hotspot":    uhi.get("top_hotspots", [{}])[0].get("name", ""),
            "building_type":  plan.get("summary", {}).get("building_type", "apartment"),
            "has_ac":         plan.get("summary", {}).get("has_ac", False),
            "floor":          plan.get("summary", {}).get("floor", 1),
            "immediate_actions": plan.get("immediate_actions", [])[:5],
            "energy_savings":    plan.get("energy_savings", {}),
            "health_alerts":     [a["message"] for a in plan.get("health_alerts", [])[:2]],
            "top_interventions": [
                i["action"] for i in plan.get("short_term", [])[:3]
            ],
        }

        user_message = (
            "Here is the data for this user's location and situation:\n\n"
            + json.dumps(context, indent=2)
            + "\n\nWrite a warm, practical cooling advice summary for this person."
        )

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      LLM_MODEL,
                    "max_tokens": 700,
                    "system":     SYSTEM_PROMPT,
                    "messages":   [{"role": "user", "content": user_message}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json().get("content", [])
            for block in content:
                if block.get("type") == "text":
                    return block["text"]
        except Exception as e:
            print(f"  [LLM warning] Anthropic API error: {e} – using fallback narrative")

        return self._fallback_narrative(weather, uhi, plan)

    def _fallback_narrative(self, weather: Dict, uhi: Dict, plan: Dict) -> str:
        """Rule-based narrative when LLM is unavailable."""
        city      = weather.get("location", {}).get("city", "your city")
        area      = weather.get("location", {}).get("display", city)
        temp      = weather.get("current", {}).get("temperature", "?")
        feels     = weather.get("current", {}).get("feels_like", "?")
        max_t     = weather.get("today",   {}).get("max", "?")
        uhi_d     = uhi.get("user_zone",   {}).get("uhi_delta", 2.5)
        btype     = plan.get("summary",    {}).get("building_type", "home")
        actions   = plan.get("immediate_actions", [])
        savings   = plan.get("energy_savings", {})

        lines = [
            f"🌡️ **Heat Alert for {area}**",
            "",
            f"Right now it's **{temp}°C** (feels like **{feels}°C**) and today will peak at **{max_t}°C**.",
            f"Your area has a +{uhi_d:.1f}°C urban heat island effect – that's why it feels hotter than rural areas.",
            "",
            "⚡ **Do These Right Now:**",
        ]
        for i, action in enumerate(actions[:5], 1):
            lines.append(f"  {i}. {action}")

        if savings:
            lines += [
                "",
                f"💰 **Potential Savings:** Following this plan could save you ₹{savings.get('saved_inr_per_month', 0):.0f}/month on electricity.",
            ]

        lines += [
            "",
            "Stay safe, drink lots of water, and check on your elderly neighbours. 💙",
            "",
            "🤖 Powered by CoolCity AI | Data: Open-Meteo | Analysis: Anthropic Claude",
        ]
        return "\n".join(lines)
