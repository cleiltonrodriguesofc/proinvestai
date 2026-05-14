from typing import Dict, Any
from ...domain.entities.portfolio import Portfolio
from ..services.stress_test_engine import StressTestEngine

class RunBacktestUseCase:
    """
    Use case to run an empirical historical backtest of a portfolio.
    """
    def __init__(self, stress_test_engine: StressTestEngine):
        self.stress_test_engine = stress_test_engine

    def execute(self, portfolio: Portfolio, initial_amount: float) -> Dict[str, Any]:
        """
        Runs a backtest and returns metrics (total return, max drawdown, volatility, etc).
        """
        results = self.stress_test_engine.run_backtest(portfolio, initial_amount)
        return results
