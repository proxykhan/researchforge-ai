# ResearchForge AI

**Autonomous Multi-Agent Research & Intelligence Platform**

*Research. Verify. Debate. Synthesize.*

ResearchForge AI is a production-grade platform that autonomously investigates complex research questions using specialized AI agents. It plans research, searches academic databases, retrieves and analyzes papers, extracts and verifies claims, conducts agent debate, evaluates output quality, and produces citation-grounded research reports.

## How It Works

A user submits a research question. The system:

1. **Planner** decomposes the question into subtasks and determines search strategy
2. **Researcher** searches arXiv, Semantic Scholar, and Crossref for relevant papers
3. **Synthesizer** extracts key findings and produces a grounded synthesis
4. **Fact-Checker** verifies important claims against retrieved evidence
5. **Debate** agents argue competing conclusions from multiple perspectives
6. **Critic** evaluates completeness and may request additional research
7. **Synthesizer** produces the final citation-grounded report
8. **Evaluator** scores the output on relevance, accuracy, completeness, and citation quality

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13+, TypeScript 5 |
| Backend | FastAPI, Pydantic, async/await |
| Agent Framework | LangGraph (stateful multi-agent graph) |
| LLM | Anthropic Claude (structured outputs) |
| Research APIs | arXiv, Semantic Scholar, Crossref |
| RAG | Chunking, embeddings, hybrid retrieval, reranking |
| Database | PostgreSQL (asyncpg), SQLAlchemy 2 |
| Cache | Redis (rate limiting, caching) |
| Auth | API key authentication with Bearer tokens |
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Containerization | Docker multi-stage builds, Docker Compose |
| CI/CD | GitHub Actions (lint, test, build, deploy) |
| Infrastructure | AWS ECS Fargate, RDS, ElastiCache, S3, ALB |
| IaC | Terraform (modular, multi-environment) |
| Observability | structlog (JSON), OpenTelemetry tracing, request correlation |
| Security | CORS, CSP, HSTS, request size limits, security headers |

## Project Structure

```
researchforge-ai/
  src/researchforge/
    agents/          # LangGraph agent nodes (planner, researcher, synthesizer, etc.)
    api/             # FastAPI app, routes, schemas
    auth/            # API key auth, user store
    cache/           # Redis client, rate limiter
    config.py        # Environment-driven settings
    database/        # SQLAlchemy async engine, models, migrations
    integrations/    # arXiv, Semantic Scholar, Crossref providers
    llm/             # LLM abstraction (Anthropic provider)
    observability/   # Logging, tracing, security middleware
    rag/             # Chunking, embeddings, retrieval, reranking
    repositories/    # Repository pattern (memory + Postgres)
    services/        # Research orchestration service
    workers/         # Background job manager
  tests/             # 238 Python tests (pytest)
  frontend/          # Next.js 16 app (19 Vitest tests)
  infrastructure/    # Terraform modules and environments
  .github/workflows/ # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- Git

### Local Development

```bash
# Clone and enter the project
git clone https://github.com/<your-username>/researchforge-ai.git
cd researchforge-ai

# Backend setup
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Frontend setup
cd frontend
npm install
cd ..
```

### Running the API

```bash
uvicorn researchforge.api.app:create_app --factory --reload
```

API docs available at http://localhost:8000/api/docs

### Running the Frontend

```bash
cd frontend && npm run dev
```

Frontend available at http://localhost:3000

### Docker Compose (full stack)

```bash
docker compose up --build
```

Starts: PostgreSQL, Redis, API (port 8000), Worker, Frontend (port 3000)

### Running Tests

```bash
# Python tests (238 tests)
pytest

# Frontend tests (19 tests)
cd frontend && npm test

# Code quality
ruff check src/ tests/
mypy src/
cd frontend && npx eslint .
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness check |
| GET | `/api/v1/health/ready` | Readiness check (DB + Redis) |
| POST | `/api/v1/research` | Submit a research question |
| GET | `/api/v1/research` | List all research sessions |
| GET | `/api/v1/research/{id}` | Get research detail |
| GET | `/api/v1/research/{id}/status` | Get research status |
| GET | `/api/v1/research/{id}/sources` | Get discovered papers |
| GET | `/api/v1/research/{id}/report` | Get the research report |
| POST | `/api/v1/research/{id}/cancel` | Cancel a running research |

All research endpoints require `Authorization: Bearer <api-key>` when `AUTH_ENABLED=true`.

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Environment (development/production) | development |
| `ANTHROPIC_API_KEY` | Claude API key | (required) |
| `DATABASE_URL` | PostgreSQL connection string | (empty) |
| `REDIS_URL` | Redis connection string | (empty) |
| `AUTH_ENABLED` | Enable API key authentication | true |
| `CORS_ORIGINS` | Comma-separated allowed origins | (empty) |
| `OTLP_ENDPOINT` | OpenTelemetry collector endpoint | (empty) |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions.

## Known Limitations

- **LLM dependency**: All agent reasoning requires a valid Anthropic API key and incurs token costs.
- **No persistent vector store**: RAG uses an in-memory vector store; a production deployment would use pgvector or a dedicated vector database.
- **Single-node workers**: The background job manager runs in-process; production should use a distributed task queue (Celery/Dramatiq).
- **No WebSocket streaming**: Research progress is polled via REST; WebSocket push would improve the UX.
- **Research APIs rate limits**: arXiv, Semantic Scholar, and Crossref have rate limits that constrain throughput for concurrent research sessions.
- **No user management UI**: Users are created via API or seed scripts, not through the frontend.

## License

MIT
