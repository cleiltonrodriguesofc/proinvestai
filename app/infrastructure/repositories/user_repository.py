from uuid import UUID
from sqlalchemy import select, update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.entities.user import User as DomainUser, SubscriptionPlan
from ...domain.interfaces.repositories import IUserRepository
from ..database.models import User as UserModel


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: DomainUser) -> DomainUser:
        model = UserModel(
            id=user.id,
            email=user.email,
            name=user.name,
            hashed_password=user.hashed_password,
            phone=user.phone,
            plan=user.plan.value if hasattr(user.plan, 'value') else user.plan,
            created_at=user.created_at
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_email(self, email: str) -> DomainUser | None:
        query = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_id(self, user_id: UUID) -> DomainUser | None:
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def update(self, user: DomainUser) -> DomainUser:
        stmt = (
            sqlalchemy_update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                email=user.email,
                name=user.name,
                hashed_password=user.hashed_password,
                phone=user.phone,
                plan=user.plan.value if hasattr(user.plan, 'value') else user.plan
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return user

    def _to_domain(self, model: UserModel) -> DomainUser:
        return DomainUser(
            id=model.id,
            email=model.email,
            name=model.name,
            hashed_password=model.hashed_password,
            phone=model.phone,
            plan=SubscriptionPlan(model.plan),
            created_at=model.created_at
        )
