from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

class RiskProfile(str, Enum):
    ULTRACONSERVATIVE = "ultraconservative"
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    ULTRA_AGGRESSIVE = "ultra_aggressive"

@dataclass
class InvestorProfile:
    risk_profile: RiskProfile
    investment_horizon_months: int
    monthly_income: Decimal
    initial_amount: Decimal
    monthly_contribution: Decimal
    has_emergency_reserve: bool
    investment_goal: str
    score: int
    raw_responses: dict | None = None
    user_id: str | None = None
    created_at: datetime | None = None
