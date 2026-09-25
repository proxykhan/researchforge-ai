# ResearchForge AI

**Autonomous Multi-Agent Research & Intelligence Platform**

*Research. Verify. Debate. Synthesize.*

ResearchForge AI is a production-grade platform that autonomously investigates complex research questions using specialized AI agents, external research APIs, RAG, document intelligence, automated verification, agent debate, and AI evaluation.

## Status

**Phase 0** — Repository setup, tooling, and standards.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13+, FastAPI, Pydantic |
| Agents | LangGraph |
| Database | PostgreSQL, pgvector |
| Cache | Redis |
| Frontend | Next.js, TypeScript, React |
| Infrastructure | Docker, AWS ECS Fargate, Terraform |
| CI/CD | GitHub Actions |
| Observability | OpenTelemetry, CloudWatch |

## Development Setup

### Prerequisites

- Python 3.13+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/researchforge-ai.git
cd researchforge-ai

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/
```

## License

MIT
