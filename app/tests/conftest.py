import os
import time

import httpx
import pytest
import pytest_asyncio

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("APP_BASE_URL", "http://localhost:8080")


@pytest_asyncio.fixture(autouse=True)
async def clear_items_table(async_client):
    await async_client.post("/test/clear_items")


@pytest.fixture(scope="session", autouse=True)
def wait_for_app(base_url):
    """Ждём пока сервис станет доступен по /health"""
    timeout = 30
    start = time.time()
    url = f"{base_url}/health"

    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(1)

    pytest.fail(f"App not healthy after {timeout} seconds at {url}")


@pytest_asyncio.fixture
async def async_client(base_url):
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        yield client
