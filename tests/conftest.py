"""
shared fixtures for all test suites.

updated to match the refactored domain model (asset type + allocation).
"""
import sys
import os
import pytest

# ensure project root is on the path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.domain.entities.asset import Asset, AssetType, AssetClass
from app.domain.entities.portfolio import Portfolio
from app.domain.value_objects.allocation import Allocation
from app.domain.entities.investor_profile import InvestorProfile, RiskProfile
from app.domain.entities.quiz import QuizQuestion, QuizOption, QuizResponse
from decimal import Decimal


@pytest.fixture
def sample_asset_fixed():
    """a typical fixed income asset (tesouro selic)."""
    return Asset(
        name="Tesouro Selic 2029",
        asset_type=AssetType.TESOURO_SELIC,
        expected_annual_return=0.1475,
        annual_volatility=0.005,
        is_tax_exempt=False,
        min_holding_days=0,
        liquidity_days=1,
        has_fgc=False,
        b3_custody_rate=0.002,
    )


@pytest.fixture
def sample_asset_equity():
    """a typical equity asset (etf ibovespa)."""
    return Asset(
        name="ETF BOVA11",
        asset_type=AssetType.ETF_IBOV,
        expected_annual_return=0.18,
        annual_volatility=0.22,
        is_tax_exempt=False,
        min_holding_days=0,
        liquidity_days=3,
        has_fgc=False,
        b3_custody_rate=0.0,
    )


@pytest.fixture
def sample_portfolio(sample_asset_fixed, sample_asset_equity):
    """a simple 80/20 portfolio using the new model."""
    portfolio = Portfolio(
        name="Test Portfolio",
        total_value=100000.0,
        monthly_expenses=5000.0,
        reserve_months=6,
    )
    portfolio.add_allocation(sample_asset_fixed, 0.8)
    portfolio.add_allocation(sample_asset_equity, 0.2)
    return portfolio


@pytest.fixture
def conservative_profile():
    """an ultraconservative investor profile."""
    return InvestorProfile(
        risk_profile=RiskProfile.CONSERVATIVE,
        investment_horizon_months=36,
        monthly_income=Decimal("5000"),
        initial_amount=Decimal("50000"),
        monthly_contribution=Decimal("500"),
        has_emergency_reserve=True,
        investment_goal="aposentadoria",
        score=35,
    )


@pytest.fixture
def moderate_profile():
    """a moderate investor profile."""
    return InvestorProfile(
        risk_profile=RiskProfile.MODERATE,
        investment_horizon_months=60,
        monthly_income=Decimal("10000"),
        initial_amount=Decimal("100000"),
        monthly_contribution=Decimal("1000"),
        has_emergency_reserve=True,
        investment_goal="patrimônio",
        score=65,
    )


@pytest.fixture
def sample_quiz_responses():
    """a full set of quiz responses (36 answers for the expanded quiz)."""
    return [
        QuizResponse(question_id=f"q{i}", option_id=f"o{i}b")
        for i in range(1, 37)
    ]
