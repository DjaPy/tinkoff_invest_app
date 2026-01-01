from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from starlette import status

from src.algo_trading.adapters.models import RiskControls
from src.algo_trading.enums import StrategyTypeEnum
from src.algo_trading.ports.api.v1.schemas.analytics_schema import (
    BacktestRequestSchema,
    BacktestResponseSchema,
)



async def test_post_backtest_runs_strategy_backtest(client, config, mock_auth, mongo_connection):
    """Test POST /api/v1/analytics/backtest runs a backtest"""
    backtest_request = BacktestRequestSchema(
        strategy_type=StrategyTypeEnum.MOMENTUM,
        parameters={'lookback_period': 20, 'momentum_threshold': 0.02, 'position_size': 100},
        instruments=['AAPL', 'MSFT'],
        start_date=datetime.now(timezone.utc) - timedelta(days=365),
        end_date=datetime.now(timezone.utc),
        initial_capital=Decimal('100000'),
        risk_controls=RiskControls(
            max_position_size=Decimal('10000'),
            max_portfolio_value=Decimal('100000'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.10'),
            daily_loss_limit=Decimal('1000'),
            max_orders_per_day=20,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
            enabled=True,
        ),
    )

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=backtest_request.model_dump(mode='json'),
    ) as response:
        data = await response.json()
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']
        results = BacktestResponseSchema(**data)
        assert results.strategy_type == backtest_request.strategy_type
        assert results.initial_capital == Decimal(backtest_request.initial_capital)
        assert results.final_capital > 0
        assert results.total_trades >= 0
        assert 0 <= results.win_rate <= 1
        assert results.max_drawdown <= 0



async def test_post_backtest_validates_required_fields(client, config, mock_auth):
    """Test POST /api/v1/analytics/backtest validates required fields"""
    invalid_request = {
        'strategy_type': 'momentum',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_request,
    ) as response:
        data = await response.json()
        assert response.status == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 422



async def test_post_backtest_validates_date_range(client, config, mock_auth):
    """Test POST /api/v1/analytics/backtest validates date range"""
    invalid_request = {
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'instruments': ['AAPL'],
        'start_date': datetime.now(timezone.utc).isoformat(),
        'end_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),  # Invalid: before start
        'initial_capital': str(Decimal('100000')),
        'risk_controls': {
            'max_position_size': str(Decimal('10000')),
            'max_portfolio_value': str(Decimal('100000')),
            'stop_loss_percent': str(Decimal('0.05')),
            'max_drawdown_percent': str(Decimal('0.10')),
            'daily_loss_limit': str(Decimal('1000')),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_request,
    ) as response:
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT]
        data = await response.json()
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 400
        assert data.get('detail') == 'end_date must be after start_date'


async def test_post_backtest_validates_initial_capital(client, config, mock_auth):
    """Test POST /api/v1/analytics/backtest validates initial capital is positive"""
    invalid_request = {
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'instruments': ['AAPL'],
        'start_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        'end_date': datetime.now(timezone.utc).isoformat(),
        'initial_capital': str(Decimal('-1000')),  # Invalid: negative
        'risk_controls': {
            'max_position_size': str(Decimal('10000')),
            'max_portfolio_value': str(Decimal('100000')),
            'stop_loss_percent': str(Decimal('0.05')),
            'max_drawdown_percent': str(Decimal('0.10')),
            'daily_loss_limit': str(Decimal('1000')),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_request,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = await response.json()
        assert data['status'] == 422



async def test_post_backtest_validates_instruments_list(client, config, mock_auth):
    """Test POST /api/v1/analytics/backtest requires at least one instrument"""
    invalid_request = {
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'instruments': [],  # Invalid: empty list
        'start_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        'end_date': datetime.now(timezone.utc).isoformat(),
        'initial_capital': str(Decimal('100000')),
        'risk_controls': {
            'max_position_size': str(Decimal('10000')),
            'max_portfolio_value': str(Decimal('100000')),
            'stop_loss_percent': str(Decimal('0.05')),
            'max_drawdown_percent': str(Decimal('0.10')),
            'daily_loss_limit': str(Decimal('1000')),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_request,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = await response.json()
        assert data['status'] == 422



async def test_post_backtest_unauthorized(client, config):
    """Test POST /api/v1/analytics/backtest requires authentication"""
    backtest_request = {
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'instruments': ['AAPL'],
        'start_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        'end_date': datetime.now(timezone.utc).isoformat(),
        'initial_capital': str(Decimal('100000')),
        'risk_controls': {},
    }

    # No Authorization header
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Content-Type': 'application/json'},
        json=backtest_request,
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.parametrize('strategy_type', ['momentum', 'mean_reversion', 'arbitrage', 'market_making'])

async def test_post_backtest_supports_different_strategy_types(client, config, strategy_type):
    """Test POST /api/v1/analytics/backtest supports different strategy types"""
    backtest_request = {
        'strategy_type': strategy_type,
        'parameters': {'lookback_period': 20},
        'instruments': ['AAPL'],
        'start_date': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        'end_date': datetime.now(timezone.utc).isoformat(),
        'initial_capital': str(Decimal('100000')),
        'risk_controls': {
            'max_position_size': str(Decimal('10000')),
            'max_portfolio_value': str(Decimal('100000')),
            'stop_loss_percent': str(Decimal('0.05')),
            'max_drawdown_percent': str(Decimal('0.10')),
            'daily_loss_limit': str(Decimal('1000')),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=backtest_request,
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            results = BacktestResponseSchema(**data)
            assert results.strategy_type == strategy_type
