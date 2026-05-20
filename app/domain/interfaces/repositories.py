from abc import ABC, abstractmethod
from uuid import UUID
from ..entities.user import User
from ..entities.investor_profile import InvestorProfile
from ..entities.user_asset import UserAsset


class IUserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...


class IProfileRepository(ABC):
    @abstractmethod
    async def save_profile(self, profile: InvestorProfile) -> InvestorProfile:
        ...

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> InvestorProfile | None:
        ...

    @abstractmethod
    async def get_latest_by_user(self, user_id: UUID) -> InvestorProfile | None:
        ...


class IUserAssetRepository(ABC):
    @abstractmethod
    async def create(self, asset: UserAsset) -> UserAsset:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[UserAsset]:
        ...

    @abstractmethod
    async def update(self, asset: UserAsset) -> UserAsset:
        ...

    @abstractmethod
    async def delete(self, asset_id: UUID) -> None:
        ...
