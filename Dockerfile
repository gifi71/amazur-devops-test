FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir --upgrade pip==25.2 setuptools==80.9.0
WORKDIR /app

COPY requirements/base.txt .

RUN pip install --no-cache-dir -r base.txt

FROM python:3.13-slim

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY app/ ./app
COPY migrations/ ./migrations
COPY alembic.ini ./

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.src.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--log-level", "info", "--no-access-log"]
