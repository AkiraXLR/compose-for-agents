---
name: adk-sock-shop-instructions
description: "Guidance for working with the ADK Sock Store agent demo. Use when: understanding the architecture, adding new tools, modifying agent behavior, debugging the e-commerce workflow, extending product catalog integration."
applyTo: "adk-sock-shop/**"
---

# ADK Sock Store Agent - Developer Guide

Reference: [CLAUDE.md](../../adk-sock-shop/CLAUDE.md) for architectural details

## Quick Start

```bash
cd adk-sock-shop
cp mcp.env.example .mcp.env
docker compose up --build
# Open http://localhost:8080
```

## Architecture at a Glance

**Three-tier multi-agent system:**

```
Root Agent (SequentialAgent)
├── Shopping Agent (product browsing, recommendations)
├── Cart Agent (add/remove items, pricing)
└── Order Agent (checkout, payments)
```

**Key Components:**
- **Root**: Orchestrator at `agents/agent.py:22`
- **Agents**: `agents/sub_agents/shopping/`, `agents/sub_agents/cart/`, `agents/sub_agents/order/`
- **Tools**: `agents/tools.py` (product lookup, inventory, pricing)
- **Data**: MongoDB connection in `compose.yaml`
- **MCP Integration**: curl, brave, mongodb servers

## Data Flow

```
User Query
    ↓
Root Agent (auditor) identifies task type
    ↓
Delegates to:
├─ Shopping Agent (if browsing) → MCP: brave search, mongodb queries
├─ Cart Agent (if modifying cart) → Local: pricing logic
└─ Order Agent (if checkout) → MCP: curl API calls
    ↓
Agent returns JSON response
    ↓
Web UI renders result
```

## Key Files

| File | Purpose | Key Lines |
|------|---------|-----------|
| `agents/agent.py` | Root orchestrator | L22-L50 |
| `agents/sub_agents/shopping/agent.py` | Product browsing agent | L15-L45 |
| `agents/sub_agents/cart/agent.py` | Cart management agent | L8-L40 |
| `agents/sub_agents/order/agent.py` | Checkout orchestration | L12-L55 |
| `agents/tools.py` | MCP tool definitions | L1-L100 |
| `compose.yaml` | Services (mongodb, MCP gateway, agent) | L1-L60 |
| `pyproject.toml` | Dependencies (adk, pydantic, litellm) | L1-L25 |

## Adding a New Agent

Example: Adding a "Recommendations Agent"

### Step 1: Create Agent File

```bash
mkdir -p agents/sub_agents/recommendations
touch agents/sub_agents/recommendations/__init__.py
touch agents/sub_agents/recommendations/agent.py
```

### Step 2: Define Agent

```python
# agents/sub_agents/recommendations/agent.py
from adk import Agent, ToolCall

class RecommendationsAgent(Agent):
    def __init__(self):
        super().__init__(
            name="recommendations",
            description="Provides personalized product recommendations",
            model="qwen3",
        )
        self.tools = self.create_tools()

    def create_tools(self):
        # Use MCP tools: mongodb queries for user history
        # Use curl for external recommendation API
        return [
            "mcp/mongodb:find",  # Query purchase history
            "mcp/curl:get",      # Call recommendation API
        ]

    async def execute(self, user_id: str, category: str = None):
        # Logic here
        pass
```

### Step 3: Register in Root Agent

In `agents/agent.py`:

```python
from agents.sub_agents.recommendations.agent import RecommendationsAgent

class RootAgent(SequentialAgent):
    def __init__(self):
        self.recommendations_agent = RecommendationsAgent()
        # Add to sub_agents list
        self.sub_agents.append(self.recommendations_agent)
```

### Step 4: Add Routing Logic

In `agents/agent.py`, update the orchestrator:

```python
async def route_task(self, user_input):
    if "recommend" in user_input.lower():
        return await self.recommendations_agent.execute(...)
    elif "shopping" in user_input.lower():
        return await self.shopping_agent.execute(...)
    # ... other routes
```

## Adding New MCP Tools

### Step 1: Enable Server in Compose

In `compose.yaml`, update `mcp-gateway` service:

```yaml
mcp-gateway:
  image: docker/mcp-gateway:latest
  command:
    - --servers=mongodb,curl,brave,stripe  # Add 'stripe'
    - --secrets=/run/secrets/mcp_secret
```

### Step 2: Add Secret (if needed)

In `.mcp.env`:

```env
STRIPE_API_KEY=sk_test_xxxxx
```

### Step 3: Register Tool in Agent

In `agents/tools.py`:

```python
def create_mcp_toolsets():
    return {
        "mongodb": create_mongodb_tools(),
        "curl": create_curl_tools(),
        "stripe": create_stripe_tools(),  # NEW
    }
```

### Step 4: Use in Agent

```python
async def process_payment(self, amount, card_token):
    result = await self.call_tool(
        "mcp/stripe:create_charge",
        {"amount": amount, "token": card_token}
    )
    return result
```

## Common Patterns in This Demo

### Pattern 1: Sub-Agent Delegation

```python
# In root agent
async def execute(self, user_input):
    # Determine which agent should handle it
    if "cart" in user_input:
        return await self.cart_agent.execute(user_input)
    elif "order" in user_input:
        return await self.order_agent.execute(user_input)
```

### Pattern 2: Tool Chaining

```python
# In shopping agent - multiple tool calls in sequence
user_history = await self.call_tool("mcp/mongodb:find", {"collection": "users"})
recommendations = await self.call_tool("mcp/curl:get", {"url": "/api/recommendations"})
search_results = await self.call_tool("mcp/brave:search", {"query": search_term})
```

### Pattern 3: Error Handling

```python
try:
    result = await self.call_tool("mcp/mongodb:find", query)
except ToolExecutionError as e:
    # Fallback: try alternative data source
    result = await self.call_tool("mcp/curl:get", {"url": "/api/fallback"})
```

## Debugging

### View Agent Decision Process

```bash
# Enable debug logging
export DEBUG=true
docker compose up agent-service

# Or in code:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Agent Selection

```bash
# Check which agent handled the request
docker compose logs agent-service | grep "Routing to"
```

### Test Individual Tools

```bash
# Shell into container
docker compose exec agent-service bash

# Test MongoDB connection
python -c "
from agents.tools import create_mcp_toolsets
tools = create_mcp_toolsets()
print(tools['mongodb'].available_commands())
"
```

### Check MCP Gateway Status

```bash
curl http://localhost:8811/tools
# Should return list of registered tools
```

## Testing

### Run Unit Tests

```bash
cd adk-sock-shop
python -m pytest tests/ -v
```

### Test Agent Manually

```bash
docker compose exec agent-service python -i
>>> from agents.agent import RootAgent
>>> agent = RootAgent()
>>> result = agent.execute("Show me available shoes")
>>> print(result)
```

## Deployment Notes

### Production Considerations

1. **Database Backup**: MongoDB data in `compose.yaml` volume
   ```bash
   docker compose exec mongodb mongodump --out /backup
   ```

2. **Secret Management**: Store `.mcp.env` in secure vault, not version control
   ```bash
   git add .gitignore  # Ensure .mcp.env is ignored
   ```

3. **Model Selection**: Change model in `compose.yaml`
   ```yaml
   environment:
     - MODEL=qwen3  # or llama3.2, gemma3
   ```

4. **Scaling**: For multi-tenant, isolate MongoDB and MCP gateway:
   ```bash
   docker compose -f compose.yaml -f compose.gcloud.yaml up
   ```

## Modifying Agent Behavior

### Change Model

In `compose.yaml`:

```yaml
agent-service:
  environment:
    - MODEL=llama3.2  # From qwen3
```

### Adjust Tool Restrictions

In `agents/agent.py`:

```python
self.allowed_tools = [
    "mcp/mongodb:find",
    "mcp/curl:get",
    # Remove 'brave' to disable web search
]
```

### Add System Prompt

In `agents/agent.py`:

```python
self.system_prompt = """You are a helpful e-commerce assistant.
- Prioritize customer satisfaction
- Always verify inventory before confirming orders
- Never process payments without explicit confirmation
"""
```

## Common Issues

### MongoDB Connection Fails

```bash
# Check service is running
docker compose ps mongodb

# View logs
docker compose logs mongodb

# Test connection
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### MCP Tools Not Found

```bash
# Verify gateway has loaded tools
curl http://localhost:8811/tools | jq .

# Restart gateway
docker compose restart mcp-gateway
```

### Agent Crashes on Startup

```bash
# Check dependencies installed
docker compose exec agent-service pip list | grep -E "adk|pydantic"

# Run manually to see error
docker compose exec agent-service python -m agents.agent
```

## Next Steps

- Add persistence layer (cache frequently accessed products)
- Implement vector embeddings for semantic search
- Add payment fraud detection
- Create admin dashboard for inventory management
- Expand to multi-language support

---

**Related:** [CLAUDE.md](../../adk-sock-shop/CLAUDE.md), [adk-sock-shop README](../../adk-sock-shop/README.md)
