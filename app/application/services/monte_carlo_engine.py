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

        # Extract asset parameters
        # In this new project, we need to handle the returns properly.
        # We'll assume the portfolio already has expected_return and volatility calculated
        # But for Monte Carlo, it's better to simulate asset by asset if we have correlations.
        
        # If we don't have per-asset expected returns in the entity yet, 
        # we might need to compute them from historical_returns or pass them.
        # For now, let's use the portfolio level metrics as a fallback or 
        # assume assets have been populated with expected metrics.

        # Let's assume we use the portfolio's expected_return and volatility for a aggregate GBM
        # if we don't want to get into per-asset details right now, or if they are missing.
        
        # However, the old code did per-asset. Let's see if we can do that.
        # Current Asset entity doesn't have expected_return field, but it has historical_returns.
        
        mu_list = []
        sigma_list = []
        weights = []
        
        for alloc in portfolio.allocations:
            # Simple estimation if historical_returns exist
            if alloc.asset.historical_returns and len(alloc.asset.historical_returns) > 0:
                rets = [float(r) for r in alloc.asset.historical_returns]
                mu_list.append(np.mean(rets))
                sigma_list.append(np.std(rets))
            else:
                # Fallbacks (should be replaced by real data service later)
                mu_list.append(0.008) # 0.8% month
                sigma_list.append(0.02) # 2% month
            
            weights.append(float(alloc.weight))

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
