from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

Base = declarative_base()

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():  # pragma: no cover
    async with async_session() as session:  # pragma: no cover
        yield session


import redis.asyncio as redis

redis_client = None


async def get_redis() -> redis.Redis:
    global redis_client  # pragma: no cover
    if redis_client is None:  # pragma: no cover
        redis_client = redis.from_url(settings.REDIS_URL or "redis://redis:6379/0", decode_responses=True)  # pragma: no cover
    return redis_client  # pragma: no cover
