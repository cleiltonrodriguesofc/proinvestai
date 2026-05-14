from dataclasses import dataclass
from decimal import Decimal
from .asset import Asset

@dataclass
class PortfolioAllocation:
    asset: Asset
    weight: Decimal  # 0.0 to 1.0

@dataclass
class Portfolio:
    allocations: list[PortfolioAllocation]
    expected_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal | None = None
