"""
tests/test_agents.py – Unit tests for all CoolCity AI agents

Run with:
    pytest tests/ -v
or:
    python tests/test_agents.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import unittest


class TestWeatherMonitorAgent(unittest.TestCase):

    def setUp(self):
        from agents.weather_monitor import WeatherMonitorAgent
        self.agent = WeatherMonitorAgent()

    def test_bengaluru_weather(self):
        result = self.agent.run(city="Bengaluru", area="Koramangala")
        self.assertTrue(result.success, f"Failed: {result.error}")
        data = result.data
        self.assertIn("current", data)
        self.assertIn("today", data)
        self.assertIn("hourly_today", data)
        self.assertIn("forecast_7day", data)
        cur = data["current"]
        self.assertIn("temperature", cur)
        self.assertIn("feels_like", cur)
        self.assertIsInstance(cur["temperature"], (int, float))
        print(f"  ✓ Bengaluru: {cur['temperature']}°C, {cur['condition']}")

    def test_mumbai_weather(self):
        result = self.agent.run(city="Mumbai")
        self.assertTrue(result.success, f"Failed: {result.error}")
        print(f"  ✓ Mumbai: {result.data['current']['temperature']}°C")

    def test_unknown_city_geocode(self):
        # Should fall back to heuristic or return failure gracefully
        result = self.agent.run(city="Pune")
        print(f"  ✓ Pune: success={result.success}")

    def test_forecast_7days(self):
        result = self.agent.run(city="Delhi")
        if result.success:
            self.assertGreaterEqual(len(result.data["forecast_7day"]), 3)
            print(f"  ✓ Delhi 7-day forecast: {len(result.data['forecast_7day'])} days")


class TestUrbanHeatMapAgent(unittest.TestCase):

    def setUp(self):
        from agents.urban_heat_map import UrbanHeatMapAgent
        self.agent = UrbanHeatMapAgent()

    def test_bengaluru_uhi(self):
        result = self.agent.run(city="Bengaluru", area="Koramangala", base_temp=40)
        self.assertTrue(result.success, f"Failed: {result.error}")
        data = result.data
        self.assertIn("all_zones", data)
        self.assertIn("top_hotspots", data)
        self.assertIn("user_zone", data)
        self.assertGreater(len(data["all_zones"]), 5)
        print(f"  ✓ Bengaluru UHI: {len(data['all_zones'])} zones, avg +{data['city_uhi_summary']['avg_delta']:.1f}°C")

    def test_zone_ranking(self):
        result = self.agent.run(city="Bengaluru", base_temp=40)
        self.assertTrue(result.success)
        zones = result.data["all_zones"]
        # Should be sorted hottest first
        for i in range(len(zones) - 1):
            self.assertGreaterEqual(round(zones[i]["uhi_delta"], 1), round(zones[i+1]["uhi_delta"], 1))
        print(f"  ✓ Zones correctly sorted by heat")

    def test_unknown_city_fallback(self):
        result = self.agent.run(city="Mysuru", base_temp=38)
        self.assertTrue(result.success)
        print(f"  ✓ Unknown city Mysuru: {len(result.data['all_zones'])} fallback zones")

    def test_interventions_generated(self):
        result = self.agent.run(city="Bengaluru", area="Whitefield", base_temp=42)
        self.assertTrue(result.success)
        interventions = result.data.get("interventions", [])
        self.assertGreater(len(interventions), 0)
        print(f"  ✓ Generated {len(interventions)} interventions for Whitefield")

    def test_cool_zone(self):
        result = self.agent.run(city="Bengaluru", area="Cubbon Park", base_temp=38)
        self.assertTrue(result.success)
        zone = result.data.get("user_zone")
        if zone:
            self.assertIn(zone["risk"], ["cool", "low"])
            print(f"  ✓ Cubbon Park correctly classified as {zone['risk']}")


class TestCoolingPlannerAgent(unittest.TestCase):

    def setUp(self):
        from agents.cooling_planner import CoolingPlannerAgent
        self.agent = CoolingPlannerAgent()

    def _mock_weather(self):
        return {
            "current": {"temperature": 40, "feels_like": 44, "humidity": 55},
            "today":   {"max": 43, "min": 28},
            "location": {"city": "Bengaluru", "display": "Koramangala, Bengaluru"},
        }

    def _mock_uhi(self):
        return {
            "city": "Bengaluru",
            "user_zone": {"uhi_delta": 2.5, "risk": "high", "surface_type": "mixed_urban", "green_cover_pct": 12},
            "interventions": [
                {"description": "Plant trees", "temp_reduction": 1.5, "energy_saving_pct": 10,
                 "feasibility": "medium-term", "cost": "low", "action": "Plant 3-5 trees", "score": 3},
                {"description": "Reflective paint", "temp_reduction": 1.0, "energy_saving_pct": 8,
                 "feasibility": "short-term", "cost": "low", "action": "White roof paint", "score": 2},
            ],
        }

    def test_apartment_with_ac(self):
        result = self.agent.run(
            weather_data=self._mock_weather(),
            uhi_data=self._mock_uhi(),
            building_type="apartment",
            has_ac=True,
            floor_number=5,
            facing="south",
        )
        self.assertTrue(result.success, f"Failed: {result.error}")
        data = result.data
        self.assertIn("daily_schedule", data)
        self.assertIn("immediate_actions", data)
        self.assertIn("energy_savings", data)
        self.assertGreater(len(data["immediate_actions"]), 0)
        print(f"  ✓ Apartment plan: {len(data['immediate_actions'])} immediate actions")

    def test_house_without_ac(self):
        result = self.agent.run(
            weather_data=self._mock_weather(),
            uhi_data=self._mock_uhi(),
            building_type="house",
            has_ac=False,
            facing="west",
        )
        self.assertTrue(result.success)
        actions = result.data["immediate_actions"]
        # Should recommend fan + wet cloth, not AC
        fan_action = any("fan" in a.lower() or "wet" in a.lower() for a in actions)
        self.assertTrue(fan_action, "Should have fan/cooling action for no-AC case")
        print(f"  ✓ House (no AC): {len(actions)} immediate actions")

    def test_energy_savings_positive(self):
        result = self.agent.run(
            weather_data=self._mock_weather(),
            uhi_data=self._mock_uhi(),
            has_ac=True,
            area_sqft=1200,
            num_people=4,
        )
        self.assertTrue(result.success)
        savings = result.data["energy_savings"]
        self.assertGreater(savings["saving_pct"], 0)
        self.assertGreater(savings["saved_inr_per_month"], 0)
        print(f"  ✓ Energy savings: {savings['saving_pct']:.0f}%, ₹{savings['saved_inr_per_month']:.0f}/month")

    def test_schedule_has_all_periods(self):
        result = self.agent.run(
            weather_data=self._mock_weather(),
            uhi_data=self._mock_uhi(),
        )
        self.assertTrue(result.success)
        schedule = result.data["daily_schedule"]
        self.assertGreaterEqual(len(schedule), 6)
        print(f"  ✓ Daily schedule: {len(schedule)} time slots")


class TestHelpers(unittest.TestCase):

    def test_geocode_bengaluru(self):
        from utils.helpers import geocode_city
        result = geocode_city("Bengaluru")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["lat"], 12.97, delta=0.5)
        print(f"  ✓ Bengaluru geocoded: {result['lat']}, {result['lon']}")

    def test_heat_index(self):
        from utils.helpers import heat_index
        hi = heat_index(40, 60)
        self.assertGreater(hi, 40)  # feels hotter with humidity
        print(f"  ✓ Heat index 40°C, 60%RH = {hi}°C")

    def test_classify_zone(self):
        from utils.helpers import classify_zone
        self.assertEqual(classify_zone("MG Road"),      "dense_concrete")
        self.assertEqual(classify_zone("Cubbon Park"),   "park_green")
        self.assertEqual(classify_zone("Koramangala"),   "mixed_urban")
        self.assertEqual(classify_zone("Ulsoor Lake"),   "water_body")
        print("  ✓ Zone classification working")

    def test_wind_direction(self):
        from utils.helpers import wind_direction_name
        self.assertEqual(wind_direction_name(0),   "N")
        self.assertEqual(wind_direction_name(90),  "E")
        self.assertEqual(wind_direction_name(180), "S")
        self.assertEqual(wind_direction_name(270), "W")
        print("  ✓ Wind direction names working")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🧪  CoolCity AI — Test Suite")
    print("="*60 + "\n")
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for cls in [TestHelpers, TestUrbanHeatMapAgent, TestCoolingPlannerAgent, TestWeatherMonitorAgent]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("  ✅  All tests passed!")
    else:
        print(f"  ❌  {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*60 + "\n")
