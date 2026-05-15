"""
portfolio entity — a collection of allocated assets with business logic.

this is NOT a thin dataclass. it calculates weighted returns, income projections,
risk metrics, validates constraints, and provides allocation summaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .asset import Asset, AssetClass
from ..value_objects.allocation import Allocation


@dataclass
class Portfolio:
    """
    represents an investment portfolio with allocated assets.

    attributes:
        name: portfolio name (e.g. "carteira conservadora")
        total_value: total capital invested in brl
        allocations: list of asset allocations
        monthly_expenses: investor's monthly expenses (for reserve calculation)
        reserve_months: emergency reserve target in months
        rebalancing_months: how often to rebalance
        description: portfolio description / strategy rationale
    """

    name: str
    total_value: float
    allocations: List[Allocation] = field(default_factory=list)
    monthly_expenses: float = 0.0
    reserve_months: int = 6
    rebalancing_months: int = 3
    description: str = ""

    # ── allocation properties ──

    @property
    def total_allocation_pct(self) -> float:
        """sum of all allocation percentages."""
        return sum(a.percentage for a in self.allocations)

    @property
    def is_fully_allocated(self) -> bool:
        """check if allocations sum to ~100%."""
        return abs(self.total_allocation_pct - 1.0) < 1e-4

    # ── return properties ──

    @property
    def weighted_expected_annual_return(self) -> float:
        """portfolio expected annual return (weighted average, gross)."""
        return sum(
            a.percentage * a.asset.expected_annual_return for a in self.allocations
        )

    @property
    def weighted_expected_monthly_return(self) -> float:
        """portfolio expected monthly return (compound)."""
        return (1 + self.weighted_expected_annual_return) ** (1 / 12) - 1

    @property
    def expected_monthly_income(self) -> float:
        """expected gross monthly income in brl."""
        return sum(a.expected_monthly_income for a in self.allocations)

    @property
    def expected_annual_income(self) -> float:
        """expected gross annual income in brl."""
        return sum(a.expected_annual_income for a in self.allocations)

    def expected_net_monthly_income(self, holding_months: int = 24) -> float:
        """expected net monthly income in brl after ir and custody."""
        return sum(a.net_monthly_income(holding_months) for a in self.allocations)

    def expected_net_annual_return(self, holding_months: int = 24) -> float:
        """portfolio weighted net annual return after ir and custody."""
        return sum(
            a.percentage * a.net_annual_return(holding_months)
            for a in self.allocations
        )

    # ── risk properties ──

    @property
    def weighted_volatility(self) -> float:
        """
        simplified portfolio volatility.
        assumes +1 correlation for fixed income (conservative estimate).
        for mixed portfolios, this overstates vol — acceptable for risk warning.
        """
        return sum(
            a.percentage * a.asset.annual_volatility
            for a in self.allocations
        )

    @property
    def risk_category(self) -> str:
        """classify portfolio risk based on overall volatility."""
        vol = self.weighted_volatility
        if vol <= 0.02:
            return "ultraconservador"
        elif vol <= 0.05:
            return "conservador"
        elif vol <= 0.10:
            return "moderado"
        elif vol <= 0.20:
            return "arrojado"
        else:
            return "agressivo"

    # ── composition properties ──

    @property
    def liquid_percentage(self) -> float:
        """percentage of portfolio in liquid assets (d+0 or d+1, low vol)."""
        return sum(a.percentage for a in self.allocations if a.asset.is_liquid)

    @property
    def liquid_value(self) -> float:
        """absolute value in liquid assets (brl)."""
        return sum(a.value for a in self.allocations if a.asset.is_liquid)

    @property
    def variable_income_percentage(self) -> float:
        """percentage in renda variavel + fii + internacional + alternativo."""
        return sum(
            a.percentage for a in self.allocations
            if a.asset.is_variable_income
        )

    @property
    def fgc_protected_value(self) -> float:
        """total value protected by fgc (limit r$250k per institution)."""
        return sum(
            min(a.value, 250_000.0) for a in self.allocations
            if a.asset.has_fgc
        )

    @property
    def tax_exempt_percentage(self) -> float:
        """percentage in tax-exempt assets (lci, lca, fii dividends, debentures)."""
        return sum(a.percentage for a in self.allocations if a.asset.is_tax_exempt)

    @property
    def reserve_coverage_months(self) -> float:
        """how many months of expenses the liquid assets can cover."""
        if self.monthly_expenses <= 0:
            return float('inf')
        return self.liquid_value / self.monthly_expenses

    # ── mutation ──

    def add_allocation(self, asset: Asset, percentage: float) -> None:
        """add an asset allocation to the portfolio."""
        if percentage < 0 or percentage > 1:
            raise ValueError(f"percentage must be between 0 and 1, got {percentage}")

        if self.total_allocation_pct + percentage > 1.0 + 1e-4:
            raise ValueError(
                f"total allocation would exceed 100%: "
                f"current={self.total_allocation_pct:.2%}, adding={percentage:.2%}"
            )

        allocation = Allocation(
            asset=asset,
            percentage=percentage,
            value=self.total_value * percentage,
        )
        self.allocations.append(allocation)

    # ── summaries ──

    def get_allocation_summary(self) -> List[Dict]:
        """return a detailed summary of all allocations for the frontend."""
        return [
            {
                "asset_name": a.asset.name,
                "asset_type": a.asset.asset_type.value,
                "asset_class": a.asset.asset_class.value,
                "percentage": a.percentage,
                "percentage_display": f"{a.percentage:.1%}",
                "value": a.value,
                "value_display": f"R$ {a.value:,.2f}",
                "gross_annual_return": a.asset.expected_annual_return,
                "gross_return_display": f"{a.asset.expected_annual_return:.2%}",
                "net_annual_return": a.net_annual_return(24),
                "net_return_display": f"{a.net_annual_return(24):.2%}",
                "net_monthly_income": a.net_monthly_income(24),
                "net_income_display": f"R$ {a.net_monthly_income(24):,.2f}",
                "is_tax_exempt": a.asset.is_tax_exempt,
                "tax_label": "Isento" if a.asset.is_tax_exempt else "IR Regressivo",
                "liquidity": f"D+{a.asset.liquidity_days}",
                "risk": a.asset.risk_label,
                "has_fgc": a.asset.has_fgc,
                "description": a.asset.description,
            }
            for a in self.allocations
        ]

    def get_class_breakdown(self) -> Dict[str, float]:
        """return allocation breakdown by asset class."""
        breakdown = {}
        for a in self.allocations:
            cls = a.asset.asset_class.value
            breakdown[cls] = breakdown.get(cls, 0.0) + a.percentage
        return breakdown

    # ── validation ──

    def validate(self) -> List[str]:
        """validate portfolio constraints, return list of issues."""
        issues = []
        if not self.is_fully_allocated:
            issues.append(
                f"carteira nao esta 100% alocada: {self.total_allocation_pct:.1%}"
            )
        if self.total_value <= 0:
            issues.append("valor total deve ser positivo")
        if not self.allocations:
            issues.append("carteira nao tem alocacoes")
        if self.monthly_expenses > 0:
            target_reserve = self.monthly_expenses * self.reserve_months
            if self.liquid_value < target_reserve * 0.9:
                issues.append(
                    f"reserva de emergencia insuficiente: "
                    f"R$ {self.liquid_value:,.0f} vs meta R$ {target_reserve:,.0f} "
                    f"({self.reserve_months} meses)"
                )
        return issues
