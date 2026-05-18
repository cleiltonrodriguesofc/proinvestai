from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.entities.investor_profile import InvestorProfile as DomainProfile, RiskProfile
from ...domain.interfaces.repositories import IProfileRepository
from ..database.models import InvestorProfile as ProfileModel


class SQLAlchemyProfileRepository(IProfileRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_profile(self, profile: DomainProfile) -> DomainProfile:
        model = ProfileModel(
            user_id=profile.user_id,
            risk_profile=profile.risk_profile.value if hasattr(profile.risk_profile, 'value') else profile.risk_profile,
            investment_horizon_months=profile.investment_horizon_months,
            monthly_income=profile.monthly_income,
            initial_amount=profile.initial_amount,
            monthly_contribution=profile.monthly_contribution,
            has_emergency_reserve=profile.has_emergency_reserve,
            investment_goal=profile.investment_goal,
            score=profile.score,
            raw_responses=profile.raw_responses,
            created_at=profile.created_at
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_user(self, user_id: UUID) -> DomainProfile | None:
        query = select(ProfileModel).where(ProfileModel.user_id == user_id).order_by(desc(ProfileModel.created_at)).limit(1)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_latest_by_user(self, user_id: UUID) -> DomainProfile | None:
        query = (
            select(ProfileModel)
            .where(ProfileModel.user_id == user_id)
            .order_by(desc(ProfileModel.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    def _to_domain(self, model: ProfileModel) -> DomainProfile:
        return DomainProfile(
            user_id=str(model.user_id),
            risk_profile=RiskProfile(model.risk_profile),
            investment_horizon_months=int(model.investment_horizon_months),
            monthly_income=model.monthly_income,
            initial_amount=model.initial_amount,
            monthly_contribution=model.monthly_contribution,
            has_emergency_reserve=model.has_emergency_reserve,
            investment_goal=model.investment_goal,
            score=int(model.score),
            raw_responses=model.raw_responses,
            created_at=model.created_at
        )
