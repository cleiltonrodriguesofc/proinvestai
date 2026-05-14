"""
unit tests for domain entities (task 1.x / task 6.1).
"""
import pytest
from decimal import Decimal
from app.domain.entities.asset import Asset, AssetClass
from app.domain.entities.portfolio import Portfolio, PortfolioAllocation
from app.domain.entities.investor_profile import InvestorProfile, RiskProfile
from app.domain.entities.quiz import QuizQuestion, QuizOption, QuizResponse, QuizResult


class TestAssetEntity:

    def test_create_fixed_income(self, sample_asset_fixed):
        assert sample_asset_fixed.asset_class == AssetClass.FIXED_INCOME
        assert sample_asset_fixed.liquidity_days == 1

    def test_create_equity(self, sample_asset_equity):
        assert sample_asset_equity.asset_class == AssetClass.EQUITY

    def test_asset_class_values(self):
        assert AssetClass.FIXED_INCOME.value == "fixed_income"
        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.REAL_ESTATE.value == "real_estate"

    def test_historical_returns_default_none(self):
        a = Asset(
            name="x", asset_class=AssetClass.CASH, subclass="s",
            benchmark="b", spread=Decimal("0"), tax_exempt=False,
            min_investment=Decimal("0"), liquidity_days=0,
        )
        assert a.historical_returns is None


class TestPortfolioEntity:

    def test_allocations_weights_sum(self, sample_portfolio):
        total = sum(float(a.weight) for a in sample_portfolio.allocations)
        assert abs(total - 1.0) < 1e-6

    def test_has_sharpe_ratio(self, sample_portfolio):
        assert sample_portfolio.sharpe_ratio == Decimal("0.8")

    def test_max_drawdown_optional(self):
        p = Portfolio(
            allocations=[], expected_return=Decimal("0"),
            volatility=Decimal("0"), sharpe_ratio=Decimal("0"),
        )
        assert p.max_drawdown is None


class TestInvestorProfileEntity:

    def test_risk_profiles_exist(self):
        profiles = [e.value for e in RiskProfile]
        assert "ultraconservative" in profiles
        assert "conservative" in profiles
        assert "moderate" in profiles
        assert "aggressive" in profiles

    def test_create_profile(self, conservative_profile):
        assert conservative_profile.risk_profile == RiskProfile.CONSERVATIVE
        assert conservative_profile.has_emergency_reserve is True

    def test_raw_responses_optional(self, conservative_profile):
        assert conservative_profile.raw_responses is None

    def test_raw_responses_can_be_set(self):
        p = InvestorProfile(
            risk_profile=RiskProfile.MODERATE,
            investment_horizon_months=60,
            monthly_income=Decimal("5000"),
            initial_amount=Decimal("10000"),
            monthly_contribution=Decimal("500"),
            has_emergency_reserve=True,
            investment_goal="test",
            score=50,
            raw_responses={"q1": "o1a", "q2": "o2b"},
        )
        assert p.raw_responses["q1"] == "o1a"


class TestQuizEntities:

    def test_quiz_option_creation(self):
        o = QuizOption(id="o1", text="test", score=3)
        assert o.score == 3

    def test_quiz_question_creation(self):
        q = QuizQuestion(
            id="q1", text="test?", section="s1",
            options=[QuizOption(id="o1", text="a", score=1)],
        )
        assert len(q.options) == 1

    def test_quiz_response_creation(self):
        r = QuizResponse(question_id="q1", option_id="o1")
        assert r.question_id == "q1"

    def test_quiz_result_creation(self):
        r = QuizResult(
            total_score=55, profile_type="Moderado",
            answers=[], section_scores={"s1": 10},
        )
        assert r.profile_type == "Moderado"
