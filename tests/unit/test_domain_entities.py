"""
unit tests for domain entities (task 1.x / task 6.1).

updated to match the refactored domain model.
"""
import pytest
from app.domain.entities.asset import Asset, AssetType, AssetClass, ASSET_TYPE_TO_CLASS
from app.domain.entities.portfolio import Portfolio
from app.domain.value_objects.allocation import Allocation
from app.domain.entities.investor_profile import InvestorProfile, RiskProfile
from app.domain.entities.quiz import QuizQuestion, QuizOption, QuizResponse, QuizResult


class TestAssetEntity:

    def test_create_fixed_income(self, sample_asset_fixed):
        assert sample_asset_fixed.asset_class == AssetClass.RENDA_FIXA
        assert sample_asset_fixed.liquidity_days == 1

    def test_create_equity(self, sample_asset_equity):
        assert sample_asset_equity.asset_class == AssetClass.RENDA_VARIAVEL

    def test_asset_class_values(self):
        assert AssetClass.RENDA_FIXA.value == "renda_fixa"
        assert AssetClass.RENDA_VARIAVEL.value == "renda_variavel"
        assert AssetClass.FII.value == "fii"

    def test_asset_type_mapping(self):
        """each asset type maps to the correct class."""
        assert ASSET_TYPE_TO_CLASS[AssetType.TESOURO_SELIC] == AssetClass.RENDA_FIXA
        assert ASSET_TYPE_TO_CLASS[AssetType.ETF_IBOV] == AssetClass.RENDA_VARIAVEL
        assert ASSET_TYPE_TO_CLASS[AssetType.FII] == AssetClass.FII
        assert ASSET_TYPE_TO_CLASS[AssetType.ETF_SP500] == AssetClass.INTERNACIONAL

    def test_monthly_return_conversion(self):
        a = Asset(
            name="test",
            asset_type=AssetType.TESOURO_SELIC,
            expected_annual_return=0.12,
            annual_volatility=0.01,
        )
        monthly = a.expected_monthly_return
        # (1+0.12)^(1/12) - 1 ≈ 0.00949
        assert 0.009 < monthly < 0.01

    def test_risk_category_classification(self):
        low_risk = Asset(name="safe", asset_type=AssetType.TESOURO_SELIC,
                         expected_annual_return=0.10, annual_volatility=0.005)
        assert low_risk.risk_category == "muito_baixo"

        mod_risk = Asset(name="mod", asset_type=AssetType.FII,
                         expected_annual_return=0.12, annual_volatility=0.12)
        assert mod_risk.risk_category == "moderado"

        high_risk = Asset(name="high", asset_type=AssetType.ETF_IBOV,
                          expected_annual_return=0.18, annual_volatility=0.22)
        assert high_risk.risk_category == "alto"

    def test_is_liquid_property(self):
        liquid = Asset(name="l", asset_type=AssetType.TESOURO_SELIC,
                       expected_annual_return=0.10, annual_volatility=0.005,
                       liquidity_days=1)
        assert liquid.is_liquid is True

        illiquid = Asset(name="i", asset_type=AssetType.ETF_IBOV,
                         expected_annual_return=0.18, annual_volatility=0.22,
                         liquidity_days=3)
        assert illiquid.is_liquid is False

    def test_invalid_return_raises(self):
        with pytest.raises(ValueError):
            Asset(name="bad", asset_type=AssetType.TESOURO_SELIC,
                  expected_annual_return=-2.0, annual_volatility=0.01)

    def test_negative_volatility_raises(self):
        with pytest.raises(ValueError):
            Asset(name="bad", asset_type=AssetType.TESOURO_SELIC,
                  expected_annual_return=0.10, annual_volatility=-0.01)


class TestPortfolioEntity:

    def test_allocations_sum_to_one(self, sample_portfolio):
        assert abs(sample_portfolio.total_allocation_pct - 1.0) < 1e-6

    def test_is_fully_allocated(self, sample_portfolio):
        assert sample_portfolio.is_fully_allocated is True

    def test_weighted_return(self, sample_portfolio):
        # 0.8 * 0.1475 + 0.2 * 0.18 = 0.118 + 0.036 = 0.154
        assert abs(sample_portfolio.weighted_expected_annual_return - 0.154) < 0.001

    def test_weighted_volatility(self, sample_portfolio):
        # 0.8 * 0.005 + 0.2 * 0.22 = 0.004 + 0.044 = 0.048
        assert abs(sample_portfolio.weighted_volatility - 0.048) < 0.001

    def test_liquid_percentage(self, sample_portfolio):
        # only tesouro selic (d+1, vol < 2%) qualifies as liquid = 80%
        assert abs(sample_portfolio.liquid_percentage - 0.8) < 0.001

    def test_variable_income_percentage(self, sample_portfolio):
        # only etf ibov qualifies = 20%
        assert abs(sample_portfolio.variable_income_percentage - 0.2) < 0.001

    def test_empty_portfolio(self):
        p = Portfolio(name="empty", total_value=100000.0)
        assert p.total_allocation_pct == 0.0
        assert p.is_fully_allocated is False

    def test_validation_empty_portfolio(self):
        p = Portfolio(name="empty", total_value=100000.0)
        issues = p.validate()
        assert len(issues) > 0

    def test_add_allocation_over_100_raises(self, sample_asset_fixed):
        p = Portfolio(name="test", total_value=100000.0)
        p.add_allocation(sample_asset_fixed, 0.8)
        with pytest.raises(ValueError):
            p.add_allocation(sample_asset_fixed, 0.3)

    def test_class_breakdown(self, sample_portfolio):
        breakdown = sample_portfolio.get_class_breakdown()
        assert "renda_fixa" in breakdown
        assert "renda_variavel" in breakdown
        assert abs(breakdown["renda_fixa"] - 0.8) < 0.001

    def test_allocation_summary_structure(self, sample_portfolio):
        summary = sample_portfolio.get_allocation_summary()
        assert len(summary) == 2
        first = summary[0]
        assert "asset_name" in first
        assert "percentage_display" in first
        assert "value_display" in first
        assert "risk" in first


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
        from decimal import Decimal
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
