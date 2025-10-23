from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.engine import make_url
from .settings import settings


class Base(DeclarativeBase):
    pass


url = make_url(settings.database_url)
engine_kwargs: dict[str, object] = {
    "echo": False,
    "pool_pre_ping": True,
}

if url.get_backend_name().startswith("sqlite"):
    # SQLite's async driver uses a static pool by default; extra pooling args cause errors.
    engine_kwargs["pool_pre_ping"] = False
else:
    engine_kwargs.update(
        pool_size=20,
        max_overflow=40,
        pool_timeout=120,
    )

engine: AsyncEngine = create_async_engine(settings.database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    # Ensure pgvector exists and verify connectivity
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("SELECT 1"))
