FROM python:3.11-slim AS builder

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.11-slim

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY app/ ./app
COPY migrations/ ./migrations
COPY alembic.ini ./

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.src.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--log-level", "info", "--access-log", "--proxy-headers"]
