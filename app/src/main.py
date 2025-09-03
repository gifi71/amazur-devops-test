from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, validator
from uuid import uuid4
from datetime import datetime
import logging
import time

app = FastAPI(title="Amazur Autotrade: DevOps Backend Engineer Test Task", version="0.1.0")


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    price: float = Field(..., gt=0, le=10_000_000)

    @validator("price")
    def round_price(cls, v):
        return round(v, 2)


# TODO: Move to DB
items = []
counter = 0

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
        "ts": datetime.utcnow().isoformat(),
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
def add_item(item: ItemCreate):
    global counter
    counter += 1
    new_item = {
        "id": counter,
        "name": item.name,
        "price": item.price,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    items.append(new_item)
    return new_item


@app.get("/stats")
def get_stats():
    if not items:
        return {"count": 0, "avg_price": 0}

    total = sum(i["price"] for i in items)
    avg_price = round(total / len(items), 2)
    return {"count": len(items), "avg_price": avg_price}


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
