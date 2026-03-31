from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings

engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker | None = None

try:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print("DB ERROR:", e)
