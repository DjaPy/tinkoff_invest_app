"""Health check endpoints for algorithmic trading.

Provides health and readiness checks for the application.
"""

from datetime import datetime
from typing import Any

from src.algo_trading.adapters.models import TradingStrategy


class HealthChecker:
    """
    Health check service for monitoring application status.

    Provides liveness and readiness probes.
    """

    async def check_liveness(self) -> dict[str, Any]:
        """
        Check if application is alive.

        Returns:
            Health status dictionary
        """
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'algo-trading',
        }

    async def check_readiness(self) -> dict[str, Any]:
        """
        Check if application is ready to serve traffic.

        Returns:
            Readiness status dictionary with component checks
        """
        checks = {}

        # Check database connectivity
        db_healthy = await self._check_database()
        checks['database'] = {
            'healthy': db_healthy,
            'message': 'Connected' if db_healthy else 'Not connected',
        }

        # Check if strategies can be queried
        strategies_healthy = await self._check_strategies()
        checks['strategies'] = {
            'healthy': strategies_healthy,
            'message': 'Accessible' if strategies_healthy else 'Not accessible',
        }

        # Overall readiness
        all_healthy = all(check['healthy'] for check in checks.values())

        return {
            'status': 'ready' if all_healthy else 'not_ready',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': checks,
        }

    async def _check_database(self) -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is accessible
        """
        try:
            # Simple ping by counting documents
            await TradingStrategy.count()
            return True
        except Exception:
            return False

    async def _check_strategies(self) -> bool:
        """
        Check if strategies collection is accessible.

        Returns:
            True if strategies can be queried
        """
        try:
            # Try to query strategies
            await TradingStrategy.find().limit(1).to_list()
            return True
        except Exception:
            return False

    async def get_application_info(self) -> dict[str, Any]:
        """
        Get application information.

        Returns:
            Application metadata
        """
        # Count strategies by status
        try:
            total_strategies = await TradingStrategy.count()
            active_strategies = await TradingStrategy.find(
                TradingStrategy.status == 'ACTIVE',
            ).count()
        except Exception:
            total_strategies = 0
            active_strategies = 0

        return {
            'service': 'algo-trading',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {
                'total_strategies': total_strategies,
                'active_strategies': active_strategies,
            },
        }
