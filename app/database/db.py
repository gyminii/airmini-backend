from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings


settings = get_settings()

def _asyncpg_url(url: str) -> str:
    """Strip all query params — asyncpg doesn't understand libpq params like
    sslmode, channel_binding, etc. SSL is passed via connect_args instead."""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url.replace("postgresql://", "postgresql+asyncpg://", 1))
    return urlunparse(parsed._replace(query=""))


engine = create_async_engine(
    _asyncpg_url(settings["database_url"]),
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": True},
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
