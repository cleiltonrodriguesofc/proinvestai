from typing import List, Dict, Any
from ...domain.entities.quiz import QuizResponse
from ...domain.entities.investor_profile import InvestorProfile
from ..services.quiz_service import QuizService
from ...domain.interfaces.repositories import IProfileRepository

class SubmitQuizUseCase:
    """
    Use case to process a quiz submission, calculate the profile,
    and persist it to the database.
    """
    def __init__(self, quiz_service: QuizService, profile_repository: IProfileRepository):
        self.quiz_service = quiz_service
        self.profile_repository = profile_repository

    async def execute(self, user_id: str, answers: List[QuizResponse]) -> InvestorProfile:
        # 1. Calculate score and profile
        quiz_result = self.quiz_service.calculate_result(answers)
        
        # 2. Map answers to a dictionary for persistence
        raw_responses = {ans.question_id: ans.option_id for ans in answers}
        
        # 3. Save profile to database
        profile = await self.profile_repository.save_profile(
            user_id=user_id,
            profile_type=quiz_result.profile_type,
            score=quiz_result.total_score,
            raw_responses=raw_responses
        )
        
        return profile
