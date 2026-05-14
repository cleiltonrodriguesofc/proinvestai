from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

class SubscriptionPlan(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"

@dataclass
class User:
    id: UUID
    email: str
    name: str
    hashed_password: str
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    phone: str | None = None
    created_at: datetime | None = None
