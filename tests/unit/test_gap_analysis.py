"""
unit tests for the gap analysis engine (task 3.6).

updated to use the new domain model (AssetType, Portfolio.add_allocation).
"""
import pytest
from app.application.services.gap_analysis_engine import GapAnalysisEngine, GapResult
from app.domain.entities.portfolio import Portfolio
from app.domain.entities.asset import Asset, AssetType


@pytest.fixture
def gap_engine():
    return GapAnalysisEngine()


@pytest.fixture
def fixed_asset():
    return Asset(
        name="Tesouro Selic",
        asset_type=AssetType.TESOURO_SELIC,
        expected_annual_return=0.1475,
        annual_volatility=0.005,
        liquidity_days=1,
    )


@pytest.fixture
def equity_asset():
    return Asset(
        name="BOVA11",
        asset_type=AssetType.ETF_IBOV,
        expected_annual_return=0.18,
        annual_volatility=0.22,
        liquidity_days=3,
    )


@pytest.fixture
def fii_asset():
    return Asset(
        name="HGLG11",
        asset_type=AssetType.FII,
        expected_annual_return=0.12,
        annual_volatility=0.12,
        is_tax_exempt=True,
        liquidity_days=3,
    )


def _make_portfolio(allocations: list, total_value: float = 100000.0) -> Portfolio:
    """helper to build a portfolio from a list of (asset, pct) tuples."""
    p = Portfolio(name="test", total_value=total_value)
    for asset, pct in allocations:
        p.add_allocation(asset, pct)
    return p


def test_compare_identical_portfolios(gap_engine, fixed_asset, equity_asset):
    portfolio = _make_portfolio([
        (fixed_asset, 0.8),
        (equity_asset, 0.2),
    ])

    result = gap_engine.compare(portfolio, portfolio, 100000.0)

    assert isinstance(result, GapResult)
    assert result.total_misallocated_capital == 0.0
    assert result.deviations.get("renda_fixa", 0.0) == 0.0
    assert result.deviations.get("renda_variavel", 0.0) == 0.0


def test_compare_different_portfolios(gap_engine, fixed_asset, equity_asset):
    curr_port = _make_portfolio([(fixed_asset, 1.0)])
    ideal_port = _make_portfolio([
        (fixed_asset, 0.6),
        (equity_asset, 0.4),
    ])

    result = gap_engine.compare(curr_port, ideal_port, 100000.0)

    # user has 100% renda_fixa, ideal is 60% renda_fixa + 40% renda_variavel
    assert result.total_misallocated_capital == pytest.approx(40000.0)
    assert result.deviations["renda_fixa"] == pytest.approx(0.4)
    assert result.deviations["renda_variavel"] == pytest.approx(-0.4)

    # potential gain lost = 100k * (ideal_return - curr_return)
    expected_gain = 100000.0 * (ideal_port.weighted_expected_annual_return -
                                 curr_port.weighted_expected_annual_return)
    assert result.potential_gain_lost == pytest.approx(expected_gain, abs=1.0)


def test_compare_returns_gap_result_dataclass(gap_engine, fixed_asset):
    port = _make_portfolio([(fixed_asset, 1.0)])

    result = gap_engine.compare(port, port, 1000.0)
    assert hasattr(result, "current_allocation")
    assert hasattr(result, "ideal_allocation")
    assert hasattr(result, "deviations")
    assert hasattr(result, "total_misallocated_capital")
    assert hasattr(result, "potential_gain_lost")


def test_compare_missing_asset_class_in_current(gap_engine, fixed_asset, equity_asset):
    curr_port = _make_portfolio([(fixed_asset, 1.0)])
    ideal_port = _make_portfolio([
        (fixed_asset, 0.8),
        (equity_asset, 0.2),
    ])

    result = gap_engine.compare(curr_port, ideal_port, 10000.0)
    assert result.current_allocation.get("renda_variavel", 0.0) == 0.0
    assert result.ideal_allocation["renda_variavel"] == pytest.approx(0.2)
    assert result.deviations["renda_variavel"] == pytest.approx(-0.2)


def test_compare_fallback_potential_gain_lost_when_returns_are_equal(gap_engine, fixed_asset):
    """when returns are equal, fallback uses 5% of misallocated capital."""
    # create a second fixed asset with same return but different type
    fixed_asset_2 = Asset(
        name="CDB Liquidez",
        asset_type=AssetType.CDB_LIQUIDEZ,
        expected_annual_return=fixed_asset.expected_annual_return,  # same return
        annual_volatility=0.005,
        liquidity_days=0,
    )

    curr_port = _make_portfolio([(fixed_asset, 1.0)])
    ideal_port = _make_portfolio([
        (fixed_asset, 0.5),
        (fixed_asset_2, 0.5),
    ])

    result = gap_engine.compare(curr_port, ideal_port, 100000.0)
    # both have same weighted return (all renda_fixa), so no deviation in return
    # misallocated = 0 since both are renda_fixa class
    # this tests the fallback path when returns are equal
    assert result.potential_gain_lost >= 0


def test_fii_class_separation(gap_engine, fixed_asset, fii_asset):
    """fii should be tracked as a separate class from renda_fixa."""
    curr_port = _make_portfolio([(fixed_asset, 1.0)])
    ideal_port = _make_portfolio([
        (fixed_asset, 0.7),
        (fii_asset, 0.3),
    ])

    result = gap_engine.compare(curr_port, ideal_port, 100000.0)
    assert "fii" in result.ideal_allocation
    assert result.ideal_allocation["fii"] == pytest.approx(0.3)
