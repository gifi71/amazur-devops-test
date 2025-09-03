from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
import logging
import time, os

from .db import SessionLocal
from .models import Item

app = FastAPI(title="Amazur Autotrade: DevOps Backend Engineer Test Task", version="0.1.0")


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    price: float = Field(..., gt=0, le=10_000_000)

    @validator("price")
    def round_price(cls, v):
        return round(v, 2)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# TODO: JSON logging
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()

formatter = logging.Formatter(
    '{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}'
)
handler.setFormatter(formatter)
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
    logger.info(log_data)

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/add", status_code=status.HTTP_201_CREATED)
def add_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": float(db_item.price),
        "created_at": db_item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    }


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    count = db.query(Item).count()
    avg_price = db.query(func.avg(Item.price)).scalar() or 0
    return {"count": count, "avg_price": round(float(avg_price), 2)}


if os.getenv("APP_ENV") == "test":
    @app.post("/test/clear_items")
    def clear_items(db: Session = Depends(get_db)):
        db.query(Item).delete()
        db.commit()
        return {"status": "ok"}
    
    
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"error": "Validation failed", "details": errors},
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"},
        headers={"Content-Type": "application/json"},
    )
