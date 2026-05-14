from typing import List
from ...domain.entities.investor_profile import InvestorProfile
from ...domain.entities.portfolio import Portfolio
from ...domain.entities.asset import Asset
from ...domain.interfaces.services import IOptimizerService

class GeneratePortfolioUseCase:
    """
    Use case to generate an optimized portfolio for an investor profile.
    """
    def __init__(self, optimizer_service: IOptimizerService):
        self.optimizer_service = optimizer_service

    def execute(self, profile: InvestorProfile, available_assets: List[Asset]) -> Portfolio:
        """
        Runs optimization (e.g. Markowitz) to find the best asset allocation for the user's profile.
        """
        # In a real scenario, the optimizer service would filter assets
        # and apply constraints based on the user's risk profile.
        optimized_portfolio = self.optimizer_service.optimize(profile, available_assets)
        
        return optimized_portfolio
