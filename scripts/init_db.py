import asyncio
from app.infrastructure.database.connection import engine
from app.infrastructure.database.models import Base

async def init_models():
    async with engine.begin() as conn:
        # This will create any missing tables based on the models defined in Base
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables synchronized.")

if __name__ == "__main__":
    asyncio.run(init_models())
