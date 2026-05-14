import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Result of a Markowitz optimization."""
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    is_efficient: bool


class MarkowitzOptimizer:
    """
    Markowitz Mean-Variance Optimizer.
    """

    def __init__(
        self,
        asset_names: List[str],
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        asset_categories: Dict[str, str],
        risk_free_rate: float = 0.0,
    ):
        self.n = len(asset_names)
        self.names = asset_names
        self.mu = expected_returns
        self.sigma = covariance_matrix
        self.categories = asset_categories
        self.rf = risk_free_rate

    def _portfolio_return(self, w: np.ndarray) -> float:
        return float(w @ self.mu)

    def _portfolio_variance(self, w: np.ndarray) -> float:
        return float(w @ self.sigma @ w)

    def _portfolio_volatility(self, w: np.ndarray) -> float:
        return float(np.sqrt(self._portfolio_variance(w)))

    def _sharpe_ratio(self, w: np.ndarray) -> float:
        vol = self._portfolio_volatility(w)
        if vol < 1e-10:
            return 0.0
        return (self._portfolio_return(w) - self.rf) / vol

    def optimize_min_variance(
        self,
        min_return: float = None,
        min_liquid_pct: float = 0.0,
        max_variable_income_pct: float = 1.0,
        min_weights: Dict[str, float] = None,
        max_weights: Dict[str, float] = None,
    ) -> OptimizationResult:
        w0 = np.ones(self.n) / self.n
        bounds = []
        for i, name in enumerate(self.names):
            lo = 0.0
            hi = 1.0
            if min_weights and name in min_weights:
                lo = min_weights[name]
            if max_weights and name in max_weights:
                hi = max_weights[name]
            bounds.append((lo, hi))

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        if min_return is not None:
            constraints.append({
                "type": "ineq",
                "fun": lambda w: self._portfolio_return(w) - min_return,
            })

        if min_liquid_pct > 0:
            liquid_mask = np.array([
                1.0 if self.categories.get(name) == "fixed_income" else 0.0 # simplified for now
                for name in self.names
            ])
            constraints.append({
                "type": "ineq",
                "fun": lambda w, m=liquid_mask: float(w @ m) - min_liquid_pct,
            })

        result = minimize(
            self._portfolio_variance,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = {name: max(0, round(float(w), 4)) for name, w in zip(self.names, result.x)}
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total, 4) for k, v in weights.items()}

        w_opt = np.array([weights[n] for n in self.names])

        return OptimizationResult(
            weights=weights,
            expected_return=self._portfolio_return(w_opt),
            expected_volatility=self._portfolio_volatility(w_opt),
            sharpe_ratio=self._sharpe_ratio(w_opt),
            is_efficient=result.success,
        )

    def optimize_max_sharpe(
        self,
        min_liquid_pct: float = 0.0,
        max_variable_income_pct: float = 1.0,
        min_weights: Dict[str, float] = None,
        max_weights: Dict[str, float] = None,
    ) -> OptimizationResult:
        
        def neg_sharpe(w):
            vol = np.sqrt(float(w @ self.sigma @ w))
            if vol < 1e-10:
                return 0.0
            return -(float(w @ self.mu) - self.rf) / vol

        w0 = np.ones(self.n) / self.n
        bounds = [(0, 1) for _ in range(self.n)] # simplified bounds
        
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        result = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        weights = {name: max(0, round(float(w), 4)) for name, w in zip(self.names, result.x)}
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total, 4) for k, v in weights.items()}

        w_opt = np.array([weights[n] for n in self.names])

        return OptimizationResult(
            weights=weights,
            expected_return=self._portfolio_return(w_opt),
            expected_volatility=self._portfolio_volatility(w_opt),
            sharpe_ratio=self._sharpe_ratio(w_opt),
            is_efficient=result.success,
        )


def build_optimizer_from_historical(
    historical_returns: Dict[str, np.ndarray],
    asset_categories: Dict[str, str],
    risk_free_rate: float = 0.0,
) -> MarkowitzOptimizer:
    names = list(historical_returns.keys())
    n = len(names)
    min_len = min(len(v) for v in historical_returns.values())
    returns_matrix = np.column_stack([
        historical_returns[name][:min_len] for name in names
    ])

    monthly_means = np.mean(returns_matrix, axis=0)
    annual_returns = (1 + monthly_means) ** 12 - 1
    monthly_cov = np.cov(returns_matrix, rowvar=False)
    annual_cov = monthly_cov * 12

    return MarkowitzOptimizer(
        asset_names=names,
        expected_returns=annual_returns,
        covariance_matrix=annual_cov,
        asset_categories=asset_categories,
        risk_free_rate=risk_free_rate,
    )
