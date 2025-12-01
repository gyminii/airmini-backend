import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.models import Base
from app.config import get_settings

settings = get_settings()


# python -m scripts.init_db
async def init_db():
    engine = create_async_engine(settings["database_url"], echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✓ Tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
