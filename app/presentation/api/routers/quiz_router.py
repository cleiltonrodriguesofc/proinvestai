from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from ....application.services.quiz_service import QuizService
from ....infrastructure.database.connection import get_session as get_db
from ....infrastructure.repositories.profile_repository import SQLAlchemyProfileRepository
from ....domain.entities.quiz import QuizResponse
from ....domain.entities.investor_profile import InvestorProfile, RiskProfile, Decimal

from ....domain.entities.user import User as DomainUser
from ...web.routers.auth import get_current_user

router = APIRouter(prefix="/api/quiz", tags=["quiz"])
quiz_service = QuizService()

@router.post("/submit")
async def submit_quiz(
    responses: List[QuizResponse],
    db: AsyncSession = Depends(get_db),
    user: DomainUser | None = Depends(get_current_user)
):
    # 1. Calculate result
    result = quiz_service.calculate_result(responses)
    
    # 2. Map to InvestorProfile entity
    user_id = user.id if user else uuid.UUID("00000000-0000-0000-0000-000000000000")
    
    # Convert profile type string to enum
    profile_map = {
        "Conservador": RiskProfile.CONSERVATIVE,
        "Moderado": RiskProfile.MODERATE,
        "Arrojado": RiskProfile.AGGRESSIVE
    }
    
    profile = InvestorProfile(
        user_id=user_id,
        risk_profile=profile_map.get(result.profile_type, RiskProfile.MODERATE),
        investment_horizon_months=60, # Mock default
        monthly_income=Decimal("0"), # Emptied mock
        initial_amount=Decimal("0"), # Let user input later
        monthly_contribution=Decimal("0"), # Emptied mock
        has_emergency_reserve=True,
        investment_goal="Crescimento",
        score=result.total_score,
        raw_responses={ans.question_id: ans.option_id for ans in responses}
    )
    
    # 3. Save via repository
    repo = SQLAlchemyProfileRepository(db)
    saved_profile = await repo.save_profile(profile)
    
    return {
        "status": "success",
        "profile": result.profile_type,
        "score": result.total_score,
        "profile_id": str(saved_profile.user_id) # Should be id, but user_id is what we have in domain for now
    }
