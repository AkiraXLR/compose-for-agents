# Compose-for-Agents: Architecture & Patterns Analysis

This document summarizes common patterns, configurations, and best practices across 11+ agent framework demonstrations in this repository.

## Executive Summary

The repository demonstrates a **standardized Docker Compose-based approach** for running AI agents with consistent patterns for:
- **MCP Integration**: All projects use `docker/mcp-gateway:latest` as a central service
- **Dual-Provider Support**: Every project supports both local (Docker Model Runner) and cloud (OpenAI) inference
- **Secret Management**: Flexible patterns for API keys (file-based, Docker MCP secrets, environment variables)
- **Multi-Agent Orchestration**: Sequential and team-based coordination patterns

---

## 1. Common Architectural Patterns

### Pattern A: Sequential Multi-Agent (Coordinator → Sub-agents)
**Used by**: A2A, ADK, ADK Sock Store, Agno, CrewAI

```
Coordinator Agent
  ├── Sub-Agent 1 (Critic)
  ├── Sub-Agent 2 (Reviser)
  └── Sub-Agent 3 (etc.)
```

**Characteristics**:
- Parent agent orchestrates workflow
- Sub-agents have specialized roles and tools
- Communication via HTTP endpoints or frameworks
- Example: **A2A Auditor** coordinates Critic (searches web) + Reviser (refines answer)

**Framework specifics**:
- **A2A**: Uses A2A SDK with YAML config
- **ADK**: Uses Google ADK with Python or YAML
- **Agno**: Uses teams with coordinator mode
- **CrewAI**: Explicit crew definition with agents + tasks

---

### Pattern B: Single-Agent with Tools
**Used by**: LangGraph, LangChainGo, Spring AI, Embabel

```
Agent → MCP Gateway → Tool (Search, DB Query, etc.)
```

**Characteristics**:
- Direct tool access via MCP Gateway
- Simpler orchestration
- Better for single-purpose applications

---

### Pattern C: Multi-Framework Hybrid
**Used by**: ADK Sock Store, Embabel

```
Microservice Architecture:
  ├── Vendor App (UI)
  ├── Agent Portal
  ├── External Services (MongoDB, etc.)
  └── MCP Gateway (central)
```

---

## 2. Docker Compose Configuration Patterns

### Core Pattern: Three-Part Structure

#### Part 1: Agent Services
```yaml
services:
  agent:
    build:
      context: .           # Local Dockerfile
      target: agent        # Multi-stage target
    ports:
      - 8080:8080         # Web UI typically on 8080
    environment:
      - MCPGATEWAY_ENDPOINT=http://mcp-gateway:8811/sse
      - MODEL_RUNNER_MODEL=ai/qwen3:14B-Q6_K
    depends_on:
      - mcp-gateway
      - [other-services]
    volumes:
      - ./agents.yaml:/agents.yaml  # Config override
```

#### Part 2: MCP Gateway (Universal)
```yaml
  mcp-gateway:
    image: docker/mcp-gateway:latest
    use_api_socket: true              # Docker manages secrets
    ports:
      - 8811:8811                     # Default MCP port
    command:
      - --transport=sse               # HTTP-based transport
      - --servers=duckduckgo          # CSV list of MCP servers
      - --tools=search,fetch_content  # Tool filtering
      - --secrets=/run/secrets/db_url # Pass secrets to gateway
```

#### Part 3: Model Configuration (Docker Model Runner)
```yaml
models:
  qwen3:
    model: ai/qwen3:14B-Q6_K          # GGUF model identifier
    context_size: 15000               # Token context limit
    runtime_flags:
      - --no-prefill-assistant
```

### Composition Variants

| File | Purpose | Usage |
|------|---------|-------|
| `compose.yaml` | Base orchestration | `docker compose up` |
| `compose.openai.yaml` | OpenAI provider override | `docker compose -f compose.yaml -f compose.openai.yaml up` |
| `compose.offload.yaml` | GPU offload (remote) | Combined with above for remote execution |
| `compose.dmr.yaml` | Docker Model Runner specific | Alternative to base compose |
| `compose.gcloudrun.yaml` | Google Cloud Run deployment | Cloud-specific configuration |

**Overlay Pattern**: The `-f` flag allows composing multiple files, with later files overriding earlier ones.

---

## 3. Build & Test Commands

### Universal Commands (All Projects)
```bash
# Standard: Local with Docker Model Runner
docker compose up --build

# With OpenAI
docker compose -f compose.yaml -f compose.openai.yaml up --build

# With GPU Offload
docker compose -f compose.yaml -f compose.offload.yaml up --build

# Cleanup (removes volumes)
docker compose down -v
```

### Project-Specific Commands

**A2A, ADK, CrewAI**:
```bash
# Setup: Create secret file
echo "sk-..." > secret.openai-api-key

# Run with MCP secrets
docker mcp secret set 'brave.api_key=YOUR_KEY'
docker mcp secret export brave > .mcp.env
```

**ADK Sock Store** (Makefile):
```bash
make gateway-secrets          # Setup all MCP secrets
make local-up                 # Compose up locally
make offload-up               # Compose up with GPU offload
```

**Repository Root** (Task runner):
```bash
task lint:markdown
task lint:yaml
```

---

## 4. Environment Setup Patterns

### Secret Management: Three Approaches

**Approach 1: File-based (Most Common)**
```bash
# Create file
echo "sk-..." > secret.openai-api-key

# Reference in compose.yaml
secrets:
  openai-api-key:
    file: secret.openai-api-key

# Access in container
export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
```

**Approach 2: Docker MCP Secrets (Advanced)**
```bash
# Set secrets
docker mcp secret set 'brave.api_key=YOUR_KEY'
docker mcp secret set 'mongodb.connection_string=mongodb://user:pass@host/db'

# Export to environment file
docker mcp secret export brave mongodb > .mcp.env

# Pass to gateway
command:
  - --secrets=/run/secrets/mcp_secret
```

**Approach 3: Direct Environment Variables**
```bash
export OPENAI_API_KEY=sk-...
export MODEL_RUNNER_URL=http://localhost:12434
docker compose up
```

### Runtime Configuration Pattern (Dockerfiles)

**All projects follow this entrypoint pattern:**

```bash
#!/bin/sh
# 1. Check for OpenAI API key (takes precedence)
if test -f /run/secrets/openai-api-key; then
    export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
    export LLM_PROVIDER=openai
    export MODEL_NAME=${OPENAI_MODEL_NAME}
else
    # 2. Fall back to Docker Model Runner
    export OPENAI_BASE_URL=${MODEL_RUNNER_URL}
    export MODEL_NAME=${MODEL_RUNNER_MODEL}
    export OPENAI_API_KEY=cannot_be_empty  # Placeholder
fi

exec python main.py
```

### Environment Variables Reference

**MCP Gateway Communication**:
```
MCPGATEWAY_ENDPOINT=http://mcp-gateway:8811/sse  # SSE transport
MCPGATEWAY_URL=http://mcp-gateway:8811           # Streaming transport
```

**Model Configuration**:
```
MODEL_RUNNER_URL=http://mcp-gateway:8811         # Local models endpoint
MODEL_RUNNER_MODEL=ai/qwen3:14B-Q6_K             # Model identifier
OPENAI_MODEL_NAME=gpt-4o                          # For OpenAI
OPENAI_API_KEY=sk-...                             # OpenAI credential
```

**Application-Specific**:
```
DATABASE_URL=postgres://user:pass@host/db        # Database URL
SPRING_PROFILES_ACTIVE=prod                       # Spring environment
QUESTION="What is X?"                             # Initial query
```

---

## 5. Configuration File Patterns

### Configuration Format 1: Declarative YAML (agents.yaml)

**Used by**: Agno, A2A sub-agents, ADK

```yaml
agents:
  github-retriever:
    name: "Github Issue Retriever"
    description: "Retrieves open issues from a GitHub repository"
    instructions: |
      Given a repository <owner>/<repo>:
      1. Retrieve all open issues
      2. Include title, number, and labels
      3. Return as CSV format
      
      Omit pull requests.
    tools:
      - mcp/github-mcp-server:list_issues  # Format: mcp/server:tool
    model:
      name: ${MODEL_NAME}                   # Template variables from env
      provider: ${MODEL_PROVIDER}

teams:
  coordinator:
    name: "Coordinator"
    mode: coordinate                        # Mode: "coordinate" or "sequential"
    members: [github-retriever, writer]
    instructions: |
      Coordinate the following workflow...
    model:
      name: ${MODEL_NAME}
      provider: ${MODEL_PROVIDER}
```

---

### Configuration Format 2: Programmatic Python (agent.py)

**Used by**: ADK, Google ADK, LangGraph

```python
from google.adk.agents import SequentialAgent

# Define sub-agents
critic_agent = Agent(
    name="critic",
    description="Gathers evidence from web",
    tools=[mcp_tool("duckduckgo", "search")]
)

reviser_agent = Agent(
    name="reviser",
    description="Refines conclusions"
)

# Compose orchestration
auditor_agent = SequentialAgent(
    name="auditor",
    description="Coordinates fact-checking",
    sub_agents=[critic_agent, reviser_agent]
)

root_agent = auditor_agent
```

---

### Configuration Format 3: CrewAI Explicit Team Definition

```python
# agents.py
lead_analyst = Agent(
    role="Market Research Lead",
    goal="Research market trends",
    tools=[search_tool, web_scraper],
    llm=llm
)

# tasks.py
market_research_task = Task(
    description="Research competitive landscape",
    agent=lead_analyst,
    expected_output="Market analysis report"
)

# crew.py
crew = Crew(
    agents=[lead_analyst, strategist, creator],
    tasks=[market_research_task, strategy_task, creation_task],
    verbose=True
)
```

---

### Configuration Format 4: Spring AI Properties

```properties
# application.yaml
spring.ai.openai.api-key=${OPENAI_API_KEY}
spring.ai.openai.base-url=${OPENAI_BASE_URL}
spring.ai.openai.chat.options.model=${OPENAI_MODEL_NAME}

server.port=8080
spring.profiles.active=prod
```

---

## 6. Dockerfile Patterns by Language

### Python: Multi-Stage with UV Package Manager

**Pattern used by**: A2A, ADK, LangGraph

```dockerfile
# Stage 1: Base runtime
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install uv

WORKDIR /app

# Cache dependencies by copying only metadata first
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    uv sync --locked --no-dev --no-install-project

# Copy application
COPY main.py src ./
RUN python -m compileall -q .

# Dynamic entrypoint script (inlined)
COPY <<EOF ./entrypoint.sh
#!/bin/sh
set -e
if test -f /run/secrets/openai-api-key; then
    export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
    export LLM_PROVIDER=openai
else
    export OPENAI_BASE_URL=${MODEL_RUNNER_URL}
    export OPENAI_API_KEY=cannot_be_empty
fi
exec python main.py --host 0.0.0.0 --port 8080
EOF
RUN chmod +x ./entrypoint.sh

# Non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Stage 2: Specific agent targets
FROM base AS critic-agent
COPY agents/critic.yaml /app/agent.yaml
ENTRYPOINT ["./entrypoint.sh"]
```

**Key aspects**:
- `uv sync --locked`: Reproducible dependency installation
- Multi-stage builds for different agent roles
- Inline entrypoint script for runtime flexibility
- Non-root user for security

---

### Python: Poetry-Based (CrewAI)

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-root

COPY . .
RUN poetry install

COPY <<EOF /entrypoint.sh
#!/bin/sh
if test -f /run/secrets/openai-api-key; then
    export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
else
    export OPENAI_BASE_URL=${MODEL_RUNNER_URL}
    export OPENAI_API_KEY=cannot_be_empty
fi
exec poetry run marketing_posts
EOF

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

---

### Java: Maven Multi-Stage (Spring AI)

```dockerfile
# Stage 1: Build
FROM eclipse-temurin:17-jdk AS builder

WORKDIR /build
COPY pom.xml .mvn mvnw ./
RUN ./mvnw dependency:go-offline -B

COPY src ./src
RUN ./mvnw package -DskipTests -B

# Stage 2: Runtime
FROM eclipse-temurin:17-jre AS app

WORKDIR /app
COPY --from=builder /build/target/*.jar app.jar

COPY <<EOF entrypoint.sh
#!/bin/sh
if test -f /run/secrets/openai-api-key; then
    export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
else
    export OPENAI_BASE_URL=${MODEL_RUNNER_URL}
    export OPENAI_MODEL_NAME=${MODEL_RUNNER_MODEL}
    export OPENAI_API_KEY=cannot_be_empty
fi
# Spring AI uses base URL without /v1
export OPENAI_BASE_URL=${OPENAI_BASE_URL%/v1}
exec java -jar app.jar
EOF

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
```

---

### Go: Static Build (LangChainGo)

```dockerfile
# Stage 1: Build
FROM golang:1.24.1-alpine AS builder

WORKDIR /build
RUN apk --no-cache add ca-certificates

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo \
    -ldflags '-extldflags "-static"' -tags timetzdata -o app .

# Stage 2: Runtime
FROM alpine:3.19 AS app

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app
COPY --from=builder /build/app app

COPY <<EOF entrypoint.sh
#!/bin/sh
if test -f /run/secrets/openai-api-key; then
    export OPENAI_API_KEY=$(cat /run/secrets/openai-api-key)
else
    export OPENAI_BASE_URL=${MODEL_RUNNER_URL}
    export OPENAI_MODEL_NAME=${MODEL_RUNNER_MODEL}
    export OPENAI_API_KEY=cannot_be_empty
fi
exec ./app
EOF

RUN chmod +x entrypoint.sh
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
RUN chown -R appuser:appgroup /app
USER appuser

ENTRYPOINT ["./entrypoint.sh"]
```

---

## 7. MCP Server Integration

### Supported MCP Servers

| Server | Tools | Use Cases |
|--------|-------|-----------|
| `duckduckgo` | search, fetch_content | Web search, information gathering |
| `github-official` | list_issues, list_prs, search_repos | GitHub data access |
| `postgres` | query | Database operations (SQL) |
| `brave` | search, fetch_content | Brave Search (requires API key) |
| `google-maps` | search_places, get_place_details | Maps and location data |
| `wikipedia-mcp` | search, read_article | Wikipedia access |
| `weather` | get_weather | Weather data |
| `mongodb` | query_collection, insert, update | MongoDB operations |
| `resend` | send_email | Email sending |
| `curl` | execute | Raw HTTP requests |
| `airbnb` | search_listings | Airbnb integration |

### Gateway Tool Filtering

```yaml
mcp-gateway:
  command:
    - --servers=duckduckgo,github-official
    - --tools=search,fetch_content,list_issues  # Whitelist specific tools
```

### Transport Options

```yaml
# SSE: HTTP-based, works with browser clients
--transport=sse
# Endpoint: http://mcp-gateway:8811/sse

# Streaming: Native streaming protocol, higher performance
--transport=streaming
# Endpoint: http://mcp-gateway:8811
```

---

## 8. Directory Structure & Naming Conventions

### Standard Project Layout

```
project-root/
├── compose.yaml                    # Main orchestration
├── compose.openai.yaml             # Optional: OpenAI variant
├── compose.offload.yaml            # Optional: GPU offload
├── Dockerfile                      # Container image
├── [pyproject.toml|pom.xml|go.mod] # Dependencies
├── README.md                       # Setup instructions
├── agents/
│   ├── agent.py                   # Agent definition
│   ├── agent.yaml                 # Agent configuration
│   ├── sub_agents/
│   │   ├── critic.yaml
│   │   ├── reviser.yaml
│   │   └── [sub-agent].py
│   └── tools.py                   # Custom tools
├── src/
│   ├── agent/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── agents.yaml
│   ├── agent-ui/                  # Frontend (if applicable)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── next.config.ts
│   └── [other-modules]/
├── data/
│   └── mongodb/                   # Data fixtures
├── secret.openai-api-key          # Git-ignored
└── postgres_url                   # Git-ignored
```

### Naming Conventions

**Service names** (kebab-case):
- `auditor-agent-a2a` (framework + role)
- `adk` (framework name)
- `agents` (generic)
- `mcp-gateway` (universal)

**Ports** (conventional):
- `8080`: Main web UI / application
- `8001`: Sub-agent service
- `8811`: MCP Gateway
- `7777`: Agno agents service
- `9000`: Akka agent
- `3000`: Frontend UI (React)

**Environment variables** (SCREAMING_SNAKE_CASE):
- `MCPGATEWAY_ENDPOINT`
- `MODEL_RUNNER_URL`
- `OPENAI_API_KEY`
- `QUESTION` (input query)

**Agent names** (snake_case):
- In Python: `critic_agent`, `reviser_agent`
- In YAML: `github-retriever`, `market-analyst`

**MCP tool references**:
- Format: `mcp/server-name:tool_name`
- Example: `mcp/duckduckgo:search`
- Example: `mcp/github-mcp-server:list_issues`

---

## 9. Common Pitfalls & Troubleshooting

### Requirement Checklist

- [ ] Docker Desktop 4.43.0+ or Docker Engine with Compose 2.38.1+
- [ ] GPU support enabled (NVIDIA drivers for Linux, Apple Silicon native on Mac)
- [ ] Python 3.10+ (3.13 preferred for newer projects)
- [ ] 8GB+ VRAM for local models
- [ ] API keys for OpenAI / MCP services (if used)

### Common Issues

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Model fails to load | Insufficient VRAM or outdated Docker | Reduce context_size in compose.yaml; update Docker |
| MCP Gateway unreachable | Network isolation in compose | Check service dependencies and `use_api_socket: true` |
| Agent can't find database | Connection string errors | Verify hostname (service name in compose) and port |
| "cannot_be_empty" API key error | OpenAI mode fallback triggered | Verify `/run/secrets/openai-api-key` exists and is readable |
| Port already in use | Multiple projects running | Change port in compose.yaml or run `docker compose down` |
| Model runner URL incorrect | Missing MODEL_RUNNER_URL env | Set in compose.yaml environment section |
| Sub-agent communication fails | URL format error | Use `http://service-name:port` format |
| YAML parsing error | Invalid indentation/syntax | Use yamllint or validate in editor |

### Performance Tuning

**Context size trade-offs** (approximate VRAM usage):
```
8192 tokens    → ~4 GB
15000 tokens   → ~7 GB
41000 tokens   → ~13 GB
80000 tokens   → ~25 GB
131000 tokens  → ~35 GB
```

**Model selection by use case**:
- **Fast inference**: `qwen3:4B-Q4_0` (~2 GB)
- **Balanced**: `qwen3:8B-Q4_0` (~4 GB)
- **Quality**: `qwen3:14B-Q6_K` (~11 GB)
- **Specialized**: `gemma3`, `llama3.2` (various sizes)

---

## 10. Framework Comparison

| Framework | Strengths | Setup | Deployment |
|-----------|-----------|-------|-----------|
| **ADK** | Rich ecosystem, Google backing | Python/YAML config | Fast |
| **A2A** | Multi-agent coordination | Framework-native | Moderate |
| **Agno** | Team-based workflows | YAML + env vars | Straightforward |
| **CrewAI** | Task-based orchestration | Python crew definition | Python-focused |
| **LangGraph** | Graph-based workflows | Python + LangChain | Flexible |
| **Spring AI** | Java ecosystem integration | Maven/Spring config | JVM deployment |
| **LangChainGo** | Go language support | go.mod | Lightweight |
| **Embabel** | Multi-model support | Complex setup | Feature-rich |
| **Akka** | Scala/Java actor model | Maven + config | Distributed |

---

## 11. Key Takeaways

1. **Universal Pattern**: All projects follow compose → agent → MCP Gateway → tools architecture
2. **Flexibility**: Support for multiple inference providers (local, OpenAI, custom)
3. **Security**: Secrets managed via Docker or file-based system
4. **Scalability**: Multi-agent orchestration via sequential or team patterns
5. **Language Agnostic**: Python, Java, Go examples all use same Docker Compose pattern
6. **Configuration-Driven**: Minimal code changes needed to swap models, MCPs, or providers

---

## Quick Start Template

```bash
# 1. Clone and enter project directory
cd [project-name]

# 2. Setup API key (if needed)
echo "sk-..." > secret.openai-api-key

# 3. Setup MCP secrets (if needed)
docker mcp secret set 'brave.api_key=YOUR_KEY'
docker mcp secret export brave > .mcp.env

# 4. Start with default (Docker Model Runner)
docker compose up --build

# OR start with OpenAI
docker compose -f compose.yaml -f compose.openai.yaml up --build

# 5. Access UI
# Usually: http://localhost:8080
# Check README.md for specific port
```

