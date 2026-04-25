#!/usr/bin/env python3
"""
main.py – CoolCity AI Entry Point

Usage:
    python main.py                         # start web server (default)
    python main.py --demo                  # run CLI demo (no server)
    python main.py --city Mumbai --area Andheri --demo
    python main.py --port 8080             # custom port
"""

import sys
import os
import argparse
import json

# ─── Ensure project root is on path ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_demo(city: str, area: str, building: str, has_ac: bool, floor: int, facing: str):
    """CLI demo that runs the full multi-agent pipeline and prints results."""
    print("\n" + "="*65)
    print("  CoolCity AI - Multi-Agent Heat Analysis Demo")
    print("="*65)

    from agents.orchestrator import Orchestrator
    orch = Orchestrator()

    print(f"\n[ANALYSIS] Analysing: {area}, {city}")
    print(f"   Building : {building}  |  Floor: {floor}  |  Facing: {facing}")
    print(f"   Has AC   : {'Yes' if has_ac else 'No'}")
    print()

    result = orch.analyse(
        city=city,
        area=area,
        building_type=building,
        has_ac=has_ac,
        floor_number=floor,
        facing=facing,
        num_people=3,
        area_sqft=900,
    )

    if not result.get("success"):
        print(f"\n[ERROR] Analysis failed: {result.get('error')}")
        return

    # ── Print narrative ────────────────────────────────────────────────────
    print("\n" + "-"*65)
    print("  AI COOLING ADVISOR REPORT")
    print("-"*65)
    narrative = result.get("narrative", "No narrative generated.")
    try:
        print(narrative)
    except UnicodeEncodeError:
        # Fallback for Windows terminal
        print(narrative.encode("ascii", "backslashreplace").decode("ascii"))

    # ── Weather summary ────────────────────────────────────────────────────
    w = result.get("weather", {})
    cur = w.get("current", {})
    tod = w.get("today", {})
    print("\n" + "-"*65)
    print("  WEATHER SUMMARY")
    print("-"*65)
    print(f"  Current temp : {cur.get('temperature')} C  (feels {cur.get('feels_like')} C)")
    print(f"  Today max/min: {tod.get('max')} C / {tod.get('min')} C")
    print(f"  Humidity     : {cur.get('humidity')}%")
    print(f"  Condition    : {cur.get('condition')}")
    print(f"  Heat level   : {cur.get('heat_level', {}).get('label')}")

    # ── UHI summary ────────────────────────────────────────────────────────
    u = result.get("uhi", {})
    zone = u.get("user_zone", {})
    top_hot = u.get("top_hotspots", [{}])
    print("\n" + "-"*65)
    print("  URBAN HEAT ISLAND ANALYSIS")
    print("-"*65)
    print(f"  Your area UHI  : +{zone.get('uhi_delta', 0):.1f} C above rural baseline")
    print(f"  Your area risk : {zone.get('risk', 'N/A')}")
    print(f"  City avg UHI   : +{u.get('city_uhi_summary', {}).get('avg_delta', 0):.1f} C")
    print(f"  Hottest zone   : {top_hot[0].get('name', 'N/A') if top_hot else 'N/A'} (+{top_hot[0].get('uhi_delta', 0):.1f} C)")

    # ── Immediate actions ──────────────────────────────────────────────────
    p = result.get("plan", {})
    immediate = p.get("immediate_actions", [])
    print("\n" + "-"*65)
    print("  DO THESE RIGHT NOW")
    print("-"*65)
    for i, action in enumerate(immediate[:6], 1):
        print(f"  {i}. {action}")

    # ── Energy savings ─────────────────────────────────────────────────────
    savings = p.get("energy_savings", {})
    print("\n" + "-"*65)
    print("  POTENTIAL SAVINGS")
    print("-"*65)
    print(f"  Energy saved  : {savings.get('saving_pct', 0):.0f}% reduction")
    print(f"  Monthly saving: {savings.get('saved_inr_per_month', 0):.0f} INR")
    print(f"  CO2 offset    : {savings.get('co2_saved_kg_month', 0):.1f} kg/month")

    # ── Simulation ─────────────────────────────────────────────────────────
    sim = p.get("simulation", {})
    if sim:
        print("\n" + "-"*65)
        print("  SIMULATION: IF YOU APPLY TOP 3 ACTIONS")
        print("-"*65)
        print(f"  Current temp  : {sim['current_temp']} C")
        print(f"  After actions : {sim['simulated_temp']} C  (-{sim['total_reduction']} C)")
        for a in sim.get("top_3_actions", []):
            print(f"    -> {a}")

    print("\n" + "="*65)
    print("  Full results also saved to: coolcity_result.json")
    print("  Run 'python main.py' (without --demo) for the web UI")
    print("="*65 + "\n")

    # Save full JSON result
    with open("coolcity_result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI web server."""
    try:
        import uvicorn
    except ImportError:
        print("Installing uvicorn...")
        os.system("pip install uvicorn fastapi --break-system-packages -q")
        import uvicorn

    print("\n" + "="*60)
    print("  CoolCity AI - Web Server Starting")
    print(f"  Open: http://localhost:{port}")
    print(f"  API docs: http://localhost:{port}/docs")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")

    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(description="CoolCity AI - Beat the 2026 Heatwave")
    parser.add_argument("--demo",     action="store_true", help="Run CLI demo (no server)")
    parser.add_argument("--city",     default="Bengaluru",  help="City name")
    parser.add_argument("--area",     default="Koramangala",help="Neighbourhood/area")
    parser.add_argument("--building", default="apartment",  help="Building type")
    parser.add_argument("--no-ac",    action="store_true",  help="No AC available")
    parser.add_argument("--floor",    type=int, default=4,  help="Floor number")
    parser.add_argument("--facing",   default="south",      help="Window direction")
    parser.add_argument("--host",     default="0.0.0.0",    help="Server host")
    parser.add_argument("--port",     type=int, default=8000, help="Server port")
    args = parser.parse_args()

    if args.demo:
        run_demo(
            city=args.city,
            area=args.area,
            building=args.building,
            has_ac=not args.no_ac,
            floor=args.floor,
            facing=args.facing,
        )
    else:
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
