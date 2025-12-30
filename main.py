import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from database.connection import engine, init_mongodb, close_mongodb
from database.models import Base
from handlers import commands, callbacks, messages, admin, events, verification, social, payments
from middleware.database import DatabaseMiddleware
from database.redis_client import redis_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_tables():
    """Создание таблиц в БД"""
    # Для SQLite: пересоздаем таблицы если нужно
    # В продакшене используйте Alembic миграции!
    async with engine.begin() as conn:
        # Удаляем все таблицы (только для разработки!)
        # await conn.run_sync(Base.metadata.drop_all)
        # Создаем таблицы
        await conn.run_sync(Base.metadata.create_all)


async def main():
    """Главная функция"""
    # Инициализация MongoDB
    if init_mongodb():
        logger.info("✅ MongoDB подключена")
    else:
        logger.warning("⚠️  MongoDB недоступна, используется SQLite")
    
    # Инициализация бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    # Проверяем доступность Redis перед использованием
    try:
        import redis.asyncio as redis
        test_redis = redis.from_url(settings.REDIS_URL)
        await test_redis.ping()
        await test_redis.aclose()
        storage = RedisStorage.from_url(settings.REDIS_URL)
        logger.info("Redis подключен, используется RedisStorage")
    except Exception as e:
        logger.warning(f"Redis недоступен ({e}), используется MemoryStorage")
        storage = MemoryStorage()
    
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware для dependency injection сессии БД
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.edited_message.middleware(DatabaseMiddleware())
    
    # Регистрация роутеров
    # Важно: verification должен быть раньше messages, чтобы перехватывать фото для верификации
    # payments должен быть раньше других для перехвата платежных событий
    dp.include_router(payments.router)  # Обработка платежей
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(verification.router)  # Регистрируем раньше messages
    dp.include_router(messages.router)
    dp.include_router(admin.router)
    dp.include_router(events.router)
    dp.include_router(social.router)
    
    # Создание таблиц
    await create_tables()
    logger.info("Таблицы созданы")
    
    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        # Закрываем подключение к MongoDB
        try:
            asyncio.run(close_mongodb())
        except Exception as e:
            logger.warning(f"Ошибка при закрытии MongoDB: {e}")

