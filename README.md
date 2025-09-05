# Amazur DevOps Test Backend

Minimal HTTP service with PostgreSQL, Docker Compose, CI and tests.  
This project was created as a backend/DevOps test task.

---

## 🔹 Project Overview

This project is a minimal HTTP service with PostgreSQL.  

Features include:

- Add items with `name` and `price`.
- Get statistics about items (`count` and `average price`).
- Health check endpoint `/health`.
- Clear database for testing (`/test/clear_items`, only in test environment).

The CI/CD pipeline runs linting, type checking, Docker image build and scans, integration tests, and image publishing.

---

## 🔹 Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic (DB migrations)
- Docker / Docker Compose
- Pytest (integration tests)
- GitHub Actions (CI)
- Pre-commit, Flake8, Black, isort, mypy, Hadolint, Trivy

---

## 🔹 Installation & Running

Compose brings up three services:

1. **postgres** – database
2. **migrate** – Alembic migrations
3. **app** – FastAPI service

Run:

```bash
git clone https://github.com/gifi71/amazur-devops-test.git
cd amazur-devops-test/deploy
cp .env.example .env
docker compose up -d
```

Check health:

```bash
curl http://localhost:8080/health
```

Stop:

```bash
docker compose down
```

---

## 🔹 API Endpoints

| Method | Path               | Description                          | Status |
| ------ | ------------------ | ------------------------------------ | ------ |
| GET    | /health            | Service health check                 | 200    |
| POST   | /add               | Add an item                          | 201    |
| GET    | /stats             | Get items statistics                 | 200    |
| POST   | /test/clear_items  | Clear database (only `APP_ENV=test`) | 200    |

---

## 🔹 Testing

### Integration Tests

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
pytest -v app/tests
```

Tests are also run in CI:

- Linting (`flake8`, `black`, `isort`)
- Type checking (`mypy`)
- Security scanning (Trivy, Hadolint)
- Integration tests with Docker Compose

---

## 🔹 CI/CD (GitHub Actions)

The pipeline includes:

1. **Lint** – code and Dockerfile checks
2. **Build Docker Image** – build and vulnerability scan
3. **Integration Tests** – run integration tests via Docker Compose
4. **Push & Sign** – publish and sign Docker images to GitHub Container Registry

Configuration file: `.github/workflows/ci.yml`.

---

## 🔹 Database Migrations

Alembic manages the database schema.  

1. **Create a migration locally**:

    ```bash
    cd app
    alembic revision -m "change" --autogenerate
    ````

2. **Rebuild Docker image**:

    ```bash
    docker build -t ghcr.io/gifi71/amazur-devops-test:latest ..
    ```

3. **Apply migrations**:

- Automatically: `docker compose up` (migrate runs before app)
- Manually: `docker compose run --rm migrate`

---

## 🔹 TODO

- [ ] Postgres volume
- [ ] Standardize logging
- [ ] Standardize responses
- [ ] Bump Postgres version
- [ ] Redesign project structure
- [ ] Add unit tests
- [ ] Add prometheus metrics
- [ ] Add swagger
- [ ] Add request examples
- [ ] Add .env descryption
- [ ] Add architecture and choices description
- [ ] Add /items endpoint with pagination
