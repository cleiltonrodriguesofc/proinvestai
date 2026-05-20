from typing import Optional
import numpy as np
from ...domain.entities.portfolio import Portfolio
from ...domain.value_objects.simulation_result import SimulationResult


class MonteCarloEngine:
    """
    Monte Carlo simulation engine using Geometric Brownian Motion.
    Supports correlated multi-asset portfolios.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: random seed for reproducibility
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def simulate(
        self,
        portfolio: Portfolio,
        initial_amount: float,
        horizon_months: int = 60,
        num_simulations: int = 5000,
        monthly_contribution: float = 0.0,
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation with GBM for a portfolio.
        """
        n_assets = len(portfolio.allocations)
        dt = 1.0  # monthly time step

        # extract per-asset monthly return and volatility from the new entity model
        mu_list = []
        sigma_list = []
        weights = []
        
        for alloc in portfolio.allocations:
            mu_list.append(float(alloc.asset.expected_monthly_return))
            sigma_list.append(float(alloc.asset.monthly_volatility))
            weights.append(float(alloc.percentage))

        mu = np.array(mu_list)
        sigma = np.array(sigma_list)
        weights = np.array(weights)
        initial_values = weights * initial_amount

        # Generate correlated random draws
        if correlation_matrix is not None and n_assets > 1:
            chol = np.linalg.cholesky(correlation_matrix)
            z = self.rng.standard_normal((num_simulations, horizon_months, n_assets))
            correlated_z = np.einsum("ijk,lk->ijl", z, chol)
        else:
            correlated_z = self.rng.standard_normal(
                (num_simulations, horizon_months, n_assets)
            )

        asset_paths = np.zeros((num_simulations, horizon_months + 1, n_assets))
        asset_paths[:, 0, :] = initial_values

        for t in range(horizon_months):
            drift = (mu - 0.5 * sigma**2) * dt
            diffusion = sigma * np.sqrt(dt) * correlated_z[:, t, :]
            asset_paths[:, t + 1, :] = asset_paths[:, t, :] * np.exp(
                drift + diffusion
            )
            # Add monthly contribution
            if monthly_contribution > 0:
                asset_paths[:, t + 1, :] += monthly_contribution * weights

        portfolio_paths = np.sum(asset_paths, axis=2)
        monthly_returns = np.diff(portfolio_paths, axis=1) / portfolio_paths[:, :-1]

        result = SimulationResult(
            scenario_name="Custom Portfolio",
            simulation_type="monte_carlo_gbm",
            num_simulations=num_simulations,
            horizon_months=horizon_months,
            paths=portfolio_paths,
            monthly_returns=monthly_returns,
        )
        result.compute_percentiles()

        return result
