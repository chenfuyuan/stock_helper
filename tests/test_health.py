import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    # In a real test environment without DB, this might fail or return error
    # But since we catch exceptions in the health check, it should return 200
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
