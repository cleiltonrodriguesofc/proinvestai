"""
stress test engine — backtests the portfolio against historical crises.

updated to use the new allocation model (alloc.percentage, alloc.asset.asset_class).
"""

import logging
from typing import Dict, List
import numpy as np
from ...domain.entities.portfolio import Portfolio
from ...domain.interfaces.services import IMarketDataService
from .tax_calculator import TaxCalculator

logger = logging.getLogger(__name__)


class StressTestEngine:
    """
    Performs stress testing and backtesting using historical data.
    """

    def __init__(self, bcb_service: IMarketDataService, tax_calculator: TaxCalculator):
        self.bcb_service = bcb_service
        self.tax_calculator = tax_calculator

    def run_backtest(self, portfolio: Portfolio, initial_value: float) -> Dict:
        """
        Runs an empirical backtest using historical returns.
        """
        asset_series = self.bcb_service.build_asset_return_series()
        if not asset_series:
            return {"error": "No historical data available"}

        # extract weights from the new allocation model
        weights = {}
        for alloc in portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            weights[a_class] = weights.get(a_class, 0.0) + float(alloc.percentage)

        # get common months across all series
        first_series = next(iter(asset_series.values()), {})
        if not first_series:
            return {"error": "Empty historical series"}

        all_months = sorted(first_series.keys())
        
        portfolio_returns = []
        for month in all_months:
            month_ret = 0.0
            for a_class, weight in weights.items():
                # map domain asset classes to bcb series keys
                series_key = "fixed_income_post"
                if a_class in ("renda_variavel", "equity"):
                    series_key = "equity"
                elif a_class in ("fii",):
                    series_key = "fii"
                elif a_class in ("internacional",):
                    series_key = "international"
                
                if series_key in asset_series and month in asset_series[series_key]:
                    month_ret += weight * asset_series[series_key][month]
            
            portfolio_returns.append(month_ret)

        if not portfolio_returns:
            return {"error": "No overlapping historical periods"}

        returns_arr = np.array(portfolio_returns)
        growth_factors = np.cumprod(1 + returns_arr)
        equity_curve = initial_value * growth_factors
        
        total_return = (equity_curve[-1] / initial_value) - 1
        max_dd = self._compute_max_drawdown(equity_curve)

        return {
            "total_return": float(total_return),
            "max_drawdown": float(max_dd),
            "annualized_return": float((1 + total_return) ** (12 / max(len(returns_arr), 1)) - 1),
            "volatility": float(np.std(returns_arr) * np.sqrt(12)),
            "negative_months_pct": float(np.mean(returns_arr < 0)),
            "final_value": float(equity_curve[-1])
        }

    def run_crisis_tests(self, portfolio: Portfolio, initial_value: float) -> List[Dict]:
        """
        Tests portfolio against specific historical crises.
        """
        crises = self.bcb_service.get_crisis_periods()
        asset_series = self.bcb_service.build_asset_return_series()
        
        weights = {}
        for alloc in portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            weights[a_class] = weights.get(a_class, 0.0) + float(alloc.percentage)
        
        results = []
        for crisis in crises:
            start, end = crisis["start"], crisis["end"]
            
            period_returns = []
            for a_class, weight in weights.items():
                series_key = "fixed_income_post"
                if a_class in ("renda_variavel", "equity"):
                    series_key = "equity"
                elif a_class in ("fii",):
                    series_key = "fii"
                
                if series_key in asset_series:
                    rets = [v for k, v in asset_series[series_key].items() if start <= k <= end]
                    if rets:
                        period_returns.append(np.array(rets) * weight)
            
            if period_returns:
                portfolio_crisis_rets = np.sum(period_returns, axis=0)
                cumulative_impact = np.prod(1 + portfolio_crisis_rets) - 1
                
                results.append({
                    "name": crisis["name"],
                    "impact": float(cumulative_impact),
                    "severity": crisis["severity"]
                })
        
        return results

    def _compute_max_drawdown(self, curve: np.ndarray) -> float:
        peak = np.maximum.accumulate(curve)
        drawdown = np.where(peak > 0, (peak - curve) / peak, 0)
        return np.max(drawdown)
