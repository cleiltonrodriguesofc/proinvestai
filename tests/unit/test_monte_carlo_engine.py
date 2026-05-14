"""
unit tests for monte carlo simulation engine (task 3.5 / task 6.1).
"""
import pytest
import numpy as np
from decimal import Decimal
from app.application.services.monte_carlo_engine import MonteCarloEngine
from app.domain.entities.asset import Asset, AssetClass
from app.domain.entities.portfolio import Portfolio, PortfolioAllocation
from app.domain.value_objects.simulation_result import SimulationResult


@pytest.fixture
def engine():
    return MonteCarloEngine(seed=42)


@pytest.fixture
def portfolio_with_returns():
    """portfolio with historical returns on assets."""
    asset_fi = Asset(
        name="Tesouro Selic",
        asset_class=AssetClass.FIXED_INCOME,
        subclass="tesouro_selic",
        benchmark="CDI",
        spread=Decimal("1.0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=1,
        historical_returns=[Decimal("0.008")] * 60,
    )
    asset_eq = Asset(
        name="BOVA11",
        asset_class=AssetClass.EQUITY,
        subclass="etf",
        benchmark="IBOV",
        spread=Decimal("0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=2,
        historical_returns=[Decimal("0.01")] * 60,
    )
    return Portfolio(
        allocations=[
            PortfolioAllocation(asset=asset_fi, weight=Decimal("0.7")),
            PortfolioAllocation(asset=asset_eq, weight=Decimal("0.3")),
        ],
        expected_return=Decimal("0.11"),
        volatility=Decimal("0.05"),
        sharpe_ratio=Decimal("0.8"),
    )


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
