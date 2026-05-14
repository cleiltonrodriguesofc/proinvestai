"""
unit tests for the tax calculator (brazilian investment taxation).
"""
import pytest
from app.application.services.tax_calculator import TaxCalculator, TaxResult


class TestIRRegressiveTable:

    def test_up_to_180_days(self):
        assert TaxCalculator.get_ir_rate(1) == 0.225
        assert TaxCalculator.get_ir_rate(180) == 0.225

    def test_181_to_360_days(self):
        assert TaxCalculator.get_ir_rate(181) == 0.20
        assert TaxCalculator.get_ir_rate(360) == 0.20

    def test_361_to_720_days(self):
        assert TaxCalculator.get_ir_rate(361) == 0.175
        assert TaxCalculator.get_ir_rate(720) == 0.175

    def test_above_720_days(self):
        assert TaxCalculator.get_ir_rate(721) == 0.15
        assert TaxCalculator.get_ir_rate(9999) == 0.15


class TestTaxCalculation:

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_no_gain_no_tax(self):
        result = self.calc.calculate_tax("fixed_income", 0.0, 365)
        assert result.ir_tax == 0
        assert result.net_gain == 0

    def test_negative_gain_no_tax(self):
        result = self.calc.calculate_tax("fixed_income", -100.0, 365)
        assert result.ir_tax == 0

    def test_fixed_income_tax_applied(self):
        result = self.calc.calculate_tax("fixed_income", 1000.0, 365)
        # 361-720 days = 17.5%
        assert result.ir_tax == pytest.approx(175.0)
        assert result.net_gain == pytest.approx(825.0)

    def test_equity_dividend_exempt(self):
        result = self.calc.calculate_tax("equity", 1000.0, 365, is_dividend=True)
        assert result.ir_tax == 0.0

    def test_result_type(self):
        result = self.calc.calculate_tax("fixed_income", 500.0, 100)
        assert isinstance(result, TaxResult)

    def test_effective_rate_correct(self):
        result = self.calc.calculate_tax("fixed_income", 1000.0, 100)
        expected_rate = result.ir_tax / 1000.0
        assert result.effective_tax_rate == pytest.approx(expected_rate)
