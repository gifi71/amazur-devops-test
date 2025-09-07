import json
import logging
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import AsyncSessionLocal
from .models import Item

app = FastAPI(
    title="amazur-devops-test",
    version="1.0.0",
)


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    price: float = Field(..., le=10_000_000)

    @field_validator("price")
    @classmethod
    def round_price(cls, v: float) -> float:
        v = round(v, 2)
        if v <= 0:
            raise ValueError("Price must be greater than 0 after rounding")
        return v


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    log_data = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": "INFO",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": round(process_time, 2),
        "request_id": request_id,
    }
    logger.info(json.dumps(log_data, ensure_ascii=False))

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.post("/add", status_code=status.HTTP_201_CREATED, tags=["Items"])
async def add_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    db_item = Item(name=item.name, price=item.price)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    return {
        "status": "ok",
        "id": db_item.id,
        "name": db_item.name,
        "price": float(db_item.price),
        "created_at": db_item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/stats", tags=["Stats"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Item.id)))
    count = result.scalar()

    result = await db.execute(select(func.avg(Item.price)))
    avg_price = result.scalar() or 0

    return {
        "status": "ok",
        "count": count,
        "avg_price": round(float(avg_price), 2),
    }


@app.get("/items", tags=["Items"])
async def get_items(
    db: AsyncSession = Depends(get_db), page: int = 1, limit: int = 50
):
    limit = min(limit, 100)

    result = await db.execute(select(func.count(Item.id)))
    total: int = result.scalar_one()

    items_result = await db.execute(
        select(Item).offset((page - 1) * limit).limit(limit)
    )
    items: list[Item] = list(items_result.scalars().all())

    return {
        "status": "ok",
        "page": page,
        "limit": limit,
        "total": total,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "price": float(item.price),
                "created_at": item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            for item in items
        ],
    }


if os.getenv("APP_ENV") == "test":

    @app.post("/test/clear_items", tags=["Items"])
    async def clear_items(db: AsyncSession = Depends(get_db)):
        await db.execute(delete(Item))
        await db.commit()

        result = await db.execute(select(func.count(Item.id)))
        if result.scalar_one() > 0:
            return {"status": "error", "error": "Items not deleted"}

        return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "error": "Validation failed",
            "details": errors,
        },
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": exc.detail},
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal Server Error"},
        headers={"Content-Type": "application/json"},
    )


Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", tags=["Stats"]
)
