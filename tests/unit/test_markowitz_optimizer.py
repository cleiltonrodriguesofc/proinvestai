"""
unit tests for markowitz mean-variance optimizer (task 3.2 / task 6.1).
"""
import pytest
import numpy as np
from app.application.services.markowitz_optimizer import (
    MarkowitzOptimizer,
    OptimizationResult,
    build_optimizer_from_historical,
)


@pytest.fixture
def simple_optimizer():
    """a 3-asset optimizer with known parameters."""
    names = ["tesouro_selic", "cdb_cdi", "etf_bova"]
    expected_returns = np.array([0.10, 0.12, 0.18])
    # simple diagonal-ish covariance (low correlation)
    cov = np.array([
        [0.001, 0.0002, 0.0001],
        [0.0002, 0.002, 0.0003],
        [0.0001, 0.0003, 0.04],
    ])
    categories = {
        "tesouro_selic": "fixed_income",
        "cdb_cdi": "fixed_income",
        "etf_bova": "equity",
    }
    return MarkowitzOptimizer(
        asset_names=names,
        expected_returns=expected_returns,
        covariance_matrix=cov,
        asset_categories=categories,
        risk_free_rate=0.05,
    )


class TestMarkowitzOptimizer:

    def test_weights_sum_to_one(self, simple_optimizer):
        result = simple_optimizer.optimize_min_variance()
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-4

    def test_weights_are_non_negative(self, simple_optimizer):
        result = simple_optimizer.optimize_min_variance()
        for w in result.weights.values():
            assert w >= 0

    def test_result_is_optimization_result(self, simple_optimizer):
        result = simple_optimizer.optimize_min_variance()
        assert isinstance(result, OptimizationResult)

    def test_sharpe_ratio_positive(self, simple_optimizer):
        result = simple_optimizer.optimize_max_sharpe()
        assert result.sharpe_ratio > 0

    def test_min_variance_has_lower_vol_than_equal_weight(self, simple_optimizer):
        opt = simple_optimizer
        min_var = opt.optimize_min_variance()
        # equal weight volatility
        w_eq = np.ones(3) / 3
        vol_eq = opt._portfolio_volatility(w_eq)
        assert min_var.expected_volatility <= vol_eq + 1e-6

    def test_min_return_constraint_respected(self, simple_optimizer):
        result = simple_optimizer.optimize_min_variance(min_return=0.14)
        assert result.expected_return >= 0.14 - 1e-4

    def test_max_sharpe_beats_min_variance_sharpe(self, simple_optimizer):
        min_var = simple_optimizer.optimize_min_variance()
        max_sr = simple_optimizer.optimize_max_sharpe()
        assert max_sr.sharpe_ratio >= min_var.sharpe_ratio - 1e-4


class TestBuildOptimizerFromHistorical:

    def test_builds_from_monthly_returns(self):
        np.random.seed(42)
        historical = {
            "asset_a": np.random.normal(0.008, 0.02, 60),
            "asset_b": np.random.normal(0.01, 0.04, 60),
        }
        categories = {"asset_a": "fixed_income", "asset_b": "equity"}
        opt = build_optimizer_from_historical(historical, categories, risk_free_rate=0.05)
        assert opt.n == 2
        assert len(opt.names) == 2

    def test_annualized_returns_reasonable(self):
        # monthly 0.8% = ~10% annual
        historical = {
            "asset_a": np.full(60, 0.008),
        }
        opt = build_optimizer_from_historical(historical, {"asset_a": "fi"}, 0.0)
        annual = opt.mu[0]
        assert 0.09 < annual < 0.11  # roughly 10%
