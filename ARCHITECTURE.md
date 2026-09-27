# Architecture

## System Overview

ResearchForge AI is a multi-agent research platform built as a modular monolith. The system processes research questions through a pipeline of specialized AI agents, each responsible for a distinct phase of the research workflow.

```
User
  |
  v
Next.js Frontend (port 3000)
  |
  v (REST API)
FastAPI Backend (port 8000)
  |
  +-- Research Service (orchestration)
  |     |
  |     +-- LangGraph Agent Pipeline
  |     |     |
  |     |     +-- Planner --> Researcher --> Synthesizer
  |     |     |                                  |
  |     |     +-- Fact-Checker <-- Critic <------+
  |     |     |                      |
  |     |     +-- Debate Agents <----+
  |     |     |
  |     |     +-- Evaluator (scoring)
  |     |
  |     +-- Background Job Manager
  |
  +-- Research APIs (arXiv, Semantic Scholar, Crossref)
  +-- RAG Pipeline (chunk, embed, retrieve, rerank)
  +-- PostgreSQL (persistence)
  +-- Redis (caching, rate limiting)
```

## Agent Pipeline

The agent pipeline is implemented as a LangGraph `StateGraph`. Each node is a specialized agent that transforms shared `ResearchState`:

### Agents

| Agent | Role | Key Outputs |
|---|---|---|
| **Planner** | Decomposes question into subtasks, selects search queries | `search_queries`, `subtasks` |
| **Researcher** | Searches academic APIs, retrieves papers | `papers`, `paper_count` |
| **Synthesizer** | Extracts findings, produces grounded synthesis | `synthesis`, `key_findings` |
| **Fact-Checker** | Verifies claims against retrieved evidence | `verified_claims`, `unverified_claims` |
| **Critic** | Evaluates completeness, may request more research | `critique`, `needs_more_research` |
| **Debate** | Multiple perspectives argue competing conclusions | `debate_arguments`, `consensus` |
| **Evaluator** | Scores output quality (0-10 across 4 dimensions) | `evaluation_score`, `evaluation_details` |

### Graph Flow

```
plan_research --> execute_search --> synthesize
                                        |
                                        v
                                  fact_check --> debate --> critique
                                                              |
                                                   [needs_more?]
                                                  /            \
                                                yes             no
                                                 |               |
                                           execute_search    evaluate
```

The critic-to-researcher loop is bounded by a maximum iteration count to prevent infinite cycles.

### State Management

All agents share a `ResearchState` TypedDict containing:
- `question`: The original research question
- `search_queries`: Generated search queries
- `papers`: Retrieved paper metadata
- `synthesis`: The current synthesis text
- `iteration`: Current loop iteration count
- `evaluation_score`: Final quality score (0-10)

### Instrumentation

Every agent node is wrapped with `traced_agent_node`, which:
- Creates an OpenTelemetry span per agent invocation
- Records `agent.name`, `agent.duration_ms`, domain-specific attributes
- Propagates errors without swallowing them

## Backend Architecture

### Layer Structure

```
API Layer (FastAPI routes, schemas, middleware)
    |
Service Layer (ResearchService orchestration)
    |
Domain Layer (agents, RAG, integrations)
    |
Infrastructure Layer (database, cache, config)
```

### Key Design Decisions

**Repository Pattern**: The `ResearchRepository` protocol abstracts persistence. `InMemoryResearchRepository` is used in tests and development; `PostgresResearchRepository` uses SQLAlchemy async for production.

**Dependency Injection**: `create_app()` accepts optional overrides for every major dependency (LLM, registry, repository, job manager), making the entire app testable without mocking internals.

**Provider Abstraction**: Research sources (arXiv, Semantic Scholar, Crossref) implement a common `ResearchProvider` protocol with `search()` and rate-limiting. The `ProviderRegistry` manages provider lifecycle and parallel search.

**LLM Abstraction**: The `LLMProvider` protocol wraps model calls. `AnthropicProvider` implements it using the Anthropic SDK. This isolates prompt engineering from infrastructure.

### Middleware Stack (outermost first)

1. **GZipMiddleware** — Compresses responses > 500 bytes
2. **RequestSizeLimitMiddleware** — Rejects bodies > 10 MB (413)
3. **SecurityHeadersMiddleware** — CSP, X-Frame-Options, HSTS (prod)
4. **RequestIDMiddleware** — Generates/propagates X-Request-ID, binds to structlog
5. **CORSMiddleware** — Environment-driven origin allowlist

### Authentication

API key authentication via `Authorization: Bearer <key>`. Keys are validated against a user store (in-memory for dev, database-backed for production). Auth can be disabled via `AUTH_ENABLED=false`.

## RAG Pipeline

```
Document --> Chunker (semantic splitting)
                |
                v
          Embeddings (vector encoding)
                |
                v
          Vector Store (similarity search)
                |
                v
          Retriever (hybrid: keyword + semantic)
                |
                v
          Reranker (cross-encoder scoring)
                |
                v
          Top-K relevant chunks
```

The RAG pipeline uses hybrid retrieval combining BM25 keyword search with vector similarity, followed by cross-encoder reranking to maximize precision.

## Database Schema

| Table | Purpose |
|---|---|
| `research_sessions` | Research question, status, timestamps, results |
| `papers` | Discovered paper metadata (title, authors, DOI, etc.) |
| `session_papers` | Many-to-many: sessions to papers |

Migrations are managed by Alembic with async engine support.

## Infrastructure

### AWS Architecture

```
CloudFront / ALB
      |
      v
ECS Fargate Cluster
  +-- API Service (2+ tasks)
  +-- Worker Service (1+ tasks)
      |
      +-- RDS PostgreSQL (Multi-AZ)
      +-- ElastiCache Redis
      +-- S3 (document storage)
      +-- Secrets Manager
      +-- CloudWatch (logs, metrics, alarms)
```

### Terraform Modules

| Module | Resources |
|---|---|
| `vpc` | VPC, subnets (public/private), NAT, route tables |
| `rds` | PostgreSQL instance, subnet group, security group |
| `elasticache` | Redis cluster, subnet group |
| `s3` | Document storage bucket with encryption |
| `ecr` | Container image repositories |
| `alb` | Application load balancer, target groups, listeners |
| `ecs` | ECS cluster, task definitions, services |
| `secrets` | AWS Secrets Manager entries |
| `monitoring` | CloudWatch log groups, alarms, SNS topics |
| `github-oidc` | OIDC provider + IAM role for GitHub Actions |

Three environments: `dev`, `staging`, `prod` — each composing the same modules with different configurations.

## CI/CD Pipeline

```
Push to main
    |
    v
GitHub Actions CI
  +-- Lint (ruff)
  +-- Type check (mypy)
  +-- Test (pytest, 238 tests)
  +-- Build (Docker image)
    |
    v
GitHub Actions Deploy
  +-- Push to ECR
  +-- Terraform plan/apply
  +-- ECS service update
```

## Observability

| Concern | Implementation |
|---|---|
| Structured logging | structlog with JSON (prod) / colored console (dev) |
| Request correlation | X-Request-ID generated per request, propagated to all logs |
| Distributed tracing | OpenTelemetry with OTLP gRPC exporter |
| Agent instrumentation | Per-agent spans with duration, paper count, query count |
| Health checks | `/health` (liveness), `/health/ready` (DB + Redis) |

## Security Model

- API key authentication with Bearer tokens
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- HSTS in production
- CORS with environment-driven origin allowlist
- Request body size limit (10 MB)
- Prompt injection awareness (system instructions never overridable by retrieved content)
- Rate limiting via Redis (token bucket algorithm)
- Non-root container users
- AWS IAM with least privilege
- Secrets in environment variables / AWS Secrets Manager (never in code)
- Dependency scanning via pip-audit
