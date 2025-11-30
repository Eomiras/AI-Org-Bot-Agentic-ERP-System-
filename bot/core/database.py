from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.core.config import settings

# Create Async Engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True
)

# Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initializes the database tables."""
    # Import models to ensure they are registered with Base.metadata
    # This is crucial for create_all to see them.
    from bot.core import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
