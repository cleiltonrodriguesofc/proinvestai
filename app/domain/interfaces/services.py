from abc import ABC, abstractmethod
from decimal import Decimal
from ..entities.portfolio import Portfolio
from ..entities.investor_profile import InvestorProfile
from ..entities.asset import Asset


class IMarketDataService(ABC):
    """contract for fetching real market data from bcb and other sources."""

    @abstractmethod
    async def get_selic_rate(self) -> Decimal:
        ...

    @abstractmethod
    async def get_cdi_rate(self) -> Decimal:
        ...

    @abstractmethod
    async def get_ipca_rate(self) -> Decimal:
        ...

    @abstractmethod
    async def get_historical_series(self, series_code: int, start_date: str, end_date: str) -> list[dict]:
        ...

    @abstractmethod
    async def get_focus_projections(self) -> dict:
        ...


class IOptimizerService(ABC):
    """contract for portfolio optimization engine."""

    @abstractmethod
    def optimize(self, profile: InvestorProfile, assets: list[Asset]) -> Portfolio:
        ...


class IAIService(ABC):
    """contract for ai-powered explanations."""

    @abstractmethod
    async def explain_portfolio(self, portfolio: Portfolio, profile: InvestorProfile) -> str:
        ...

    @abstractmethod
    async def explain_committee_review(self, target_weights: dict, risk_metrics, profile_type: str) -> str:
        ...

    @abstractmethod
    async def explain_stress_test(self, results: dict, profile: InvestorProfile) -> str:
        ...
