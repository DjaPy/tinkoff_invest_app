"""
Contract test for GET /api/v1/strategies endpoint

This test validates the API contract for listing trading strategies.
It should FAIL until the actual endpoint implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient


def test_get_strategies_returns_strategy_list():
    """Test GET /api/v1/strategies returns list of strategies"""
    # This test is designed to FAIL until implementation
    from src.algo_trading.api.strategies import app

    client = TestClient(app)

    response = client.get(
        "/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"}
    )

    # Contract assertions
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert "strategies" in data
    assert "total" in data
    assert isinstance(data["strategies"], list)
    assert isinstance(data["total"], int)

    # If strategies exist, validate structure
    if data["strategies"]:
        strategy = data["strategies"][0]
        assert "strategy_id" in strategy
        assert "name" in strategy
        assert "strategy_type" in strategy
        assert "status" in strategy
        assert "created_at" in strategy
        assert "updated_at" in strategy


def test_get_strategies_empty_list():
    """Test GET /api/v1/strategies returns empty list when no strategies"""
    from src.algo_trading.api.strategies import app

    client = TestClient(app)

    response = client.get(
        "/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["strategies"] == []


def test_get_strategies_unauthorized_without_token():
    """Test GET /api/v1/strategies requires authentication"""
    from src.algo_trading.api.strategies import app

    client = TestClient(app)

    response = client.get("/api/v1/strategies")

    assert response.status_code == 401
    data = response.json()
    assert data["status"] == 401
    assert data["title"] == "Unauthorized"


def test_get_strategies_internal_server_error():
    """Test GET /api/v1/strategies handles internal server errors"""
    from src.algo_trading.api.strategies import app

    client = TestClient(app)

    # This test will verify error handling structure
    # Implementation should handle database errors gracefully
    response = client.get(
        "/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"}
    )

    # If there's an internal error, it should follow RFC7807 format
    if response.status_code == 500:
        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert data["status"] == 500

import uuid

import pytest
from starlette import status


@pytest.mark.parametrize(
    'result',
    [
        (True, ),
        (False, ),
    ]
)
async def test_get_agents(
        monkeypatch,
        fake,
        client,
        services,
        config,
        pydantic_generator_data,
        result,
):
    invoice_id = uuid.uuid4()
    agents_schema = [
    pydantic_generator_data(
        AgentApiSchema,
        override={
            'invoice_id': invoice_id,
            'contract': None,
        },
    ) for _ in range(3)]
    agents = [Agent(**agent_schema.dict()) for agent_schema in agents_schema]

    async def fake_get_agent_by_invoice_id(*args, **kwargs):
        if result is True:
            return agents
        return None

    monkeypatch.setattr(
        'src.invoices.rest_api.api_v1.agents.get_agent_by_invoice_id',
        fake_get_agent_by_invoice_id,
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies"',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        await response.json()
        if result is True:
            assert False
        else:
            assert False
