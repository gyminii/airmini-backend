from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings


settings = get_settings()

engine = create_async_engine(
    settings["database_url"].replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
