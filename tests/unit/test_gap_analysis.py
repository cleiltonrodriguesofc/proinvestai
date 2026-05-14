"""
Unit tests for the Gap Analysis Engine (Task 3.6).
"""
import pytest
from decimal import Decimal
from app.application.services.gap_analysis_engine import GapAnalysisEngine, GapResult
from app.domain.entities.portfolio import Portfolio, PortfolioAllocation
from app.domain.entities.asset import Asset, AssetClass

@pytest.fixture
def gap_engine():
    return GapAnalysisEngine()

@pytest.fixture
def fixed_asset():
    return Asset(
        name="Tesouro Selic",
        asset_class=AssetClass.FIXED_INCOME,
        subclass="post",
        benchmark="CDI",
        spread=Decimal("0.0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=1
    )

@pytest.fixture
def equity_asset():
    return Asset(
        name="BOVA11",
        asset_class=AssetClass.EQUITY,
        subclass="etf",
        benchmark="IBOV",
        spread=Decimal("0.0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=2
    )

@pytest.fixture
def real_estate_asset():
    return Asset(
        name="HGLG11",
        asset_class=AssetClass.REAL_ESTATE,
        subclass="fii",
        benchmark="IFIX",
        spread=Decimal("0.0"),
        tax_exempt=True,
        min_investment=Decimal("100"),
        liquidity_days=2
    )

def test_compare_identical_portfolios(gap_engine, fixed_asset, equity_asset):
    allocations = [
        PortfolioAllocation(asset=fixed_asset, weight=Decimal("0.8")),
        PortfolioAllocation(asset=equity_asset, weight=Decimal("0.2")),
    ]
    portfolio = Portfolio(allocations=allocations, expected_return=Decimal("0.1"), volatility=Decimal("0.05"), sharpe_ratio=Decimal("0.5"))
    
    result = gap_engine.compare(portfolio, portfolio, 10000.0)
    
    assert isinstance(result, GapResult)
    assert result.total_misallocated_capital == 0.0
    assert result.deviations["fixed_income"] == 0.0
    assert result.deviations["equity"] == 0.0

def test_compare_different_portfolios(gap_engine, fixed_asset, equity_asset, real_estate_asset):
    curr_alloc = [
        PortfolioAllocation(asset=fixed_asset, weight=Decimal("1.0")),
    ]
    curr_port = Portfolio(allocations=curr_alloc, expected_return=Decimal("0.10"), volatility=Decimal("0.05"), sharpe_ratio=Decimal("0.5"))
    
    ideal_alloc = [
        PortfolioAllocation(asset=fixed_asset, weight=Decimal("0.6")),
        PortfolioAllocation(asset=equity_asset, weight=Decimal("0.4")),
    ]
    ideal_port = Portfolio(allocations=ideal_alloc, expected_return=Decimal("0.15"), volatility=Decimal("0.10"), sharpe_ratio=Decimal("0.8"))
    
    # User has 100% fixed, ideal is 60% fixed / 40% equity. Total misallocated = 40%
    result = gap_engine.compare(curr_port, ideal_port, 100000.0)
    
    assert result.total_misallocated_capital == 40000.0 # 40% of 100k
    assert result.deviations["fixed_income"] == pytest.approx(0.4) # 1.0 - 0.6
    assert result.deviations["equity"] == pytest.approx(-0.4) # 0.0 - 0.4
    assert result.potential_gain_lost == pytest.approx(5000.0) # 100k * (0.15 - 0.10)

def test_compare_returns_gap_result_dataclass(gap_engine, fixed_asset):
    alloc = [PortfolioAllocation(asset=fixed_asset, weight=Decimal("1.0"))]
    port = Portfolio(allocations=alloc, expected_return=Decimal("0.1"), volatility=Decimal("0.05"), sharpe_ratio=Decimal("0.5"))
    
    result = gap_engine.compare(port, port, 1000.0)
    assert hasattr(result, "current_allocation")
    assert hasattr(result, "ideal_allocation")
    assert hasattr(result, "deviations")
    assert hasattr(result, "total_misallocated_capital")
    assert hasattr(result, "potential_gain_lost")

def test_compare_missing_asset_class_in_current(gap_engine, fixed_asset, equity_asset):
    curr_alloc = [PortfolioAllocation(asset=fixed_asset, weight=Decimal("1.0"))]
    curr_port = Portfolio(allocations=curr_alloc, expected_return=Decimal("0.10"), volatility=Decimal("0.05"), sharpe_ratio=Decimal("0.5"))
    
    ideal_alloc = [
        PortfolioAllocation(asset=fixed_asset, weight=Decimal("0.8")),
        PortfolioAllocation(asset=equity_asset, weight=Decimal("0.2")),
    ]
    ideal_port = Portfolio(allocations=ideal_alloc, expected_return=Decimal("0.12"), volatility=Decimal("0.08"), sharpe_ratio=Decimal("0.6"))
    
    result = gap_engine.compare(curr_port, ideal_port, 10000.0)
    assert result.current_allocation.get("equity", 0.0) == 0.0
    assert result.ideal_allocation["equity"] == 0.2
    assert result.deviations["equity"] == pytest.approx(-0.2)

def test_compare_fallback_potential_gain_lost_when_returns_are_equal(gap_engine, fixed_asset, equity_asset):
    curr_alloc = [PortfolioAllocation(asset=fixed_asset, weight=Decimal("1.0"))]
    curr_port = Portfolio(allocations=curr_alloc, expected_return=Decimal("0.10"), volatility=Decimal("0.05"), sharpe_ratio=Decimal("0.5"))
    
    ideal_alloc = [
        PortfolioAllocation(asset=fixed_asset, weight=Decimal("0.5")),
        PortfolioAllocation(asset=equity_asset, weight=Decimal("0.5")),
    ]
    # Expected return is the same, so no direct "opportunity cost" by simple return diff
    ideal_port = Portfolio(allocations=ideal_alloc, expected_return=Decimal("0.10"), volatility=Decimal("0.08"), sharpe_ratio=Decimal("0.6"))
    
    result = gap_engine.compare(curr_port, ideal_port, 100000.0)
    # Misallocated is 50% = 50000. Fallback uses 5% of misallocated = 2500
    assert result.potential_gain_lost == pytest.approx(2500.0)
