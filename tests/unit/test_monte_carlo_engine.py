"""
unit tests for monte carlo simulation engine (task 3.5 / task 6.1).

updated to use the new domain model (AssetType, Portfolio.add_allocation, Allocation).
"""
import pytest
import numpy as np
from app.application.services.monte_carlo_engine import MonteCarloEngine
from app.domain.entities.asset import Asset, AssetType
from app.domain.entities.portfolio import Portfolio
from app.domain.value_objects.simulation_result import SimulationResult


@pytest.fixture
def engine():
    return MonteCarloEngine(seed=42)


@pytest.fixture
def portfolio_with_returns():
    """portfolio using the new entity model."""
    asset_fi = Asset(
        name="Tesouro Selic",
        asset_type=AssetType.TESOURO_SELIC,
        expected_annual_return=0.1475,
        annual_volatility=0.005,
        liquidity_days=1,
    )
    asset_eq = Asset(
        name="BOVA11",
        asset_type=AssetType.ETF_IBOV,
        expected_annual_return=0.18,
        annual_volatility=0.22,
        liquidity_days=3,
    )

    portfolio = Portfolio(
        name="Test MC Portfolio",
        total_value=100000.0,
        monthly_expenses=5000.0,
        reserve_months=6,
    )
    portfolio.add_allocation(asset_fi, 0.7)
    portfolio.add_allocation(asset_eq, 0.3)
    return portfolio


class TestMonteCarloEngine:

    def test_returns_simulation_result(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=100,
        )
        assert isinstance(result, SimulationResult)

    def test_correct_number_of_simulations(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=500,
        )
        assert result.paths.shape[0] == 500

    def test_correct_horizon(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=24,
            num_simulations=100,
        )
        # paths has horizon_months + 1 columns (initial + each month)
        assert result.paths.shape[1] == 25

    def test_initial_value_matches(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=100,
        )
        # all simulations start at the initial amount
        initial_values = result.paths[:, 0]
        assert np.allclose(initial_values, 100000.0, atol=0.01)

    def test_percentiles_computed(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=100,
        )
        assert "p50" in result.percentiles
        assert "mean" in result.percentiles

    def test_percentile_ordering(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=1000,
        )
        p = result.percentiles
        assert p["p5"] <= p["p25"] <= p["p50"] <= p["p75"] <= p["p95"]

    def test_to_dict_serializable(self, engine, portfolio_with_returns):
        result = engine.simulate(
            portfolio_with_returns,
            initial_amount=100000.0,
            horizon_months=12,
            num_simulations=100,
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "paths" not in d  # numpy arrays should not be in the dict

    def test_seed_reproducibility(self, portfolio_with_returns):
        e1 = MonteCarloEngine(seed=123)
        e2 = MonteCarloEngine(seed=123)
        r1 = e1.simulate(portfolio_with_returns, 100000.0, 12, 50)
        r2 = e2.simulate(portfolio_with_returns, 100000.0, 12, 50)
        assert np.allclose(r1.paths, r2.paths)

    def test_monthly_contribution_increases_value(self, engine, portfolio_with_returns):
        """portfolios with monthly contribution should end higher than without."""
        r_no_contrib = engine.simulate(
            portfolio_with_returns, 100000.0, 12, 100, monthly_contribution=0.0
        )
        engine2 = MonteCarloEngine(seed=42)
        r_with_contrib = engine2.simulate(
            portfolio_with_returns, 100000.0, 12, 100, monthly_contribution=1000.0
        )
        # median final value should be higher with contributions
        assert np.median(r_with_contrib.paths[:, -1]) > np.median(r_no_contrib.paths[:, -1])
