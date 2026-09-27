# Deployment Guide

## Local Development

### Prerequisites

- Python 3.13+
- Node.js 22+
- Docker and Docker Compose (optional, for full stack)
- An Anthropic API key

### Backend Only

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"

cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY, AUTH_ENABLED=false for dev

uvicorn researchforge.api.app:create_app --factory --reload
```

API available at http://localhost:8000. Docs at http://localhost:8000/api/docs.

### Frontend Only

```bash
cd frontend
npm install
npm run dev
```

Frontend available at http://localhost:3000. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if the API runs on a different host.

### Docker Compose (Full Stack)

```bash
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

docker compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **API** on port 8000 (with health check)
- **Worker** (background job processor)
- **Frontend** on port 3000

To run in detached mode: `docker compose up -d --build`

To stop: `docker compose down`

To reset data: `docker compose down -v` (removes volumes)

## Running Tests

```bash
# Python tests
pytest                        # All 238 tests
pytest tests/test_api*.py     # API tests only
pytest -x                     # Stop on first failure

# Frontend tests
cd frontend && npm test

# Code quality
ruff check src/ tests/        # Lint
ruff format --check src/      # Format check
mypy src/                     # Type check
cd frontend && npx eslint .   # Frontend lint
```

## CI/CD Pipeline

### GitHub Actions Workflows

| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | Push/PR to main | Lint, type check, test, build Docker image |
| `deploy.yml` | Push to main (after CI) | Push to ECR, deploy to ECS |
| `terraform.yml` | Changes to `infrastructure/` | Format check, validate, plan |

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key for integration tests |
| `AWS_REGION` | AWS region (e.g., us-east-1) |
| `AWS_ACCOUNT_ID` | AWS account ID for ECR |
| `AWS_ROLE_ARN` | IAM role ARN for GitHub OIDC |

## AWS Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform 1.6+
- An S3 bucket for Terraform state (created via bootstrap)

### Step 1: Bootstrap Terraform State

```bash
cd infrastructure/terraform/bootstrap
terraform init
terraform apply
```

This creates the S3 bucket and DynamoDB table for remote state locking.

### Step 2: Deploy Infrastructure

```bash
# Start with staging
cd infrastructure/terraform/environments/staging
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

This provisions: VPC, RDS, ElastiCache, S3, ECR, ALB, ECS cluster, Secrets Manager, CloudWatch, and IAM roles.

### Step 3: Push Docker Images

```bash
# Authenticate with ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

# Build and push API image
docker build -t researchforge-api .
docker tag researchforge-api:latest <account>.dkr.ecr.<region>.amazonaws.com/researchforge-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/researchforge-api:latest

# Build and push frontend image
docker build -t researchforge-frontend frontend/
docker tag researchforge-frontend:latest <account>.dkr.ecr.<region>.amazonaws.com/researchforge-frontend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/researchforge-frontend:latest
```

### Step 4: Configure Secrets

Store secrets in AWS Secrets Manager (referenced by the ECS task definitions):

```bash
aws secretsmanager create-secret --name researchforge/anthropic-api-key --secret-string "<your-key>"
aws secretsmanager create-secret --name researchforge/database-url --secret-string "<connection-string>"
```

### Step 5: Deploy to Production

```bash
cd infrastructure/terraform/environments/prod
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

### Step 6: Verify

```bash
# Check ECS service status
aws ecs describe-services --cluster researchforge --services api worker

# Hit the health endpoint
curl https://<alb-dns>/api/v1/health
```

## Environment Variables Reference

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | development / staging / production | development |
| `APP_NAME` | Application name for telemetry | researchforge-ai |
| `APP_LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `AUTH_ENABLED` | Enable API key auth | true |
| `ANTHROPIC_API_KEY` | Claude API key | (required) |
| `LLM_MODEL` | Claude model to use | claude-sonnet-5 |
| `DATABASE_URL` | PostgreSQL async connection string | (empty) |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size | 5 |
| `DB_MAX_OVERFLOW` | Max connections above pool size | 10 |
| `REDIS_URL` | Redis connection string | (empty) |
| `CORS_ORIGINS` | Comma-separated allowed origins | (empty) |
| `OTLP_ENDPOINT` | OpenTelemetry OTLP gRPC endpoint | (empty) |
| `OTEL_CONSOLE` | Log traces to console | false |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key (optional) | (empty) |
| `NEXT_PUBLIC_API_URL` | API URL for the frontend | http://localhost:8000 |

## Monitoring

### Health Checks

- **Liveness**: `GET /api/v1/health` — returns `{"status": "ok"}` if the process is running
- **Readiness**: `GET /api/v1/health/ready` — checks database and Redis connectivity

### Logs

- Development: colored console output via structlog
- Production: JSON-formatted logs with `request_id`, `timestamp`, `level`, `event`
- AWS: Logs ship to CloudWatch Log Groups via ECS

### Tracing

- Set `OTLP_ENDPOINT` to your OpenTelemetry collector
- Each request gets an X-Request-ID propagated through all agent spans
- Agent spans include: `agent.name`, `agent.duration_ms`, `paper_count`, `query_count`

### Alarms (CloudWatch)

- API 5xx error rate > 5% for 5 minutes
- API p99 latency > 10s
- ECS task count below desired
- RDS CPU > 80%
- Redis memory > 80%
