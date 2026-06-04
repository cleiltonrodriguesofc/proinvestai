from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
import uuid

@dataclass
class RppsInstitute:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    cnpj: str = ""
    name: str = ""
    municipality: str = ""
    state: str = ""
    type_regime: str = "capitalization" # capitalization, simple_repartition, mixed
    total_assets: Decimal = Decimal('0.0')
    actuarial_target_index: str = "IPCA"
    actuarial_target_rate: Decimal = Decimal('0.0') # e.g., 5.5 for 5.5%
    pro_gestao_level: int = 0 # 0 (none) to 4
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class FundPosition:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    rpps_id: uuid.UUID = field(default_factory=uuid.uuid4) # FK
    cnpj_fund: str = ""
    name_fund: str = ""
    segment_cmn: str = "" # Fixed Income, Variable Income, Structured, Real Estate, Exterior
    current_balance: Decimal = Decimal('0.0')
    date_entry: date = field(default_factory=date.today)
    manager_name: str = ""
    admin_name: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class FundQuote:
    """Represents a daily quote from CVM"""
    cnpj_fund: str
    quote_date: date
    nav_per_share: Decimal # Valor da cota
    total_assets: Decimal # Patrimônio líquido
    
@dataclass
class PortfolioSnapshot:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    rpps_id: uuid.UUID = field(default_factory=uuid.uuid4)
    snapshot_date: date = field(default_factory=date.today)
    total_value: Decimal = Decimal('0.0')
    compliance_status: str = "OK" # OK, WARNING, VIOLATION
    positions: List[FundPosition] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
