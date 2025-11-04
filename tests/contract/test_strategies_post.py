"""
Contract test for POST /api/v1/strategies endpoint

This test validates the API contract for creating new trading strategies.
It should FAIL until the actual endpoint implementation is complete.
"""


# This will fail until the endpoint is implemented
def test_post_strategies_creates_new_strategy():
    """Test POST /api/v1/strategies creates a new trading strategy"""
    # This test is designed to FAIL until implementation

    strategy_data = {
        'name': 'Test Momentum Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'instruments': ['AAPL', 'MSFT'],
            'position_size': 100,
        },
        'risk_controls': {
            'max_position_size': 1000,
            'max_portfolio_value': 50000,
            'stop_loss_percent': 0.05,
            'max_drawdown_percent': 0.10,
            'daily_loss_limit': 1000,
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    response = client.post('/api/v1/strategies', json=strategy_data)

    # Contract assertions
    assert response.status_code == 201
    assert 'application/json' in response.headers['content-type']

    data = response.json()
    assert 'strategy_id' in data
    assert data['name'] == strategy_data['name']
    assert data['strategy_type'] == strategy_data['strategy_type']
    assert data['status'] == 'inactive'
    assert 'created_at' in data
    assert 'updated_at' in data
    assert 'risk_controls' in data


def test_post_strategies_validates_required_fields():
    """Test POST /api/v1/strategies validates required fields"""

    # Missing required fields
    invalid_data = {
        'name': 'Incomplete Strategy',
        # Missing strategy_type, parameters, risk_controls
    }

    response = client.post('/api/v1/strategies', json=invalid_data)

    assert response.status_code == 422
    assert 'application/json' in response.headers['content-type']

    data = response.json()
    assert 'type' in data
    assert 'title' in data
    assert data['status'] == 422


def test_post_strategies_validates_risk_controls():
    """Test POST /api/v1/strategies validates risk control constraints"""

    strategy_data = {
        'name': 'Invalid Risk Strategy',
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'risk_controls': {
            'max_position_size': 1000,
            'max_portfolio_value': 50000,
            'stop_loss_percent': 1.5,  # Invalid: > 1.0
            'max_drawdown_percent': 0.10,
            'daily_loss_limit': 1000,
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    response = client.post('/api/v1/strategies', json=strategy_data)

    assert response.status_code == 422
    data = response.json()
    assert 'invalid_params' in data


def test_post_strategies_unauthorized_without_token():
    """Test POST /api/v1/strategies requires authentication"""

    strategy_data = {
        'name': 'Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'risk_controls': {
            'max_position_size': 1000,
            'max_portfolio_value': 50000,
            'stop_loss_percent': 0.05,
            'max_drawdown_percent': 0.10,
            'daily_loss_limit': 1000,
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    # No Authorization header
    response = client.post('/api/v1/strategies', json=strategy_data)

    assert response.status_code == 401
    data = response.json()
    assert data['status'] == 401
    assert data['title'] == 'Unauthorized'
