"""
api/server.py – FastAPI REST Backend for CoolCity AI

Endpoints:
  POST /api/analyse          – Full pipeline (weather + UHI + plan + narrative)
  GET  /api/weather/{city}   – Quick weather check
  GET  /api/heatmap/{city}   – City UHI heat map
  GET  /api/cities           – List of supported cities
  GET  /api/health           – Health check
  GET  /                     – Serves the frontend HTML
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field, validator
except ImportError:
    print("Installing FastAPI...")
    os.system("pip install fastapi uvicorn pydantic --break-system-packages -q")
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

from agents.orchestrator import Orchestrator

# ─── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CoolCity AI",
    description="Multi-agent AI system to combat urban heat islands. Free & open-source.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()

# ─── Request/Response models ───────────────────────────────────────────────────
class AnalyseRequest(BaseModel):
    city:          str  = Field("Bengaluru",  description="City name (e.g. Bengaluru, Mumbai, Delhi)")
    area:          str  = Field("Koramangala",description="Neighbourhood or area within the city")
    building_type: str  = Field("apartment",  description="apartment | house | office | villa | hostel")
    has_ac:        bool = Field(True,         description="Does your home have AC?")
    floor_number:  int  = Field(3,            ge=1, le=50, description="Floor number (1 = ground)")
    facing:        str  = Field("south",      description="Main window direction: north|south|east|west|mixed")
    num_people:    int  = Field(3,            ge=1, le=30, description="Number of people in your home")
    area_sqft:     int  = Field(1000,         ge=100, le=20000, description="Home area in sq ft")

    @validator("building_type")
    def validate_building(cls, v):
        valid = ["apartment", "house", "office", "villa", "hostel", "hospital", "school"]
        if v.lower() not in valid:
            return "apartment"
        return v.lower()

    @validator("facing")
    def validate_facing(cls, v):
        valid = ["north", "south", "east", "west", "mixed"]
        return v.lower() if v.lower() in valid else "south"


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "CoolCity AI", "version": "1.0.0"}


@app.get("/api/cities")
async def list_cities():
    """Returns list of cities with rich zone data."""
    from agents.urban_heat_map import CITY_ZONE_DATA
    return {
        "cities": list(CITY_ZONE_DATA.keys()),
        "total": len(CITY_ZONE_DATA),
        "note": "Other Indian cities are supported with estimated data.",
    }


@app.post("/api/analyse")
async def analyse(req: AnalyseRequest):
    """
    Full multi-agent analysis: weather + UHI + cooling plan + narrative.
    This is the main endpoint for the web app.
    """
    try:
        result = orchestrator.analyse(
            city=req.city,
            area=req.area,
            building_type=req.building_type,
            has_ac=req.has_ac,
            floor_number=req.floor_number,
            facing=req.facing,
            num_people=req.num_people,
            area_sqft=req.area_sqft,
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/{city}")
async def get_weather(city: str, area: str = ""):
    """Quick weather check for a city."""
    result = orchestrator.quick_weather(city=city, area=area)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/heatmap/{city}")
async def get_heatmap(city: str, base_temp: float = 40.0):
    """Urban heat island map data for an entire city."""
    result = orchestrator.city_heat_map(city=city, base_temp=base_temp)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Serve frontend ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return HTMLResponse(content=frontend_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CoolCity AI Backend Running</h1><p>See /docs for API.</p>")


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("  🌡️  CoolCity AI Server starting...")
    print("  📡  API docs: http://localhost:8000/docs")
    print("  🌐  Web app:  http://localhost:8000")
    print("="*60 + "\n")
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
