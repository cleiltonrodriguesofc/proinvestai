import numpy as np
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
        
        # Calculate percentile paths for the UI chart
        p10_path = np.percentile(monte_carlo_results.paths, 10, axis=0).tolist()
        p50_path = np.percentile(monte_carlo_results.paths, 50, axis=0).tolist()
        p90_path = np.percentile(monte_carlo_results.paths, 90, axis=0).tolist()
        
        mc_dict = monte_carlo_results.to_dict()
        mc_dict["p10_path"] = p10_path
        mc_dict["p50_path"] = p50_path
        mc_dict["p90_path"] = p90_path
        
        # 3. AI Narration based on Real Risk Metrics
        narration = await self.ai_service.explain_committee_review(
            target_weights or {},
            risk_metrics,
            profile_type
        )

        return {
            "backtest": backtest_results,
            "monte_carlo": mc_dict,
            "target_weights": target_weights,
            "narration": narration
        }
