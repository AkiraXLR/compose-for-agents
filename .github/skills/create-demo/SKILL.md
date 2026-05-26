---
name: create-demo
description: "Scaffold a new agent framework demo in compose-for-agents. Use when: adding a new framework, creating a demo template, scaffolding multi-agent or single-agent implementation, setting up Docker Compose for an agent framework."
---

# Create New Agent Framework Demo

This skill scaffolds a complete new agent demo in the compose-for-agents repository, following established conventions and architecture patterns.

## Workflow

### 1. Gather Requirements

Ask the following:
- **Framework name** (kebab-case): `langchain-js`, `anthropic-sdk`, etc.
- **Agent type**: Multi-agent orchestrator or Single-agent with tools?
- **Primary language**: Python, Java, Go, TypeScript, etc.
- **MCP tools needed**: Search (duckduckgo), GitHub, database, etc.
- **Use case**: What problem does this demo solve?
- **Target model**: Local (GPU required) or cloud-ready (OpenAI)?

### 2. Generate Scaffolding

Create the following structure:

```
<demo-name>/
├── compose.yaml              # Local inference (Docker Model Runner)
├── compose.openai.yaml       # OpenAI overlay (optional override)
├── compose.offload.yaml      # GPU offload overlay (optional)
├── Dockerfile                # Multi-stage build (Python/Java/Go pattern)
├── mcp.env.example           # Template for MCP secrets
├── README.md                 # Quick start + architecture
├── pyproject.toml / pom.xml / go.mod  # Dependency file
├── LICENSE                   # Dual-license: Apache-2.0 OR MIT
├── agents/
│   ├── __init__.py / Main.java / main.go
│   ├── agent.py / Agent.java  # Primary orchestrator
│   └── sub_agents/            # (Multi-agent only)
│       ├── specialist1/
│       └── specialist2/
└── src/ or src/main/         # (Python/Java) Implementation
```

### 3. Generate Files Using Templates

#### `compose.yaml` (Local Inference)

```yaml
version: "3"
services:
  agent-service:
    build: .
    ports:
      - "8080:8080"
    environment:
      - MODEL=qwen3  # or gemma3, llama3.2
      - MCP_GATEWAY_URL=http://mcp-gateway:8811/sse
    depends_on:
      - mcp-gateway
    command: ["/app/start.sh"]

  mcp-gateway:
    image: docker/mcp-gateway:latest
    ports:
      - "8811:8811"
    command:
      - --transport=sse
      - --servers=duckduckgo,github-official
    environment:
      - MCP_SECRETS_FILE=/run/secrets/mcp_secret
    secrets:
      - mcp_secret

secrets:
  mcp_secret:
    file: ./.mcp.env
```

#### `compose.openai.yaml` (Overlay)

```yaml
version: "3"
services:
  agent-service:
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
      - MODEL=gpt-4o
    secrets:
      - openai_api_key

secrets:
  openai_api_key:
    file: ./secret.openai-api-key
```

#### `Dockerfile` (Python Pattern)

```dockerfile
FROM python:3.11-slim as base
WORKDIR /app

# Install build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential curl && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency resolution
RUN pip install --no-cache-dir uv

COPY pyproject.toml pyproject.lock* ./
RUN uv pip install --system --no-cache -e .

COPY . .

FROM base
EXPOSE 8080
CMD ["python", "-m", "agent.main"]
```

#### `pyproject.toml` (Python)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "demo-<name>"
version = "0.1.0"
description = "Agent demo for <framework> framework"
dependencies = [
    "adk>=0.2.0",  # or anthropic, langgraph, etc.
    "litellm>=1.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest", "black", "ruff"]
```

#### `Dockerfile` (Java Pattern)

```dockerfile
FROM maven:3.9-openjdk-21 as builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY . .
RUN mvn clean package -DskipTests

FROM openjdk:21-slim
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
```

#### `go.mod` (Go)

```
module github.com/docker/compose-for-agents/<demo-name>

go 1.22

require (
	github.com/tmc/langchaingo v0.x.x
	github.com/duckduckgo/api v1.x.x
)
```

### 4. Update Root README

Add entry to the [README.md](../README.md) table:

```markdown
| [<Framework Name>](https://github.com/...) | Multi-Agent | qwen3(local) | duckduckgo | [./<demo-name>](./<demo-name>) | [compose.yaml](./<demo-name>/compose.yaml) |
```

### 5. Validate

- [ ] All YAML files pass linting: `task lint:yaml`
- [ ] Markdown passes linting: `task lint:markdown`
- [ ] `docker compose up --build` succeeds
- [ ] Agent UI accessible on `localhost:8080`
- [ ] MCP Gateway health check: `curl http://localhost:8811/health`
- [ ] All secrets in `.mcp.env.example` (no real keys in repo)

## Key Patterns to Follow

### Service Naming
- Main service: `<demo-name>-service` or `agent-service`
- Database: `<db>-service` (e.g., `mongodb-service`, `postgres-service`)
- Cache: `redis-service`, `cache-service`
- MCP Gateway: Always `mcp-gateway` (standard)

### Port Convention
- Main UI: `8080`
- Sub-agent services: `8001`, `8002`, etc. (for multi-agent)
- MCP Gateway: `8811` (standard)
- Database: `27017` (MongoDB), `5432` (PostgreSQL)

### Environment Variables
```yaml
# Always include
- MODEL=<default-model>
- MCP_GATEWAY_URL=http://mcp-gateway:8811/sse
- LOG_LEVEL=INFO

# For OpenAI mode
- OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

# For authentication
- GITHUB_TOKEN_FILE=/run/secrets/github_token
```

### MCP Configuration
```bash
# Standard pattern: register servers in gateway
--servers=duckduckgo,github-official,postgres
--tools=search,list_repos,query
--secrets=/run/secrets/mcp_secret
```

### Configuration File Patterns
- **Declarative YAML**: `agents.yaml` (Agno, A2A style)
- **Programmatic Python**: `agents/agent.py` class-based (ADK, CrewAI style)
- **Framework-native**: State graphs, crew configs, etc.

## Common MCP Servers Reference

| Server | Tools | Setup |
|--------|-------|-------|
| duckduckgo | search, search_news | No auth required |
| github-official | search_repos, get_issue, list_issues | `GITHUB_TOKEN` required |
| postgres | query, execute | `DATABASE_URL` required |
| mongodb | find, insert, update | `MONGODB_URL` required |
| brave | search | `BRAVE_API_KEY` required |
| google-maps | nearby, directions | `GOOGLE_MAPS_API_KEY` required |

## Post-Creation Steps

1. **Update `.github/instructions/` with demo-specific notes** (if complex)
   - Link from new README.md
2. **Add linting exceptions** (if needed) to top-level `Taskfile.yaml`
3. **Test multi-framework integration**: Ensure new demo doesn't break existing ones
4. **Open PR** with demo directory + root README update

## Reference: Existing Demos to Study

| Demo | Pattern | Complexity |
|------|---------|------------|
| [a2a](../a2a) | Sequential multi-agent, YAML config | Medium |
| [adk](../adk) | Programmatic Python, sub-agents | High |
| [langgraph](../langgraph) | Single-agent, state graph, database | Medium |
| [agno](../agno) | Declarative YAML, Next.js UI | High |
| [spring-ai](../spring-ai) | Java, properties-based | Low |
| [langchaingo](../langchaingo) | Go, minimal scaffolding | Low |

---

**Invoke this skill when:** Creating a new agent framework demo
**Output:** Complete demo directory + root README entry
**Time estimate:** 30-60 minutes scaffolding + testing
