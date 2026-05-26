---
name: embabel-instructions
description: "Guidance for working with the Embabel travel agent demo. Use when: building multi-tool orchestration agents, integrating external APIs (maps, weather, bookings), understanding complex agent coordination, extending travel planning capabilities."
applyTo: "embabel/**"
---

# Embabel Travel Agent - Developer Guide

The Embabel demo showcases the most complex MCP ecosystem in compose-for-agents, with 7+ integrated tools for travel planning.

## Quick Start

```bash
cd embabel
cp mcp.env.example .mcp.env
# Add API keys for: GOOGLE_MAPS_API_KEY, WEATHER_API_KEY, AIRBNB_API_KEY, BRAVE_API_KEY
docker compose up --build
# Open http://localhost:8080
```

## Architecture

**Multi-agent travel planner with centralized MCP gateway:**

```
User Query (e.g., "Plan a week in Tokyo")
    ↓
Root Agent (Trip Coordinator)
    ├─ Research Agent (Brave search for destinations)
    ├─ Weather Agent (Weather API for conditions)
    ├─ Location Agent (Google Maps for attractions)
    ├─ Booking Agent (Airbnb, flight APIs)
    └─ Budget Agent (Cost aggregation & optimization)
    ↓
MCP Gateway (Central routing)
    ├─ Brave Search (destination research)
    ├─ Google Maps (attractions, directions)
    ├─ Weather API (forecasts)
    ├─ Airbnb MCP (accommodation)
    ├─ Wikipedia (reference info)
    ├─ GitHub API (possibly for travel guides)
    └─ Custom REST APIs (flights, hotels)
    ↓
Final Itinerary (JSON + recommendations)
```

## Key Differentiators

1. **Widest MCP Ecosystem**: 7+ external data sources
2. **Dynamic Tool Selection**: Agents choose which tools based on query
3. **Real-time API Integration**: Live pricing, weather, availability
4. **Complex Orchestration**: Sequential + parallel agent execution
5. **Cost Optimization**: Multi-option comparison (flights, hotels, tours)

## Key Files

| File | Purpose | Key Components |
|------|---------|-----------------|
| `agent.py` | Root agent orchestration | Trip routing, agent delegation |
| `agents/research_agent.py` | Destination research | Brave search, Wikipedia lookups |
| `agents/location_agent.py` | Venue & route planning | Google Maps integration |
| `agents/weather_agent.py` | Climate forecasting | Weather API queries |
| `agents/booking_agent.py` | Accommodation/transport | Airbnb, flight, hotel APIs |
| `agents/budget_agent.py` | Cost analysis | Price aggregation, comparisons |
| `compose.yaml` | Service orchestration | All MCP servers + agent |
| `pyproject.toml` | Dependencies | litellm, adk, requests, pydantic |

## MCP Server Integration Map

```yaml
# compose.yaml command section
--servers=brave,google-maps,weather,airbnb,wikipedia,github,resend
--tools=search,nearby,directions,forecast,search_listings,search,get_repo,send_email
```

### Tool Availability by Agent

| Agent | Tools Used | API Keys Needed |
|-------|-----------|-----------------|
| Research | brave, wikipedia, github | BRAVE_API_KEY |
| Location | google-maps, brave | GOOGLE_MAPS_API_KEY |
| Weather | weather | WEATHER_API_KEY |
| Booking | airbnb (custom), stripe (payments) | AIRBNB_API_KEY |
| Budget | All (for cost comparison) | All of above |

## Adding a New Travel Data Source

### Example: Add Hotel Booking Tool

#### Step 1: Add MCP Server to Compose

```yaml
# compose.yaml
mcp-gateway:
  command:
    - --servers=brave,google-maps,weather,airbnb,wikipedia,hotels-api
    - --secrets=/run/secrets/mcp_secret
```

#### Step 2: Add API Secret

```env
# .mcp.env
HOTELS_API_KEY=your_key_here
```

#### Step 3: Create Agent Module

```bash
# agents/hotels_agent.py
from adk import Agent

class HotelsAgent(Agent):
    def __init__(self):
        super().__init__(name="hotels")

    async def search_hotels(self, city: str, dates: tuple, budget: float):
        # Call MCP tool
        results = await self.call_tool(
            "mcp/hotels-api:search",
            {
                "city": city,
                "check_in": dates[0],
                "check_out": dates[1],
                "max_price": budget
            }
        )
        # Process and rank results
        return self.rank_by_rating_and_price(results)
```

#### Step 4: Integrate into Root Agent

```python
# agent.py
from agents.hotels_agent import HotelsAgent

class RootAgent:
    def __init__(self):
        self.hotels_agent = HotelsAgent()
        # Register in agent list
        self.agents.append(self.hotels_agent)
```

#### Step 5: Update Routing

```python
async def plan_trip(self, user_query):
    trip_details = self.parse_query(user_query)
    
    # Parallel execution
    research = await self.research_agent.search(trip_details)
    weather = await self.weather_agent.forecast(trip_details)
    locations = await self.location_agent.find_venues(trip_details)
    hotels = await self.hotels_agent.search_hotels(...)  # NEW
    
    # Aggregate results
    return self.aggregate_itinerary([research, weather, locations, hotels])
```

## Pattern: Parallel vs. Sequential Execution

### Sequential (Default)

```python
# Agents wait for each previous one
research = await self.research_agent.execute()      # Starts first
locations = await self.location_agent.execute()    # Waits for research
booking = await self.booking_agent.execute()       # Waits for locations
```

**Use when:** Output of one agent feeds into the next

### Parallel (Faster)

```python
# Multiple agents run simultaneously
import asyncio
results = await asyncio.gather(
    self.research_agent.execute(),
    self.weather_agent.execute(),
    self.location_agent.execute(),
    # All start at once, return when all complete
)
```

**Use when:** Agents are independent (e.g., weather and research don't depend on each other)

## Handling Multi-Result Options

Embabel specializes in showing users multiple options and optimizing:

```python
# Booking Agent Pattern: Multiple flight options
flights = await self.call_tool("mcp/airlines:search", query)
# flights = [
#   {"airline": "AA", "price": 500, "duration": 8},
#   {"airline": "UA", "price": 480, "duration": 9},
#   {"airline": "BA", "price": 600, "duration": 7},
# ]

# Budget Agent: Sort and rank
ranked = self.budget_agent.rank_by_cost_and_time(flights)
# Present user with multiple options
```

## Cost Optimization Pattern

```python
# Budget agent aggregates across all services
def calculate_trip_cost(self, itinerary):
    total = 0
    breakdown = {}
    
    for component in ["flights", "hotels", "attractions", "food"]:
        cost = await self.get_cost(component)
        breakdown[component] = cost
        total += cost
    
    # Find cost-saving opportunities
    savings = self.find_optimizations(itinerary)
    
    return {
        "total": total,
        "breakdown": breakdown,
        "savings_opportunities": savings
    }
```

## Real-Time API Handling

### Caching Pattern (Avoid Rate Limits)

```python
# Cache Google Maps results for 1 hour
@cache(ttl=3600)
async def get_nearby_attractions(self, location):
    return await self.call_tool(
        "mcp/google-maps:nearby",
        {"location": location, "type": "tourist_attraction"}
    )
```

### Timeout Handling

```python
# If external API slow, use cached or fallback
async def search_flights_with_fallback(self, criteria):
    try:
        result = await asyncio.wait_for(
            self.call_tool("mcp/airlines:search", criteria),
            timeout=5  # 5 second timeout
        )
        return result
    except asyncio.TimeoutError:
        # Return cached results or recommendation-based fallback
        return self.get_cached_similar_flights(criteria)
```

## Debugging Multi-Tool Workflows

### View Tool Calls in Order

```bash
# Enable trace logging
export DEBUG=true
export LOG_LEVEL=DEBUG
docker compose up agent-service

# Follow MCP gateway logs
docker compose logs -f mcp-gateway | grep -E "tool|execute"
```

### Test Individual Agents

```bash
docker compose exec agent-service python -i
>>> from agents.research_agent import ResearchAgent
>>> agent = ResearchAgent()
>>> result = await agent.search("Best restaurants in Paris")
>>> print(result)
```

### Validate All MCP Servers Running

```bash
curl http://localhost:8811/tools | jq '.[] | .name'

# Expected output:
# brave
# google-maps
# weather
# airbnb
# wikipedia
# github
# resend
```

## Testing Scenarios

### Test Case 1: Full Trip Planning

```python
# agents/tests/test_trip_planning.py
async def test_complete_trip():
    agent = RootAgent()
    result = await agent.plan_trip({
        "destination": "Tokyo",
        "dates": ("2026-06-01", "2026-06-08"),
        "budget": 3000,
        "interests": ["food", "culture", "nightlife"]
    })
    
    assert result["flights"] is not None
    assert result["hotels"] is not None
    assert result["attractions"] is not None
    assert result["total_cost"] <= 3000
```

### Test Case 2: Individual Agent

```python
async def test_weather_agent():
    agent = WeatherAgent()
    forecast = await agent.forecast("Tokyo", "2026-06-01")
    
    assert "temperature" in forecast
    assert "precipitation" in forecast
    assert len(forecast["daily"]) == 7  # 7-day forecast
```

### Test Case 3: Cost Optimization

```python
async def test_budget_ranking():
    agent = BudgetAgent()
    flights = [
        {"price": 500, "duration": 8},
        {"price": 400, "duration": 10},
        {"price": 600, "duration": 7},
    ]
    
    ranked = agent.rank_by_cost_and_time(flights)
    assert ranked[0]["price"] == 400  # Cheapest first (configurable)
```

## Performance Optimization

### Parallel Tool Calls

```python
# Instead of sequential:
search1 = await self.call_tool("tool1", q1)  # Wait
search2 = await self.call_tool("tool2", q2)  # Then wait

# Use asyncio.gather:
search1, search2 = await asyncio.gather(
    self.call_tool("tool1", q1),
    self.call_tool("tool2", q2),
    # Both start immediately
)
```

### Response Streaming

```python
# For long-running queries, stream results
async def stream_itinerary_generation(self, trip_details):
    yield {"status": "Researching destinations..."}
    research = await self.research_agent.execute()
    
    yield {"status": "Checking weather...", "research": research}
    weather = await self.weather_agent.execute()
    
    # Continue streaming updates
```

## Common Issues

### Issue: API Rate Limiting

**Symptom:** `429 Too Many Requests` errors

**Solution:**
```python
# Add exponential backoff
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=2, max=60))
async def call_api_with_retry(self, tool, query):
    return await self.call_tool(tool, query)
```

### Issue: Timeout on Slow APIs

**Symptom:** Agent hangs waiting for response

**Solution:**
```python
# Set timeout + fallback
result = await asyncio.wait_for(
    self.call_tool(...),
    timeout=10  # seconds
)
```

### Issue: Inconsistent Results Across Multiple Calls

**Symptom:** Same query returns different prices/availability

**Solution:**
```python
# Cache for session
class EmbabelAgent:
    def __init__(self):
        self.session_cache = {}  # Keep for duration of trip planning
```

## Deployment

### Production Setup

```bash
# Use OpenAI models for reliability
docker compose -f compose.yaml -f compose.openai.yaml up --build

# Set production secrets
export OPENAI_API_KEY=sk-prod-xxxxx
export GOOGLE_MAPS_API_KEY=AIza...
export WEATHER_API_KEY=...
```

### Scale Multiple Concurrent Plans

```yaml
# compose.yaml
services:
  agent-service:
    deploy:
      replicas: 3  # Handle 3 simultaneous trip plans
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
```

## Next Steps

- Add flight + hotel combo searching (save up to 30% vs. separate bookings)
- Implement user preference learning (remember past preferences)
- Add alternative transportation (trains, buses vs. flights)
- Create packing recommendation agent based on weather + activities
- Integrate travel insurance quote engine

---

**Related:** [Embabel GitHub](https://github.com/embabel/embabel-agent), [MCP Server Reference](../../AGENTS.md#mcp-server-ecosystem)
