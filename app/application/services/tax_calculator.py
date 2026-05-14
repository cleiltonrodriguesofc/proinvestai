from dataclasses import dataclass
from enum import Enum


class TaxRegime(str, Enum):
    REGRESSIVE_IR = "regressive_ir"
    EXEMPT = "exempt"
    FII_DIVIDENDS = "fii_dividends"
    ETF_GAINS = "etf_gains"


@dataclass
class TaxResult:
    gross_gain: float
    ir_tax: float
    iof_tax: float
    net_gain: float
    effective_tax_rate: float


class TaxCalculator:
    """
    Calculates taxes for Brazilian investments.
    """

    @staticmethod
    def get_ir_rate(holding_days: int) -> float:
        if holding_days <= 180:
            return 0.225
        if holding_days <= 360:
            return 0.20
        if holding_days <= 720:
            return 0.175
        return 0.15

    def calculate_tax(
        self,
        asset_class: str,
        gross_gain: float,
        holding_days: int,
        is_dividend: bool = False
    ) -> TaxResult:
        if gross_gain <= 0:
            return TaxResult(gross_gain, 0, 0, gross_gain, 0)

        # Simplified logic for this stage
        if asset_class == "fixed_income":
            ir_rate = self.get_ir_rate(holding_days)
            ir_tax = gross_gain * ir_rate
        elif asset_class == "equity" and is_dividend:
            ir_tax = 0.0 # Exempt dividends
        else:
            ir_tax = gross_gain * 0.15 # Generic 15%

        net_gain = gross_gain - ir_tax
        return TaxResult(
            gross_gain=gross_gain,
            ir_tax=ir_tax,
            iof_tax=0.0,
            net_gain=net_gain,
            effective_tax_rate=ir_tax / gross_gain if gross_gain > 0 else 0
        )
