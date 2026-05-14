from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from uuid import UUID
from .asset import AssetClass

@dataclass
class UserAsset:
    id: UUID
    user_id: UUID
    asset_name: str
    asset_class: AssetClass
    quantity: Decimal
    average_price: Decimal
    purchase_date: date
    ticker: str | None = None
    current_value: Decimal | None = None
