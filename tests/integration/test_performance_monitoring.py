"""Integration Test: Performance Monitoring (Scenario 3).

Validates user story: Monitor real-time strategy performance and analyze
historical results.
"""

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from http import HTTPStatus

from src.algo_trading.adapters.models import TinkoffAccountType
from src.algo_trading.enums import OrderSideEnum


async def test_performance_monitoring_and_analytics(
    client,
    config,
    mock_auth,
    create_trading_sessions,
    create_order,
    create_tinkoff_account,
):
    """
    Integration test for performance monitoring workflow.
    """
    user_id = mock_auth

    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'Performance Monitoring Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL', 'MSFT', 'GOOGL'],
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
        'created_by': str(user_id),
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        created = await response.json()
        assert response.status == HTTPStatus.CREATED
        strategy_id = created['strategy_id']

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    session_start = datetime.now(tz=UTC) - timedelta(days=25)
    session_end = datetime.now(tz=UTC) - timedelta(hours=1)

    trading_session = await create_trading_sessions(
        strategy_id=strategy_id,
        session_start=session_start,
        session_end=session_end,
        starting_capital=Decimal('50000.00'),
        ending_capital=Decimal('51500.00'),
    )

    prices = [150, 152, 148, 155, 147, 153, 149, 156, 151, 154,
              148, 157, 150, 152, 149, 155, 151, 153, 150, 154]


    day_counter = 1
    for i in range(0, len(prices) - 1, 2):
        await create_order(
            strategy_id=strategy_id,
            session_id=trading_session.session_id,
            side=OrderSideEnum.BUY,
            filled_at=session_start + timedelta(days=day_counter),
            quantity=Decimal('10'),
            filled_quantity=Decimal('10'),
            filled_price=Decimal(str(prices[i])),
        )
        day_counter += 1

        await create_order(
            strategy_id=strategy_id,
            session_id=trading_session.session_id,
            side=OrderSideEnum.SELL,
            filled_at=session_start + timedelta(days=day_counter),
            quantity=Decimal('10'),
            filled_quantity=Decimal('10'),
            filled_price=Decimal(str(prices[i + 1])),
        )
        day_counter += 1

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=1m',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        performance = await response.json()
        assert response.status == HTTPStatus.OK


        assert 'total_return' in performance or 'metrics' in performance

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/trades?period=1m',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        trade_analytics = await response.json()

        assert 'total_trades' in trade_analytics
        assert 'winning_trades' in trade_analytics
        assert 'avg_win' in trade_analytics

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/drawdown?period=1m',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        drawdown = await response.json()

        assert 'max_drawdown' in drawdown or 'drawdown' in drawdown

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/portfolio/summary?period=1m',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        summary = await response.json()

        assert 'total_value' in summary or 'portfolio' in summary or 'summary' in summary



async def test_performance_metrics_for_inactive_strategy(
        client,
        config,
        mock_auth,
        create_trading_sessions,
        create_tinkoff_account,
):
    """
    Test performance metrics for strategy that hasn't executed any trades.

    Validates graceful handling of empty performance data.
    """
    user_id = mock_auth

    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy_data = {
        'name': 'Inactive Performance Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL'],
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
        'created_by': str(user_id),
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        created = await response.json()
        assert response.status == HTTPStatus.CREATED
        strategy_id = created['strategy_id']

    session_start = datetime.now(tz=UTC) - timedelta(days=25)
    session_end = datetime.now(tz=UTC) + timedelta(days=3)

    trading_session = await create_trading_sessions(
        strategy_id=strategy_id,
        session_start=session_start,
        session_end=session_end,
        starting_capital=Decimal('50000.00'),
        ending_capital=Decimal('51500.00'),
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=1m',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        data = await response.json()
        assert response.status == HTTPStatus.OK
        assert data
