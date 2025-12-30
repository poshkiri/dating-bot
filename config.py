from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str  # Обязательно для запуска бота
    BOT_USERNAME: str = "meetup_dating_bot"  # Username бота без @

    # Database
    DATABASE_URL: str = ""  # Для SQLAlchemy (SQLite/PostgreSQL) - оставлено для совместимости
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "dating_bot"
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Payment - Telegram Payments (рекомендуется)
    # Получите токен у провайдера (ЮKassa, Stripe и т.д.)
    PAYMENT_PROVIDER_TOKEN: str = ""
    
    # Crypto Payments - Wallet addresses
    # Укажите адреса ваших кошельков для приема платежей
    CRYPTO_WALLET_BEP20: str = ""  # BSC (Binance Smart Chain) - USDT, BUSD
    CRYPTO_WALLET_ERC20: str = ""  # Ethereum - USDT, USDC
    CRYPTO_WALLET_TRC20: str = ""  # Tron - USDT
    CRYPTO_WALLET_POLYGON: str = ""  # Polygon - USDT, USDC
    
    # Crypto Payments - RPC endpoints (опционально, для проверки транзакций)
    BSC_RPC_URL: str = "https://bsc-dataseed.binance.org/"
    ETH_RPC_URL: str = "https://eth.llamarpc.com"
    TRON_RPC_URL: str = "https://api.trongrid.io"
    POLYGON_RPC_URL: str = "https://polygon-rpc.com"
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""
    
    # Admin
    ADMIN_USER_IDS: str = ""
    
    # Subscription (в USD центах)
    # Рекомендуемые цены для международного рынка:
    # - Подписка: $9.99-$19.99/месяц (999-1999 центов)
    # - Суперлайк: $1.99-$4.99 (199-499 центов)
    SUBSCRIPTION_PRICE: int = 999  # $9.99 (можно увеличить до 1999 = $19.99)
    SUPER_LIKE_PRICE: int = 199  # $1.99 (можно увеличить до 499 = $4.99)
    
    # Limits
    DAILY_LIKES_LIMIT: int = 10
    DAILY_DISLIKES_LIMIT: int = 50
    REFERRAL_BONUS_LIKES: int = 5
    
    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_USER_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

