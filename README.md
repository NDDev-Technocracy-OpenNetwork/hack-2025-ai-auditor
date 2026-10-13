<!-- nddev-public-hackathon -->
# hack-2025-ai-auditor

NFNG 2025 hackathon prototype: Curestry prompt analysis, validation and optimization. FastAPI + Next.js.

[NDDev OpenNetwork](https://github.com/NDDev-Technocracy-OpenNetwork) · [Repository](https://github.com/rldyourmnd/hack-2025-ai-auditor)

This repository is a hackathon prototype or supporting tool. Follow the project-specific setup below; cloud integrations require your own configuration and credentials.

---

## Curestry - AI Prompt Analysis & Optimization Platform



An intelligent platform for analyzing, validating, and optimizing prompts for Large Language Models (LLMs).

## Quick Start

```bash
# Clone and setup
git clone <repository>
cd curestry
cp .env.example .env
# Add your OpenAI API key to .env

# Start development environment
cd infra
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Windows Users

Use the provided batch script:
```bash
dev up     # Start all services
dev logs   # View logs
dev down   # Stop services
dev help   # Show all commands
```

## Features

- **Multi-dimensional Analysis**: Semantic consistency, markup validation, vocabulary optimization
- **Smart Patch Generation**: Automated improvement suggestions with safe/risky categorization
- **Interactive Clarification**: Chat-based prompt refinement
- **Prompt Base Management**: Cross-prompt relationship tracking and conflict detection
- **Multi-format Support**: XML and Markdown prompt analysis

## Architecture

- **Backend**: FastAPI + PostgreSQL + Redis
- **Frontend**: Next.js + Tailwind CSS + shadcn/ui
- **LLM Integration**: OpenAI GPT-5 — nano for cheap tasks; mini for standard and premium tiers
- **Deployment**: Docker Compose

## Development

- `dev up` - Start all services
- `dev down` - Stop all services
- `dev logs` - View service logs
- `dev ps` - Check container status

## Run on a Server (Docker)

Prerequisites:
- Docker and Docker Compose installed
- A copy of this repository on the server
- A proper .env created on the server (do not commit secrets)

Steps:
1) Create .env on the server (from .env.example) and set at minimum:
   - ENV=production
   - LOG_LEVEL=INFO
   - OPENAI_API_KEY=sk-...
   - DATABASE_URL=postgresql+psycopg://curestry:secure_password@db:5432/curestry
   - NEXT_PUBLIC_API_BASE=http://YOUR_SERVER_HOST_OR_IP:8000

2) Open firewall ports 3000 (web) and 8000 (api) on the server as needed.

3) Start the stack:
   - cd infra
   - docker compose up -d

4) Verify health:
   - API: http://YOUR_SERVER_HOST_OR_IP:8000/healthz
   - Web: http://YOUR_SERVER_HOST_OR_IP:3000

5) View logs / manage lifecycle:
   - docker compose logs -f
   - docker compose ps
   - docker compose down

Notes:
- In production behind a reverse proxy, set NEXT_PUBLIC_API_BASE to the external API URL (e.g., https://your.domain/api) and proxy accordingly.
- Postgres and Redis are internal to the Docker network and are not exposed publicly by default.

## License

MIT License - see LICENSE file for details.
