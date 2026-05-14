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

    async def execute(self, current_portfolio: Portfolio, initial_amount: float):
        # 1. Backtest
        backtest_results = self.stress_test.run_backtest(current_portfolio, initial_amount)
        
        # 2. Monte Carlo Simulation
        monte_carlo_results = self.monte_carlo.simulate(current_portfolio, initial_amount)
        
        # 3. Optimization (Ideal Portfolio)
        # For simplicity, we assume we want to compare with a Max Sharpe portfolio
        # We'd need historical returns for all candidate assets to run Markowitz properly
        # In this step, we'll mock the 'ideal' weights for comparison
        ideal_weights = {
            "fixed_income": 0.60,
            "equity": 0.25,
            "real_estate": 0.10,
            "international": 0.05
        }
        
        current_weights = {}
        for alloc in current_portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            current_weights[a_class] = current_weights.get(a_class, 0) + float(alloc.weight)

        # 4. Gap Analysis Calculation
        # Estimate lost gain (example logic: 2% difference on misallocated capital)
        misallocated_capital = initial_amount * 0.15 # 15% deviation
        potential_gain_lost = misallocated_capital * 0.05 # 5% per year
        
        # 5. AI Narration
        narration = await self.ai_service.explain_gap(
            current_weights,
            ideal_weights,
            None # Optional profile
        )

        return {
            "backtest": backtest_results,
            "monte_carlo": monte_carlo_results.to_dict(),
            "ideal_weights": ideal_weights,
            "current_weights": current_weights,
            "potential_gain_lost": potential_gain_lost,
            "narration": narration
        }
