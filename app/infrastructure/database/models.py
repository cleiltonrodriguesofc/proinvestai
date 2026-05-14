import uuid
from datetime import datetime
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
