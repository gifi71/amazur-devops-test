import pytest

@pytest.mark.asyncio
async def test_health(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data and data["status"] == "ok"


@pytest.mark.asyncio
async def test_add_valid(async_client):
    resp = await async_client.post("/add", json={"name": "A", "price": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "A"
    assert data["price"] == 1
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"name": "", "price": 10},
    {"name": "X", "price": 0},
    {"name": "X", "price": -1},
    {"name": "A"*129, "price": 10},
    {"name": "Valid", "price": 10_000_001}
])
async def test_add_invalid(async_client, payload):
    resp = await async_client.post("/add", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("price", [0.01, 10_000_000])
async def test_add_edge_prices(async_client, price):
    resp = await async_client.post("/add", json={"name": f"Edge{price}", "price": price})
    assert resp.status_code == 201
    data = resp.json()
    assert data["price"] == round(price, 2)


@pytest.mark.asyncio
async def test_price_rounding(async_client):
    resp = await async_client.post("/add", json={"name": "RoundTest", "price": 1.2345})
    assert resp.status_code == 201
    data = resp.json()
    # Проверка округления до 2 знаков
    assert data["price"] == 1.23


@pytest.mark.asyncio
async def test_stats_after_additions(async_client):
    # очищаем таблицу
    await async_client.post("/test/clear_items")

    await async_client.post("/add", json={"name": "A", "price": 10})
    await async_client.post("/add", json={"name": "B", "price": 20})

    resp = await async_client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["avg_price"] == 15.0


@pytest.mark.asyncio
async def test_stats_empty(async_client):
    await async_client.post("/test/clear_items")
    resp = await async_client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["avg_price"] == 0


@pytest.mark.asyncio
async def test_clear_items_endpoint(async_client):
    # добавляем временный элемент
    await async_client.post("/add", json={"name": "Temp", "price": 1})
    resp = await async_client.post("/test/clear_items")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # проверка, что таблица пуста
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
    resp = await async_client.post("/add", data="not-a-json")
    assert resp.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("name, price", [
    ("Item1", 10),
    ("Item2", 20),
    ("Item3", 30.55),
])
async def test_add_multiple_items(async_client, name, price):
    await async_client.post("/add", json={"name": name, "price": price})
    resp = await async_client.get("/stats")
    assert resp.status_code == 200
