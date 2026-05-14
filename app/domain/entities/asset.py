from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

class AssetClass(str, Enum):
    FIXED_INCOME = "fixed_income"
    EQUITY = "equity"
    REAL_ESTATE = "real_estate"
    INTERNATIONAL = "international"
    CASH = "cash"

@dataclass
class Asset:
    name: str
    asset_class: AssetClass
    subclass: str
    benchmark: str
    spread: Decimal
    tax_exempt: bool
    min_investment: Decimal
    liquidity_days: int
    ticker: str | None = None
    historical_returns: list[Decimal] | None = None
