import re
from datetime import datetime

import pytest


@pytest.mark.asyncio
async def test_health(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert "status" in data and data["status"] == "ok"


@pytest.mark.asyncio
async def test_add_valid(async_client):
    resp = await async_client.post("/add", json={"name": "T", "price": 10})
    assert resp.status_code == 201

    data = resp.json()
    assert data["name"] == "T"
    assert data["price"] == 10
    assert "id" in data
    assert "created_at" in data

    try:
        datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pytest.fail(f"created_at has invalid format: {data['created_at']}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": 10},
        {"name": "F" * 129, "price": 10},
        {"name": "T", "price": 0},
        {"name": "T", "price": 0.0049},
        {"name": "T", "price": -1},
        {"name": "T", "price": 10_000_001},
    ],
)
async def test_add_invalid(async_client, payload):
    resp = await async_client.post("/add", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("price", [0.005, 0.01, 10_000_000])
async def test_add_edge_prices(async_client, price):
    resp = await async_client.post("/add", json={"name": "T", "price": price})
    assert resp.status_code == 201

    data = resp.json()
    assert data["price"] == round(price, 2)


@pytest.mark.asyncio
async def test_price_rounding(async_client):
    resp = await async_client.post("/add", json={"name": "T", "price": 1.2345})
    assert resp.status_code == 201

    data = resp.json()
    assert data["price"] == 1.23


@pytest.mark.asyncio
async def test_stats_after_additions(async_client):
    await async_client.post("/add", json={"name": "A", "price": 10})
    await async_client.post("/add", json={"name": "B", "price": 20})

    resp = await async_client.get("/stats")
    assert resp.status_code == 200

    data = resp.json()
    assert data["count"] == 2
    assert data["avg_price"] == 15


@pytest.mark.asyncio
async def test_stats_empty(async_client):
    resp = await async_client.get("/stats")
    assert resp.status_code == 200

    data = resp.json()
    assert data["count"] == 0
    assert data["avg_price"] == 0


@pytest.mark.asyncio
async def test_clear_items_endpoint(async_client):
    resp = await async_client.post("/test/clear_items")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = await async_client.get("/stats")
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_request_id_header(async_client):
    resp = await async_client.get("/health")
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_404_not_found(async_client):
    resp = await async_client.get("/unknown_path")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_item_bad_json(async_client):
    resp = await async_client.post("/add", content=b"not-a-json")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_items_empty(async_client):
    resp = await async_client.get("/items")
    assert resp.status_code == 200

    data = resp.json()
    assert data["page"] == 1
    assert data["limit"] == 50
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_items_after_add(async_client):
    await async_client.post("/add", json={"name": "Item1", "price": 10})
    await async_client.post("/add", json={"name": "Item2", "price": 20})

    resp = await async_client.get("/items?page=1&limit=10")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Item1"
    assert data["items"][1]["name"] == "Item2"
    assert data["items"][0]["price"] == 10
    assert data["items"][1]["price"] == 20


@pytest.mark.asyncio
async def test_items_pagination(async_client):
    for i in range(1, 6):
        await async_client.post("/add", json={"name": f"Item{i}", "price": i})

    resp = await async_client.get("/items?page=2&limit=2")
    assert resp.status_code == 200

    data = resp.json()
    assert data["page"] == 2
    assert data["limit"] == 2
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Item3"
    assert data["items"][1]["name"] == "Item4"


@pytest.mark.asyncio
async def test_items_limit_cap(async_client):
    for i in range(1, 6):
        await async_client.post("/add", json={"name": f"Item{i}", "price": i})

    resp = await async_client.get("/items?page=1&limit=200")
    assert resp.status_code == 200

    data = resp.json()
    assert data["limit"] == 100
    assert data["total"] == 5
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_metrics_endpoint_exists(async_client):
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200

    text = resp.text
    assert "# HELP" in text
    assert "# TYPE" in text


@pytest.mark.asyncio
async def test_metrics_request_counts(async_client):

    def get_metric_value(text, handler, method, status):
        pattern = rf'http_requests_total{{handler="{handler}",method="{method}",status="{status}"}} (\d+\.?\d*)'
        match = re.search(pattern, text)
        return float(match.group(1)) if match else 0.0

    async def fetch_metrics():
        resp = await async_client.get("/metrics")
        assert resp.status_code == 200
        return resp.text

    text_before = await fetch_metrics()
    add_before = get_metric_value(text_before, "/add", "POST", "2xx")
    stats_before = get_metric_value(text_before, "/stats", "GET", "2xx")
    health_before = get_metric_value(text_before, "/health", "GET", "2xx")

    for i in range(1, 6):
        await async_client.post("/add", json={"name": f"Item{i}", "price": i})

    await async_client.get("/stats")
    await async_client.get("/health")

    text_after = await fetch_metrics()

    assert (
        get_metric_value(text_after, "/add", "POST", "2xx") - add_before >= 5
    )
    assert (
        get_metric_value(text_after, "/stats", "GET", "2xx") - stats_before
        >= 1
    )
    assert (
        get_metric_value(text_after, "/health", "GET", "2xx") - health_before
        >= 1
    )
