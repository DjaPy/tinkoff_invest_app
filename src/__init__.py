"""
Algorithmic Trading Module

This module provides automated trading capabilities for the Tinkoff Invest App.
It includes strategy management, order execution, risk controls, performance analytics,
and real-time market data processing.

Features:
- Strategy creation and lifecycle management
- Real-time order execution with risk controls
- Performance monitoring and analytics
- Backtesting capabilities
- Market data integration
"""

__version__ = "1.0.0"
__author__ = "Tinkoff Invest App"

from .algo_trading import analytics, api, models, repositories, risk, services

__all__ = ["models", "services", "api", "risk", "analytics", "repositories"]
