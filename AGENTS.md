# Compose for Agents - AI Agent Developer Guide

> **Purpose:** This guide helps AI coding agents understand the compose-for-agents repository structure, conventions, and how to work effectively with the various agent framework demos.

## Quick Start

Each demo is self-contained. To run any demo:

```bash
cd <demo-directory>
cp mcp.env.example .mcp.env  # If it exists
docker compose up --build
```

Access the agent UI (typically on `localhost:8080` or as specified in each demo).

### Configuration Options

All demos support **three deployment modes**:

| Mode | File | Usage |
|------|------|-------|
| **Local Inference** | `compose.yaml` | Uses Docker Model Runner (GPU required) |
| **OpenAI Models** | `compose.yaml -f compose.openai.yaml` | Uses OpenAI API (requires API key in `secret.openai-api-key`) |
| **GPU Offload** | `compose.yaml -f compose.offload.yaml` | Offloads inference to remote GPU |

Example: `docker compose -f compose.yaml -f compose.openai.yaml up --build`

## Repository Structure

The repository contains **11 agent framework demos**, each showcasing different approaches to multi-agent coordination:

### Multi-Agent Orchestration (Coordinator Pattern)

- **[a2a](./a2a)** — A2A Fact Checker: Sequential agent coordination with DuckDuckGo search
- **[adk](./adk)** — Google ADK: Multi-agent fact checker with specialized roles
- **[agno](./agno)** — Agno Framework: GitHub issue summarization system
- **[crew-ai](./crew-ai)** — CrewAI: Marketing strategy agents with specialized crews
- **[adk-sock-shop](./adk-sock-shop)** — ADK Sock Store: E-commerce agent with product tools
- **[adk-cerebras](./adk-cerebras)** — ADK + Cerebras: Golang experts with remote inference

### Single-Agent with Tools (Direct MCP Integration)

- **[langgraph](./langgraph)** — LangGraph: SQL Agent for database queries
- **[spring-ai](./spring-ai)** — Spring AI: Brave search integration (Java)
- **[langchaingo](./langchaingo)** — LangChainGo: DuckDuckGo search (Go)
- **[embabel](./embabel)** — Embabel Travel Planner: Multi-tool orchestration

### Experimental/Specialized

- **[minions](./minions)** — Minions: Cost-efficient local-remote collaboration
- **[akka](./akka)** — Akka: Actor model-based agents (Java)
- **[vercel](./vercel)** — Vercel AI SDK: Chat UI mixing MCPs and models

## Common Architecture Pattern

All demos follow this architecture:

```
┌─────────────────────┐
│   Agent Service     │  (Python/Java/Go)
│  - Executes tasks   │
│  - Calls tools      │
└──────────┬──────────┘
           │ Tool calls
           ▼
┌─────────────────────┐
│   MCP Gateway       │  (docker/mcp-gateway:latest)
│  - Routes tools     │  Standard service port: 8811
│  - Security layer   │
└──────────┬──────────┘
           │ Tool access
           ▼
┌─────────────────────┐
│  MCP Servers        │  (duckduckgo, github, postgres, etc.)
│  - Tool execution   │
└─────────────────────┘
```

**Key insight:** The MCP Gateway is standardized across all demos — always use `docker/mcp-gateway:latest` as the central routing layer.

## Working with Docker Compose

### Essential Commands

```bash
# Build and run with automatic rebuilds
docker compose up --build

# View logs for specific service
docker compose logs -f agent-service

# Run specific compose configuration
docker compose -f compose.yaml -f compose.openai.yaml up --build

# Clean up (important when switching modes)
docker compose down -v
```

### Service Discovery

Services communicate using **service names as hostnames**:
- MCP Gateway: `http://mcp-gateway:8811/sse`
- Agent service: `http://agent-service:8080` (or demo-specific name)
- Database: `mongodb://mongodb-service:27017`

### Environment & Secrets

1. **Copy example file:** `cp mcp.env.example .mcp.env`
2. **Add API keys** (if OpenAI mode): Create `secret.openai-api-key` file with your key
3. **Docker secrets:** Compose files use `secrets:` section to mount `.mcp.env` into containers

## Configuration Patterns

Different frameworks use different approaches to define agents:

### Declarative YAML
- **Agno** (`agents.yaml`): YAML-defined agent hierarchies
- **A2A** (similar pattern): YAML-based agent orchestration

```yaml
agents:
  - name: coordinator
    type: orchestrator
    sub_agents: [critic, reviser]
```

### Programmatic Python
- **ADK** (`agents/agent.py`): Python classes with explicit tool configuration
- **CrewAI** (`agents/agent.py`): Framework-native crew definitions

```python
auditor = SequentialAgent(
    name="auditor",
    sub_agents=[critic, reviser],
    model=model
)
```

### Framework-Native
- **LangGraph**: StateGraph + nodes pattern
- **Spring AI**: Properties-based configuration
- **Go frameworks**: Struct-based configuration

## MCP Server Ecosystem

Common MCP servers available for integration:

| Server | Tools | Use Cases |
|--------|-------|-----------|
| `duckduckgo` | `search`, `search_news` | Web search, research |
| `github-official` | `search_repos`, `get_issue` | GitHub integration |
| `postgres` | `query`, `execute` | Database operations |
| `mongodb` | `find`, `insert`, `update` | NoSQL operations |
| `brave` | `search` | Web search alternative |
| `curl` | `get`, `post` | HTTP requests |
| `google-maps` | `nearby`, `directions` | Location services |
| `weather` | `current`, `forecast` | Weather data |
| `airbnb` | (custom tools) | Travel booking |
| `resend` | `send_email` | Email delivery |

### Configuring MCP Tools in Agents

Tools are registered via environment or code:

```yaml
# In compose.yaml for MCP Gateway
command:
  - --servers=duckduckgo,github-official,postgres
  - --tools=search,fetch_content,query
```

Or programmatically:
```python
toolsets = create_mcp_toolsets(["duckduckgo", "github-official"])
agent.register_tools(toolsets)
```

## Build & Development Workflow

### Common Build Commands

**Python demos:**
```bash
cd ./adk
pip install -e .  # Local development
python -m pytest  # Run tests
```

**Java demos (Spring AI, Akka):**
```bash
cd ./spring-ai
mvn clean package
mvn spring-boot:run
```

**Go demos:**
```bash
cd ./langchaingo
go build -o main ./cmd
./main
```

### Linting & Validation

```bash
# Markdown linting
task lint:markdown
task lint:markdown:fix

# YAML linting
task lint:yaml

# All checks
task lint
```

See [Taskfile.yaml](./Taskfile.yaml) for complete task definitions.

## Demo-Specific Notes

- **[adk-sock-shop](./adk-sock-shop)** — Start with [CLAUDE.md](./adk-sock-shop/CLAUDE.md) for detailed architecture
- **[agno](./agno)** — Has Next.js frontend; check [agent-ui](./agno/agent-ui) for frontend changes
- **[embabel](./embabel)** — Most complex MCP ecosystem; review compose.yaml for all server configs
- **[langgraph](./langgraph)** — Includes `postgres_url` file for database connection
- **[adk-cerebras](./adk-cerebras)** — Uses remote Cerebras inference; check for Cerebras API keys

## Troubleshooting

### Issue: Services can't communicate
**Solution:** Ensure Docker Compose is running and services are named correctly. Services use **service name as hostname** (not localhost). Example: `http://mcp-gateway:8811` not `http://localhost:8811`.

### Issue: Wrong Docker Desktop version
**Solution:** Upgrade to 4.43.0+ for Docker Model Runner support. Check: `docker --version`

### Issue: GPU not being used
**Solution:** 
1. Verify Docker has GPU access: `docker run --rm --gpus all nvidia-smi`
2. Use local `compose.yaml` (not OpenAI overlay)
3. Check demo's Dockerfile for GPU base image

### Issue: MCP secret errors
**Solution:** Create `.mcp.env` from `.mcp.env.example` before running. For OpenAI mode, also create `secret.openai-api-key` file.

### Issue: Port conflicts
**Solution:** Check what's running on port 8080/8811:
```bash
lsof -i :8080
docker compose down -v  # Clean stop
```

## Debugging Agents

### View Agent Logs
```bash
docker compose logs -f auditor-agent  # Follow logs
docker compose logs --tail=100 agent-service  # Last 100 lines
```

### Connect to Running Container
```bash
docker compose exec agent-service bash  # Python/generic
docker compose exec agent-service python -i  # Python REPL
```

### Inspect MCP Gateway Health
```bash
curl http://localhost:8811/health
docker compose logs -f mcp-gateway
```

## Contributing

When adding a new demo:

1. Create a directory: `mkdir <framework-name>`
2. Add Docker Compose files:
   - `compose.yaml` (local inference)
   - `compose.openai.yaml` (OpenAI overlay)
   - `compose.offload.yaml` (GPU offload overlay) — optional
3. Include `README.md` with:
   - Quick start instructions
   - Prerequisite secrets/keys
   - Architecture overview
4. Add agent configuration (YAML/Python/framework-native)
5. Update main [README.md](./README.md) table with new demo

## Key Insights for AI Agents

1. **Modularity First:** Each demo is isolated — changes in one don't affect others
2. **Composition over Monoliths:** Docker Compose orchestrates all services; agents focus on logic
3. **MCP as Standard Interface:** All tool access flows through MCP Gateway
4. **Provider Agnostic:** Local/OpenAI/Offload modes use same code
5. **Infrastructure as Configuration:** No code changes needed to switch deployment modes
6. **Secrets Handled Gracefully:** All services have fallback strategies (MCP secrets → Model Runner)

## Additional Resources

- [Docker MCP Gateway](https://github.com/docker/mcp-gateway) — MCP routing and security
- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io/) — MCP standards
- [Docker AI Documentation](https://docs.docker.com/ai/) — Docker Model Runner reference
- Individual demo READMEs — Framework-specific details

---

**Last updated:** May 2026 | **Frameworks covered:** 11+ | **MCP servers:** 10+
