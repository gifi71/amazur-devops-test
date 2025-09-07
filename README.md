# amazur-devops-test

Minimal HTTP service with FastAPI, PostgreSQL, Docker Compose, CI, tests and Prometheus metrics.
Runs with a single Docker Compose command. This project was created as a backend/DevOps test task.

---

## Requirements

- Docker **>= 28.1**
- Docker Compose **>= 2.36**

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/gifi71/amazur-devops-test.git
cd amazur-devops-test

# Copy environment variables
cp .env.example .env

# Build and start the service
cd deploy/
# for prod (latest image from GHCR)
docker compose up -d
# or build from Dockerfile for dev
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Health check
curl -s localhost:8080/health

# Stop
docker compose down
```

---

## API Endpoints

| Method | Endpoint          | Description |
|--------|------------------|-------------|
| **GET**  | `/health`          | Service health check. |
| **POST** | `/add`             | Add a new item. |
| **GET**  | `/stats`           | Get statistics about items. (`{count = 0, avg_price = 0}` if no items) |
| **GET**  | `/items`           | Get a paginated list of items. |
| **POST** | `/test/clear_items` | Delete all items (available only in `APP_ENV=test`). |
| **GET**  | `/metrics`         | Prometheus metrics for monitoring. |
| **GET**  | `/docs`            | Swagger UI documentation. |
| **GET**  | `/redoc`           | ReDoc documentation. |
| **GET**  | `/openapi.json`    | OpenAPI specification in JSON. |

---

## Example Requests

Add an item:

```bash
curl -X POST localhost:8080/add \
  -H 'Content-Type: application/json' \
  -d '{"name":"item","price":100}'
```

Get statistics:

```bash
curl -s localhost:8080/stats
```

Get paginated items:

```bash
curl -s "localhost:8080/items?page=1&limit=10"
```

Prometheus metrics:

```bash
curl -s localhost:8080/metrics
```

---

## Environment Variables

| Variable        | Example Value                                           | Description |
|-----------------|---------------------------------------------------------|-------------|
| **POSTGRES_USER**     | `postgres`                                         | Username for PostgreSQL. |
| **POSTGRES_PASSWORD** | `postgres`                                         | Password for PostgreSQL. |
| **POSTGRES_DB**       | `postgres`                                         | Database name. |
| **POSTGRES_HOST**     | `postgres`                                         | Hostname of the PostgreSQL server (container/service name). |
| **POSTGRES_PORT**     | `5432`                                             | PostgreSQL server port. |
| **DATABASE_URL**      | `postgresql+asyncpg://postgres:postgres@postgres:5432/postgres` | Full async database connection string (SQLAlchemy + asyncpg). |
| **APP_BASE_URL**      | `http://localhost:8080`                            | Base URL of the application. |
| **APP_ENV**           | `test`                                             | Application environment (`dev`, `test`, `prod`). |

---

## Running Tests

```bash
# Install development dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt

# Run tests
pytest -v app/tests
```

Tests are also run in CI:

- Scan for secrets (`gitleaks`)
- Linting (`flake8`, `black`, `isort`)
- Type checking (`mypy`)
- Security scanning (Trivy, Hadolint)
- Integration tests over Docker Compose

---

## CI/CD (GitHub Actions)

The pipeline includes:

1. **Lint** – code and Dockerfile checks
2. **Build Docker Image** – build and vulnerability scan
3. **Integration Tests** – run integration tests via Docker Compose
4. **Push & Sign** – publish and sign Docker images to GHCR

Configuration file: `.github/workflows/ci.yml`.

---

## Database Migrations

Alembic manages the database schema.  

1. **Create a migration locally**:

    ```bash
    DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/postgres alembic revision -m "change" --autogenerate
    ```

2. **Rebuild Docker image**:

    ```bash
    docker compose build
    ```

3. **Apply migrations**:

    - Automatically: `docker compose up -d` (migrate runs before app)
    - Manually: `docker compose run --rm migrate` (new verssion must be in container)
    - Manually: `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/postgres alembic upgrade head`

---

## Architecture & Key Features

The project follows a clean service-oriented architecture with strict separation of concerns:

- **FastAPI Application** – provides REST API endpoints (`/add`, `/stats`, `/items`, `/health`, `/metrics`) with input validation, structured error handling, and request logging with unique request IDs.
- **PostgreSQL Database** – used as the primary async data store. Database schema changes are managed through **Alembic migrations** for consistency and reproducibility.
- **Dockerized Setup** – all components (app, database, migrations) run in containers orchestrated by **Docker Compose**, with health checks ensuring readiness before dependent services start.
- **Continuous Integration (CI)** – GitHub Actions pipeline runs linting (flake8, black, isort, mypy), Dockerfile linting (hadolint), secret detection (gitleaks), and security scans (Trivy). Integration tests are executed against a fully containerized environment before images are signed and published.
- **Observability** – structured JSON logs include request metadata (method, path, latency, status, request_id). A `/metrics` endpoint exposes Prometheus-compatible metrics such as request counts, latencies, and error rates.
- **Security & Reliability** – images are built with caching, scanned for vulnerabilities, signed with Cosign, and run with health checks. Input validation prevents invalid or unsafe data from being stored.
- **Extra Features** – pagination support for `/items`, price rounding with validation, and environment-specific test utilities (e.g., `/test/clear_items` when `APP_ENV=test`).

---

## TODO

Planned improvements and enhancements:

- [ ] Reconfigure development environment (pre-commit hooks, linters, formatters)
- [ ] Add simple filtering support for the `/items` endpoint
- [ ] Restrict access to Prometheus metrics endpoint
- [ ] Refactor codebase for clarity and maintainability
- [ ] Redesign overall project structure
