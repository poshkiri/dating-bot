import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

Base = declarative_base()

# MongoDB подключение
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database = None

def init_mongodb():
    """Инициализация подключения к MongoDB"""
    global mongodb_client, mongodb_database
    try:
        mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        mongodb_database = mongodb_client[settings.MONGODB_DATABASE]
        return True
    except Exception as e:
        print(f"⚠️  Ошибка подключения к MongoDB: {e}")
        return False

async def get_mongodb():
    """Получить объект базы данных MongoDB"""
    global mongodb_database
    if mongodb_database is None:
        init_mongodb()
    return mongodb_database

async def close_mongodb():
    """Закрыть подключение к MongoDB"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        await asyncio.sleep(0.1)  # Даем время на закрытие

# SQLite подключение (для обратной совместимости)
database_url = settings.DATABASE_URL if settings.DATABASE_URL else "sqlite+aiosqlite:///./test_bot.db"

engine = create_async_engine(
    database_url,
    echo=True,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session():
    async with async_session_maker() as session:
        yield session
