---
name: compose-for-agents-debug
description: "Diagnose and fix Docker Compose issues in agent demos. Use when: debugging agent service failures, fixing MCP Gateway errors, resolving networking issues, troubleshooting secret/environment problems, validating agent deployment."
---

# Compose-for-Agents Debug Skill

This skill provides diagnostic tools and step-by-step troubleshooting for common issues in compose-for-agents demos.

## Quick Diagnosis Flowchart

```
Agent not working?
├─ Check logs: docker compose logs -f agent-service
├─ Check status: docker compose ps
├─ Check network: docker network ls
├─ Check secrets: docker compose config | grep -A5 secrets
└─ Check gateway health: curl http://localhost:8811/health
```

## Common Issues & Solutions

### 1. Services Can't Communicate

**Symptom:** Agent logs: `Connection refused: localhost:8811` or `Failed to reach mcp-gateway`

**Root Cause:** Using `localhost` instead of service name in Docker network

**Fix:**
```yaml
# ❌ WRONG (in container)
MCP_GATEWAY_URL: http://localhost:8811/sse

# ✅ CORRECT (service name as hostname)
MCP_GATEWAY_URL: http://mcp-gateway:8811/sse
```

**Verification:**
```bash
docker compose exec agent-service ping mcp-gateway
# Should succeed; if fails, check service names in compose.yaml
```

### 2. MCP Gateway Health Check Fails

**Symptom:** `curl http://localhost:8811/health` returns `Connection refused`

**Root Cause:** Gateway not started or port not exposed

**Diagnostic:**
```bash
docker compose logs mcp-gateway
docker compose ps mcp-gateway  # Check status

# If "exited", check why:
docker compose up mcp-gateway --no-build
```

**Common causes:**
- Missing MCP servers: `--servers=duckduckgo,github-official`
- Invalid secrets path: Check `MCP_SECRETS_FILE` mount
- Port conflict: `lsof -i :8811` on host

### 3. Secrets Not Found

**Symptom:** Agent logs: `Secret 'mcp_secret' not found` or `FileNotFoundError: /run/secrets/...`

**Root Cause:** Missing `.mcp.env` file or secrets misconfigured

**Fix:**
```bash
# Copy template
cp mcp.env.example .mcp.env

# Add required keys (varies by demo)
cat >> .mcp.env << EOF
GITHUB_TOKEN=gh_xxxxx
OPENAI_API_KEY=sk-xxxxx
EOF

# For OpenAI mode, also create
echo "sk-xxxxx" > secret.openai-api-key
chmod 600 secret.openai-api-key
```

**Verify:**
```bash
docker compose config | grep -A10 secrets
# Should show secrets:section with files mapped correctly
```

### 4. GPU Not Being Used

**Symptom:** Agent slow; checking logs shows CPU-only inference

**Diagnostic:**
```bash
# Check Docker GPU support
docker run --rm --gpus all nvidia-smi
# If fails, GPU not available to Docker

# Check demo's compose.yaml
grep -i "gpu\|device\|runtime" compose.yaml
# Should have: deploy.resources.reservations.devices
```

**Fix:**
```yaml
# Add to compose.yaml service
services:
  agent-service:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Requirements:**
- Docker Desktop 4.43.0+ (check: `docker --version`)
- NVIDIA GPU drivers installed
- `nvidia-docker` or Docker GPU support enabled
- Use local `compose.yaml`, not OpenAI overlay

### 5. Port Conflicts

**Symptom:** `docker compose up` fails: `port 8080 already in use`

**Diagnostic:**
```bash
# Find what's using the port
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill the process or use different port
docker compose down -v
```

**Fix:**
```bash
# Option 1: Stop conflicting service
kill -9 <PID>
docker compose down -v
docker compose up --build

# Option 2: Use different port
docker compose up -p alt-8080:8080 --build

# Option 3: Update compose.yaml
services:
  agent-service:
    ports:
      - "9090:8080"  # External:Internal
```

### 6. Image Build Failures

**Symptom:** `docker compose up --build` fails during image construction

**Diagnostic:**
```bash
# Get full build output
docker compose build --no-cache agent-service 2>&1 | tail -50

# Common causes:
# - Dependencies not installing
# - Network issues in Docker build
# - Missing base image
```

**Fix:**
```bash
# Rebuild from scratch
docker compose down -v
docker image rm <demo>-agent-service:latest
docker compose up --build

# If persistent, check Dockerfile
# Ensure multi-stage build is correct (FROM ... AS base)
```

### 7. Switching Between Deployment Modes

**Symptom:** Errors after switching from local → OpenAI or vice versa

**Root Cause:** Environment state not cleaned

**Fix:**
```bash
# ALWAYS do this when switching modes
docker compose down -v  # Remove volumes + networks

# For OpenAI mode
docker compose -f compose.yaml -f compose.openai.yaml up --build

# For local mode (default)
docker compose up --build

# For GPU offload
docker compose -f compose.yaml -f compose.offload.yaml up --build
```

### 8. Database Connection Errors

**Symptom:** Agent logs: `SQLSTATE[08006] could not connect to server`

**Root Cause:** Wrong hostname or credentials

**Fix:**
```bash
# Correct pattern (in Docker network)
DATABASE_URL=postgresql://user:pass@postgres-service:5432/dbname
# NOT: localhost:5432

# Verify connectivity
docker compose exec agent-service \
  psql -h postgres-service -U user -d dbname -c "SELECT 1"
```

### 9. Agent Service Crashes on Startup

**Symptom:** `docker compose logs agent-service` shows crash immediately

**Diagnostic:**
```bash
# Full error trace
docker compose logs --tail=100 agent-service

# Common causes:
# 1. Missing dependencies: check pyproject.toml
# 2. Wrong Python version: check Dockerfile
# 3. Missing .env variables: check environment: section

# Run shell for manual testing
docker compose run --rm agent-service bash
cd /app && python -m agents.main  # Test manually
```

### 10. MCP Server Tool Not Available

**Symptom:** Agent logs: `Tool 'search' not found` or `Unknown tool: duckduckgo/search`

**Diagnostic:**
```bash
# Check gateway config
docker compose exec mcp-gateway ps aux | grep mcp-gateway

# Check which servers are running
curl http://localhost:8811/tools
# Should return JSON list of available tools

# Check gateway startup
docker compose logs mcp-gateway | grep -i "server\|tool\|loaded"
```

**Fix:**
```yaml
# Ensure server is in compose.yaml
mcp-gateway:
  command:
    - --servers=duckduckgo,github-official  # Add missing server
    - --tools=search,fetch_content  # Restrict tools (optional)
```

## Advanced Debugging

### Enable Verbose Logging

```bash
# For all services
docker compose up --build 2>&1 | tee compose.log

# For specific service
docker compose logs -f agent-service --tail=200

# Inside container shell
docker compose exec agent-service bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

### Inspect Container Network

```bash
# List networks
docker network ls

# Inspect network (shows connected services)
docker network inspect compose-for-agents_default

# Test DNS resolution inside container
docker compose exec agent-service nslookup mcp-gateway
docker compose exec agent-service ping -c 3 mcp-gateway
```

### Validate Compose Configuration

```bash
# Dry-run: show resolved config
docker compose config

# Check for issues
docker compose config --quiet  # No output = valid

# Validate specific service
docker compose config --services  # List all services
```

### Extract Logs for Analysis

```bash
# Save all logs
docker compose logs > debug.log 2>&1

# Filter by service
docker compose logs agent-service > agent.log
docker compose logs mcp-gateway > gateway.log

# Real-time with timestamps
docker compose logs --timestamps --follow --tail=50
```

## Troubleshooting Checklist

Before reporting an issue:

- [ ] `docker compose down -v && docker compose up --build` (clean restart)
- [ ] Docker Desktop/Engine updated to 4.43.0+
- [ ] `.mcp.env` exists (copy from `.mcp.env.example`)
- [ ] No port conflicts: `lsof -i :8080`
- [ ] GPU available: `docker run --rm --gpus all nvidia-smi` (if using local)
- [ ] Logs reviewed: `docker compose logs --tail=200`
- [ ] Service names verified (not using `localhost` in compose)
- [ ] Network connectivity tested: `docker network inspect`
- [ ] Secrets mounted correctly: `docker compose config | grep -A5 secrets`
- [ ] Right compose file for mode (local vs OpenAI vs offload)

## When to Report Issues

If troubleshooting doesn't work:

1. Collect diagnostics:
   ```bash
   docker compose config > config.yaml
   docker compose logs > logs.txt
   docker compose ps > services.txt
   ```

2. Include in issue report:
   - Docker version: `docker --version`
   - Demo name and compose command used
   - Full error logs
   - `docker compose config` output
   - OS and hardware (GPU model if applicable)

---

**Invoke this skill when:** Debugging any Docker Compose errors
**Output:** Specific diagnostic commands + fix recommendations
**Resolution time:** 5-30 minutes for most issues
