import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, JSON, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    plan = Column(String, default="free", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    profiles = relationship("InvestorProfile", back_populates="user")
    assets = relationship("UserAsset", back_populates="user")
    simulations = relationship("Simulation", back_populates="user")
    rpps_institutes = relationship("RppsInstitute", back_populates="user")

class InvestorProfile(Base):
    __tablename__ = "investor_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    risk_profile = Column(String, nullable=False)
    investment_horizon_months = Column(Numeric, nullable=False)
    monthly_income = Column(Numeric, nullable=False)
    initial_amount = Column(Numeric, nullable=False)
    monthly_contribution = Column(Numeric, nullable=False)
    has_emergency_reserve = Column(Boolean, default=False)
    investment_goal = Column(String, nullable=True)
    score = Column(Numeric, nullable=False)
    raw_responses = Column(JSON, nullable=True) # stores the 28 answers
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="profiles")

class UserAsset(Base):
    __tablename__ = "user_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    asset_name = Column(String, nullable=False)
    asset_class = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    quantity = Column(Numeric, nullable=False)
    average_price = Column(Numeric, nullable=False)
    purchase_date = Column(Date, nullable=False)
    current_value = Column(Numeric, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="assets")

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("investor_profiles.id"), nullable=False)
    result_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="simulations")

class RppsInstitute(Base):
    __tablename__ = "rpps_institutes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cnpj = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    municipality = Column(String, nullable=False)
    state = Column(String, nullable=False)
    type_regime = Column(String, default="capitalization", nullable=False)
    total_assets = Column(Numeric, default=0.0)
    actuarial_target_index = Column(String, default="IPCA")
    actuarial_target_rate = Column(Numeric, default=0.0)
    pro_gestao_level = Column(Numeric, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="rpps_institutes")
    positions = relationship("FundPosition", back_populates="institute")
    snapshots = relationship("PortfolioSnapshot", back_populates="institute")

class FundPosition(Base):
    __tablename__ = "fund_positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rpps_id = Column(UUID(as_uuid=True), ForeignKey("rpps_institutes.id"), nullable=False)
    cnpj_fund = Column(String, index=True, nullable=False)
    name_fund = Column(String, nullable=False)
    segment_cmn = Column(String, nullable=False)
    regulatory_article = Column(String, nullable=True)  # e.g. "7, I"
    benchmark = Column(String, nullable=True)            # e.g. "IMA-B"
    current_balance = Column(Numeric, default=0.0)
    weight_pct = Column(Numeric, default=0.0)            # participation %
    liquidity_days = Column(Numeric, default=0)          # D+0, D+1, D+3
    monthly_return_pct = Column(Numeric, nullable=True)  # latest month return %
    admin_fee_pct = Column(Numeric, nullable=True)       # taxa de administração %
    is_legacy = Column(Boolean, default=False)           # fundos legados
    maturity_date = Column(Date, nullable=True)          # vencimento (se aplicável)
    date_entry = Column(Date, nullable=True)
    manager_name = Column(String, nullable=True)
    admin_name = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    institute = relationship("RppsInstitute", back_populates="positions")
    
class FundQuote(Base):
    __tablename__ = "fund_quotes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cnpj_fund = Column(String, index=True, nullable=False)
    quote_date = Column(Date, nullable=False)
    nav_per_share = Column(Numeric, nullable=False)
    total_assets = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rpps_id = Column(UUID(as_uuid=True), ForeignKey("rpps_institutes.id"), nullable=False)
    snapshot_date = Column(Date, default=lambda: datetime.now(timezone.utc).date())
    total_value = Column(Numeric, default=0.0)
    compliance_status = Column(String, default="OK")
    positions_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    institute = relationship("RppsInstitute", back_populates="snapshots")
