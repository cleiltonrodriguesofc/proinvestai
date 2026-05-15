from typing import Dict, List
from ...domain.entities.portfolio import Portfolio
from ..services.markowitz_optimizer import MarkowitzOptimizer
from ..services.monte_carlo_engine import MonteCarloEngine
from ..services.stress_test_engine import StressTestEngine
from ...infrastructure.external.openai_service import AIService

class AnalyzePortfolioUseCase:
    """
    Use Case to perform a complete analysis of a user portfolio.
    """

    def __init__(
        self,
        optimizer: MarkowitzOptimizer,
        monte_carlo: MonteCarloEngine,
        stress_test: StressTestEngine,
        ai_service: AIService
    ):
        self.optimizer = optimizer
        self.monte_carlo = monte_carlo
        self.stress_test = stress_test
        self.ai_service = ai_service

    async def execute(self, current_portfolio: Portfolio, initial_amount: float, target_weights: dict = None, risk_metrics = None, profile_type: str = "Moderado"):
        # 1. Backtest
        backtest_results = self.stress_test.run_backtest(current_portfolio, initial_amount)
        
        # 2. Monte Carlo Simulation
        monte_carlo_results = self.monte_carlo.simulate(current_portfolio, initial_amount)
        
        # 3. AI Narration based on Real Risk Metrics
        # Instead of gap analysis, we do a Committee Technical Review based on risk
        narration = await self.ai_service.explain_committee_review(
            target_weights or {},
            risk_metrics,
            profile_type
        )

        return {
            "backtest": backtest_results,
            "monte_carlo": monte_carlo_results.to_dict(),
            "target_weights": target_weights,
            "narration": narration
        }
