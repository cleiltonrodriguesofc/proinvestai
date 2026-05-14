from typing import Dict, Any
from ...domain.entities.portfolio import Portfolio
from ...domain.entities.investor_profile import InvestorProfile
from ..services.gap_analysis_engine import GapAnalysisEngine, GapResult
from ...domain.interfaces.services import IAIService

class AnalyzeGapUseCase:
    """
    Use case to compare user's current portfolio with an ideal optimized portfolio
    and generate AI explanations.
    """
    def __init__(self, gap_engine: GapAnalysisEngine, ai_service: IAIService):
        self.gap_engine = gap_engine
        self.ai_service = ai_service

    async def execute(
        self, 
        current_portfolio: Portfolio, 
        ideal_portfolio: Portfolio, 
        initial_amount: float,
        profile: InvestorProfile
    ) -> Dict[str, Any]:
        
        # 1. Run quantitative gap analysis
        gap_result: GapResult = self.gap_engine.compare(current_portfolio, ideal_portfolio, initial_amount)
        
        # 2. Generate AI Narration
        narration = await self.ai_service.explain_gap(
            current_portfolio=gap_result.current_allocation,
            ideal_portfolio=gap_result.ideal_allocation,
            profile=profile
        )
        
        return {
            "current_allocation": gap_result.current_allocation,
            "ideal_allocation": gap_result.ideal_allocation,
            "deviations": gap_result.deviations,
            "total_misallocated_capital": gap_result.total_misallocated_capital,
            "potential_gain_lost": gap_result.potential_gain_lost,
            "narration": narration
        }
