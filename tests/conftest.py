"""
shared fixtures for all test suites.
"""
import sys
import os
import pytest
from decimal import Decimal

# ensure project root is on the path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.domain.entities.asset import Asset, AssetClass
from app.domain.entities.portfolio import Portfolio, PortfolioAllocation
from app.domain.entities.investor_profile import InvestorProfile, RiskProfile
from app.domain.entities.quiz import QuizQuestion, QuizOption, QuizResponse


@pytest.fixture
def sample_asset_fixed():
    """a typical fixed income asset."""
    return Asset(
        name="Tesouro Selic 2029",
        asset_class=AssetClass.FIXED_INCOME,
        subclass="tesouro_selic",
        benchmark="CDI",
        spread=Decimal("1.0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=1,
    )


@pytest.fixture
def sample_asset_equity():
    """a typical equity asset."""
    return Asset(
        name="ETF BOVA11",
        asset_class=AssetClass.EQUITY,
        subclass="etf_ibovespa",
        benchmark="IBOV",
        spread=Decimal("0"),
        tax_exempt=False,
        min_investment=Decimal("100"),
        liquidity_days=2,
    )


@pytest.fixture
def sample_portfolio(sample_asset_fixed, sample_asset_equity):
    """a simple 80/20 portfolio."""
    return Portfolio(
        allocations=[
            PortfolioAllocation(asset=sample_asset_fixed, weight=Decimal("0.8")),
            PortfolioAllocation(asset=sample_asset_equity, weight=Decimal("0.2")),
        ],
        expected_return=Decimal("0.11"),
        volatility=Decimal("0.05"),
        sharpe_ratio=Decimal("0.8"),
    )


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
    """a full set of quiz responses (28 answers)."""
    # these map to the quiz_questions.py definitions
    return [
        QuizResponse(question_id=f"q{i}", option_id=f"o{i}b")
        for i in range(1, 29)
    ]
