from uuid import UUID
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.entities.user_asset import UserAsset as DomainAsset
from ...domain.entities.asset import AssetClass
from ...domain.interfaces.repositories import IUserAssetRepository
from ..database.models import UserAsset as AssetModel


class SQLAlchemyUserAssetRepository(IUserAssetRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, asset: DomainAsset) -> DomainAsset:
        model = AssetModel(
            id=asset.id,
            user_id=asset.user_id,
            asset_name=asset.asset_name,
            asset_class=asset.asset_class.value if hasattr(asset.asset_class, 'value') else asset.asset_class,
            ticker=asset.ticker,
            quantity=asset.quantity,
            average_price=asset.average_price,
            purchase_date=asset.purchase_date,
            current_value=asset.current_value
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def list_by_user(self, user_id: UUID) -> list[DomainAsset]:
        query = select(AssetModel).where(AssetModel.user_id == user_id)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def update(self, asset: DomainAsset) -> DomainAsset:
        stmt = (
            sqlalchemy_update(AssetModel)
            .where(AssetModel.id == asset.id)
            .values(
                asset_name=asset.asset_name,
                asset_class=asset.asset_class.value if hasattr(asset.asset_class, 'value') else asset.asset_class,
                ticker=asset.ticker,
                quantity=asset.quantity,
                average_price=asset.average_price,
                purchase_date=asset.purchase_date,
                current_value=asset.current_value
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return asset

    async def delete(self, asset_id: UUID) -> None:
        stmt = sqlalchemy_delete(AssetModel).where(AssetModel.id == asset_id)
        await self.session.execute(stmt)
        await self.session.commit()

    def _to_domain(self, model: AssetModel) -> DomainAsset:
        return DomainAsset(
            id=model.id,
            user_id=model.user_id,
            asset_name=model.asset_name,
            asset_class=AssetClass(model.asset_class),
            ticker=model.ticker,
            quantity=model.quantity,
            average_price=model.average_price,
            purchase_date=model.purchase_date,
            current_value=model.current_value
        )
