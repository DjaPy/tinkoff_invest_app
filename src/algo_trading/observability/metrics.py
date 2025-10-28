"""Prometheus Metrics for Algorithmic Trading.

Provides observability metrics for trading strategies, orders, and risk management.
"""

from prometheus_client import Counter, Gauge, Histogram

# Strategy Metrics
STRATEGIES_TOTAL = Gauge(
    'algo_trading_strategies_total',
    'Total number of trading strategies',
    ['status'],
)

STRATEGY_STATE_TRANSITIONS = Counter(
    'algo_trading_strategy_state_transitions_total',
    'Total number of strategy state transitions',
    ['from_state', 'to_state'],
)

STRATEGY_LIFECYCLE_DURATION = Histogram(
    'algo_trading_strategy_lifecycle_duration_seconds',
    'Duration of strategy lifecycle events',
    ['event_type'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
)

# Order Metrics
ORDERS_TOTAL = Counter(
    'algo_trading_orders_total',
    'Total number of orders placed',
    ['strategy_id', 'order_type', 'side'],
)

ORDERS_STATUS = Counter(
    'algo_trading_orders_status_total',
    'Total orders by status',
    ['strategy_id', 'status'],
)

ORDER_EXECUTION_DURATION = Histogram(
    'algo_trading_order_execution_duration_seconds',
    'Order execution duration',
    ['order_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
)

ORDER_FILL_PRICE_SLIPPAGE = Histogram(
    'algo_trading_order_fill_price_slippage_percent',
    'Price slippage on order fills',
    ['order_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

# Position Metrics
ACTIVE_POSITIONS = Gauge(
    'algo_trading_active_positions',
    'Number of active positions',
    ['strategy_id', 'instrument'],
)

POSITION_VALUE = Gauge(
    'algo_trading_position_value',
    'Current position value',
    ['strategy_id', 'instrument'],
)

PORTFOLIO_VALUE = Gauge(
    'algo_trading_portfolio_value',
    'Total portfolio value',
    ['strategy_id'],
)

# Risk Metrics
RISK_VIOLATIONS = Counter(
    'algo_trading_risk_violations_total',
    'Total number of risk violations',
    ['strategy_id', 'rule', 'severity'],
)

RISK_CHECKS = Counter(
    'algo_trading_risk_checks_total',
    'Total number of risk checks performed',
    ['strategy_id', 'check_type', 'result'],
)

CURRENT_DRAWDOWN = Gauge(
    'algo_trading_current_drawdown_percent',
    'Current drawdown percentage',
    ['strategy_id'],
)

MAX_DRAWDOWN = Gauge(
    'algo_trading_max_drawdown_percent',
    'Maximum drawdown percentage reached',
    ['strategy_id'],
)

# Performance Metrics
STRATEGY_PNL = Gauge(
    'algo_trading_strategy_pnl',
    'Strategy profit and loss',
    ['strategy_id'],
)

STRATEGY_RETURN = Gauge(
    'algo_trading_strategy_return_percent',
    'Strategy return percentage',
    ['strategy_id'],
)

STRATEGY_SHARPE_RATIO = Gauge(
    'algo_trading_strategy_sharpe_ratio',
    'Strategy Sharpe ratio',
    ['strategy_id'],
)

TRADE_WIN_RATE = Gauge(
    'algo_trading_trade_win_rate_percent',
    'Trade win rate percentage',
    ['strategy_id'],
)

# Session Metrics
ACTIVE_SESSIONS = Gauge(
    'algo_trading_active_sessions',
    'Number of active trading sessions',
)

SESSION_DURATION = Histogram(
    'algo_trading_session_duration_seconds',
    'Trading session duration',
    ['strategy_id'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400],
)

SESSION_ORDERS_TOTAL = Counter(
    'algo_trading_session_orders_total',
    'Total orders placed in session',
    ['strategy_id', 'session_id'],
)

# Market Data Metrics
MARKET_DATA_UPDATES = Counter(
    'algo_trading_market_data_updates_total',
    'Total market data updates received',
    ['instrument', 'timeframe'],
)

MARKET_DATA_LATENCY = Histogram(
    'algo_trading_market_data_latency_seconds',
    'Market data update latency',
    ['source'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2],
)

# API Metrics
API_REQUESTS = Counter(
    'algo_trading_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status'],
)

API_REQUEST_DURATION = Histogram(
    'algo_trading_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

# Backtest Metrics
BACKTEST_RUNS = Counter(
    'algo_trading_backtest_runs_total',
    'Total backtest runs',
    ['strategy_type'],
)

BACKTEST_DURATION = Histogram(
    'algo_trading_backtest_duration_seconds',
    'Backtest execution duration',
    ['strategy_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)


def record_strategy_count(status: str, count: int) -> None:
    """Record total number of strategies by status."""
    STRATEGIES_TOTAL.labels(status=status).set(count)


def record_strategy_transition(from_state: str, to_state: str) -> None:
    """Record a strategy state transition."""
    STRATEGY_STATE_TRANSITIONS.labels(from_state=from_state, to_state=to_state).inc()


def record_order_placed(strategy_id: str, order_type: str, side: str) -> None:
    """Record an order placement."""
    ORDERS_TOTAL.labels(strategy_id=strategy_id, order_type=order_type, side=side).inc()


def record_order_status(strategy_id: str, status: str) -> None:
    """Record an order status change."""
    ORDERS_STATUS.labels(strategy_id=strategy_id, status=status).inc()


def record_risk_violation(strategy_id: str, rule: str, severity: str) -> None:
    """Record a risk violation."""
    RISK_VIOLATIONS.labels(strategy_id=strategy_id, rule=rule, severity=severity).inc()


def record_risk_check(strategy_id: str, check_type: str, result: str) -> None:
    """Record a risk check."""
    RISK_CHECKS.labels(strategy_id=strategy_id, check_type=check_type, result=result).inc()


def update_portfolio_value(strategy_id: str, value: float) -> None:
    """Update portfolio value metric."""
    PORTFOLIO_VALUE.labels(strategy_id=strategy_id).set(value)


def update_strategy_pnl(strategy_id: str, pnl: float) -> None:
    """Update strategy P&L metric."""
    STRATEGY_PNL.labels(strategy_id=strategy_id).set(pnl)


def update_drawdown(strategy_id: str, current: float, max_dd: float) -> None:
    """Update drawdown metrics."""
    CURRENT_DRAWDOWN.labels(strategy_id=strategy_id).set(current)
    MAX_DRAWDOWN.labels(strategy_id=strategy_id).set(max_dd)
