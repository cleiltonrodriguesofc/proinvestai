"""
allocation value object — immutable representation of a single asset allocation
within a portfolio.

each allocation knows its percentage, absolute value in brl, and expected income.
"""

from dataclasses import dataclass
from ..entities.asset import Asset


@dataclass(frozen=True)
class Allocation:
    """
    value object representing a single allocation within a portfolio.

    attributes:
        asset: the investable product
        percentage: fraction of total portfolio (0.0 to 1.0)
        value: absolute value in brl (R$)
    """

    asset: Asset
    percentage: float
    value: float

    def __post_init__(self):
        if not 0 <= self.percentage <= 1.0 + 1e-6:
            raise ValueError(f"percentage must be between 0 and 1, got {self.percentage}")
        if self.value < 0:
            raise ValueError(f"value must be non-negative, got {self.value}")

    @property
    def expected_monthly_income(self) -> float:
        """expected monthly income from this allocation in brl."""
        return self.value * self.asset.expected_monthly_return

    @property
    def expected_annual_income(self) -> float:
        """expected annual income from this allocation in brl."""
        return self.value * self.asset.expected_annual_return

    @property
    def ir_rate(self) -> float:
        """applicable income tax rate (assumes holding > 2 years = 15%)."""
        if self.asset.is_tax_exempt:
            return 0.0
        return 0.15  # default to lowest bracket (> 720 days)

    def net_annual_return(self, holding_months: int = 24) -> float:
        """
        net annual return after ir regressivo and b3 custody.

        ir brackets:
          0-6 months:   22.50%
          7-12 months:  20.00%
          13-24 months: 17.50%
          25+ months:   15.00%
        """
        if self.asset.is_tax_exempt:
            ir = 0.0
        elif holding_months <= 6:
            ir = 0.225
        elif holding_months <= 12:
            ir = 0.20
        elif holding_months <= 24:
            ir = 0.175
        else:
            ir = 0.15

        gross = self.asset.expected_annual_return
        net = gross * (1 - ir) - self.asset.b3_custody_rate
        return net

    def net_monthly_income(self, holding_months: int = 24) -> float:
        """net monthly income in brl after tax and custody."""
        net_annual = self.net_annual_return(holding_months)
        net_monthly_rate = (1 + net_annual) ** (1 / 12) - 1
        return self.value * net_monthly_rate
