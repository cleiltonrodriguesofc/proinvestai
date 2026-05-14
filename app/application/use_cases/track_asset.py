from typing import List
from ...domain.entities.user_asset import UserAsset
from ...domain.interfaces.repositories import IUserAssetRepository

class TrackAssetUseCase:
    """
    Use case to manage and track the user's current real assets.
    """
    def __init__(self, asset_repository: IUserAssetRepository):
        self.asset_repository = asset_repository

    async def add_asset(self, user_asset: UserAsset) -> UserAsset:
        # Business rules for adding an asset could go here
        return await self.asset_repository.add(user_asset)

    async def get_user_assets(self, user_id: str) -> List[UserAsset]:
        return await self.asset_repository.get_by_user(user_id)
        
    async def remove_asset(self, user_asset_id: str) -> None:
        await self.asset_repository.delete(user_asset_id)
