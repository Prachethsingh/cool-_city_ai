# 🌡️ CoolCity AI — Multi-Agent AI System for the 2027 Heatwave

> **100% software. 100% free. Open-source. No hardware needed.**  
> Beat the 2026 heatwave with 4 coordinated AI agents that monitor, analyse, plan, and advise.

---

## 🏗️ Architecture: 4 AI Agents Working Together

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────┐
│              Orchestrator                        │
│  (coordinates all agents, caches results)        │
└────────┬──────────┬──────────┬──────────────────┘
         │          │          │
         ▼          ▼          ▼
  ┌──────────┐ ┌──────────┐ ┌──────────────────┐
  │ Weather  │ │   UHI    │ │ Cooling Planner  │
  │ Monitor  │ │   Map    │ │     Agent        │
  │  Agent   │ │  Agent   │ │                  │
  └──────────┘ └──────────┘ └──────────────────┘
      │             │               │
      └─────────────┴───────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │  User Assistant  │
          │     Agent        │
          │ (LLM narrative)  │
          └──────────────────┘
                    │
                    ▼
          Plain-language report
          + full structured data
```

### Agent Roles

| Agent | Role | Data Source | Free? |
|-------|------|-------------|-------|
| **WeatherMonitorAgent** | Real-time + 7-day weather | Open-Meteo API | ✅ Yes |
| **UrbanHeatMapAgent** | UHI analysis, zone hotspots | Built-in heuristics + open data | ✅ Yes |
| **CoolingPlannerAgent** | Personalised cooling plans, simulations | Rule-based + physics models | ✅ Yes |
| **UserAssistantAgent** | Narrative, orchestration | Anthropic Claude API | ✅ Free tier |

---

## 🚀 Getting Started (Manual Setup)

### 1. Environment Setup (Recommended)

It is highly recommended to use a virtual environment to avoid dependency conflicts.

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\activate
```

**macOS / Linux (Bash/Zsh):**
```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AI Narratives (Optional)

The system works fully offline/locally with rule-based fallbacks. To enable rich AI-generated cooling narratives, add your Anthropic API key:

```bash
# Create .env file (or add manually)
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

### 4. Run the System

#### A. Web Interface (Premium UI)
```bash
python main.py
```
Open [**http://localhost:8000**](http://localhost:8000) in your browser to access the Ethereal Frost dashboard and interactive thermal sandbox.

#### B. CLI Demo (Fast Terminal Analysis)
```bash
# Basic demo
python main.py --demo

# Specific query
python main.py --demo --city Mumbai --area Andheri --building apartment --no-ac
```

#### C. Run Tests
```bash
python tests/test_agents.py
# or
pytest tests/ -v
```

---

## 📁 Project Structure

```
cool_city_ai/
│
├── main.py                    # Entry point (web server or CLI demo)
│
├── agents/
│   ├── base_agent.py          # Abstract base class for all agents
│   ├── weather_monitor.py     # Agent 1: Weather (Open-Meteo API)
│   ├── urban_heat_map.py      # Agent 2: UHI analysis
│   ├── cooling_planner.py     # Agent 3: Personalised cooling plans
│   ├── user_assistant.py      # Agent 4: LLM narrative + orchestration
│   └── orchestrator.py        # Central coordinator
│
├── api/
│   └── server.py              # FastAPI REST backend
│
├── frontend/
│   └── index.html             # Web UI (dark theme, responsive)
│
├── config/
│   └── settings.py            # All configuration (no secrets)
│
├── utils/
│   └── helpers.py             # Geocoding, heat index, caching
│
├── tests/
│   └── test_agents.py         # Unit tests for all agents
│
├── requirements.txt
└── README.md
```

---

## 🌐 API Reference

### POST /api/analyse
Main endpoint. Returns full analysis.

```json
{
  "city": "Bengaluru",
  "area": "Koramangala",
  "building_type": "apartment",
  "has_ac": true,
  "floor_number": 4,
  "facing": "south",
  "num_people": 3,
  "area_sqft": 1000
}
```

**Response:**
```json
{
  "success": true,
  "weather": { "current": {...}, "today": {...}, "hourly_today": [...], "forecast_7day": [...] },
  "uhi": { "all_zones": [...], "user_zone": {...}, "interventions": [...] },
  "plan": { "daily_schedule": [...], "immediate_actions": [...], "energy_savings": {...} },
  "narrative": "Full AI-generated cooling advice text..."
}
```

### GET /api/weather/{city}
Quick weather check. Example: `/api/weather/Bengaluru?area=Koramangala`

### GET /api/heatmap/{city}
Full city UHI map. Example: `/api/heatmap/Mumbai?base_temp=40`

### GET /api/cities
Lists cities with rich zone data (Bengaluru, Mumbai, Delhi, Chennai, Hyderabad).

---

## 🧪 Running Tests

```bash
python tests/test_agents.py
# or
pytest tests/ -v
```

---

## 🌡️ How the UHI Analysis Works (No Hardware)

The **UrbanHeatMapAgent** uses:

1. **Surface type classification** — maps area names to surface types (dense concrete, asphalt, park, water, etc.) using keyword matching against a curated database of Indian cities
2. **Heat factor table** — each surface type has a known UHI contribution in °C (e.g., dense concrete = +4.5°C, parks = −1.0°C)
3. **Green cover adjustment** — more trees → lower UHI (parameterised per zone)
4. **Population density bonus** — more people = more heat from bodies, AC exhaust, vehicles
5. **Albedo model** — surface reflectivity affects how much solar radiation is absorbed vs reflected

This is validated against published UHI studies for Indian cities (Bengaluru UHI = 2–5°C, consistent with our model).

---

## 💡 Cooling Simulation

The planner simulates temperature reduction by combining:

| Intervention | Max reduction | Feasibility |
|---|---|---|
| Plant 3–5 trees near building | −1.5°C | Medium-term |
| Green/cool roof | −2.0°C | Long-term |
| White reflective roof paint | −1.0°C | Short-term |
| Cross-ventilation | −0.8°C | Immediate |
| Blackout/reflective curtains | −0.5°C | Immediate |
| AC at 24–26°C (pre-cool) | (energy savings) | Immediate |
| Wet cloth/evaporative cooling | −1.2°C | Immediate |
| Terrace/balcony garden | −1.8°C | Short-term |

---

## 🤝 Contributing

1. Fork the repo
2. Add a new city to `CITY_ZONE_DATA` in `agents/urban_heat_map.py`
3. Add new cooling interventions to `COOLING_INTERVENTIONS` in `config/settings.py`
4. Open a pull request

**Want to add a real satellite UHI data source?**  
See the TODO in `agents/urban_heat_map.py` — there's a hook for `geopandas`/`rasterio` integration.

---

## 📜 License

MIT License — use freely, modify, distribute. Built to help India survive the 2026 heatwave. 🇮🇳

---

## 🙏 Credits

- Weather data: [Open-Meteo](https://open-meteo.com/) (free, open-source)
- Geocoding: [Open-Meteo Geocoding](https://geocoding-api.open-meteo.com) + [Nominatim/OSM](https://nominatim.org)
- AI narratives: [Anthropic Claude](https://anthropic.com)
- UHI heuristics: Based on published research (Pathan et al. 2022, Ramaiah & Avtar 2021)
