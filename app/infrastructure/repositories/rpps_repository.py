import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from ..database.models import RppsInstitute as RppsInstituteModel
from ..database.models import FundPosition as FundPositionModel
from ...domain.entities.rpps_entities import RppsInstitute, FundPosition

class SQLAlchemyRppsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_institute(self, institute: RppsInstitute) -> RppsInstituteModel:
        db_institute = RppsInstituteModel(
            id=institute.id,
            cnpj=institute.cnpj,
            name=institute.name,
            municipality=institute.municipality,
            state=institute.state,
            type_regime=institute.type_regime,
            total_assets=institute.total_assets,
            actuarial_target_index=institute.actuarial_target_index,
            actuarial_target_rate=institute.actuarial_target_rate,
            pro_gestao_level=institute.pro_gestao_level
        )
        self.session.add(db_institute)
        await self.session.commit()
        await self.session.refresh(db_institute)
        return db_institute

    async def get_institute_by_id(self, rpps_id: uuid.UUID) -> Optional[RppsInstituteModel]:
        result = await self.session.execute(
            select(RppsInstituteModel).where(RppsInstituteModel.id == rpps_id)
        )
        return result.scalars().first()

    async def get_institute_by_cnpj(self, cnpj: str) -> Optional[RppsInstituteModel]:
        result = await self.session.execute(
            select(RppsInstituteModel).where(RppsInstituteModel.cnpj == cnpj)
        )
        return result.scalars().first()

    async def add_fund_position(self, position: FundPosition) -> FundPositionModel:
        db_position = FundPositionModel(
            id=position.id,
            rpps_id=position.rpps_id,
            cnpj_fund=position.cnpj_fund,
            name_fund=position.name_fund,
            segment_cmn=position.segment_cmn,
            current_balance=position.current_balance,
            date_entry=position.date_entry,
            manager_name=position.manager_name,
            admin_name=position.admin_name
        )
        self.session.add(db_position)
        await self.session.commit()
        await self.session.refresh(db_position)
        return db_position

    async def list_positions(self, rpps_id: uuid.UUID) -> List[FundPositionModel]:
        result = await self.session.execute(
            select(FundPositionModel).where(FundPositionModel.rpps_id == rpps_id)
        )
        return list(result.scalars().all())
        
    async def remove_fund_position(self, position_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(FundPositionModel).where(FundPositionModel.id == position_id)
        )
        await self.session.commit()
