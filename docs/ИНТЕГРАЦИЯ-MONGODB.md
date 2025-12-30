# 🔄 Интеграция MongoDB в код

Инструкция по использованию MongoDB в боте.

## ✅ Что уже сделано

1. **Обновлен `database/connection.py`:**
   - Добавлено подключение к MongoDB
   - Сохранена поддержка SQLite для обратной совместимости

2. **Обновлен `middleware/database.py`:**
   - Теперь инжектит и SQLite сессию, и MongoDB базу данных
   - Обработчики могут использовать оба варианта

3. **Обновлен `main.py`:**
   - Добавлена инициализация MongoDB при запуске
   - Добавлено закрытие подключения при остановке

## 📋 Текущая ситуация

### Что работает:
- ✅ MongoDB подключение создается при запуске
- ✅ MongoDB доступна в обработчиках через `data["database"]`
- ✅ SQLite продолжает работать (обратная совместимость)

### Что нужно сделать:
- ⚠️ Обновить обработчики для использования MongoDB
- ⚠️ Создать индексы в MongoDB
- ⚠️ (Опционально) Мигрировать данные из SQLite в MongoDB

## 🔧 Использование MongoDB в обработчиках

### Текущий код (SQLAlchemy):

```python
@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
```

### Новый код (MongoDB):

```python
@router.message(Command("start"))
async def cmd_start(message: Message, database):
    user = await database.users.find_one({"telegram_id": message.from_user.id})
```

### Гибридный подход (оба доступны):

```python
@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, database):
    # Можно использовать оба
    # SQLite: session
    # MongoDB: database
    pass
```

## 📝 Примеры операций

### Создание пользователя:

**SQLite:**
```python
user = User(telegram_id=user_id, username=username)
session.add(user)
await session.commit()
```

**MongoDB:**
```python
user = {
    "telegram_id": user_id,
    "username": username,
    "created_at": datetime.utcnow()
}
await database.users.insert_one(user)
```

### Поиск пользователя:

**SQLite:**
```python
result = await session.execute(select(User).where(User.telegram_id == user_id))
user = result.scalar_one_or_none()
```

**MongoDB:**
```python
user = await database.users.find_one({"telegram_id": user_id})
```

### Обновление пользователя:

**SQLite:**
```python
user.name = "Новое имя"
await session.commit()
```

**MongoDB:**
```python
await database.users.update_one(
    {"telegram_id": user_id},
    {"$set": {"name": "Новое имя"}}
)
```

## 🗂️ Структура коллекций MongoDB

### Коллекции (соответствуют таблицам SQLite):

- `users` - пользователи
- `likes` - лайки
- `dislikes` - дизлайки
- `events` - события
- `event_participants` - участники событий
- `complaints` - жалобы
- `payments` - платежи
- `boosts` - бусты
- `admin_messages` - сообщения админов
- `support_chats` - чаты поддержки
- `support_messages` - сообщения поддержки

## 🔍 Создание индексов

Создайте файл `database/indexes.py`:

```python
from database.connection import get_mongodb

async def create_indexes():
    """Создание индексов для оптимизации запросов"""
    database = await get_mongodb()
    
    # Индексы для users
    await database.users.create_index("telegram_id", unique=True)
    await database.users.create_index("referral_code", unique=True, sparse=True)
    await database.users.create_index("city")
    await database.users.create_index("gender")
    await database.users.create_index("interest")
    
    # Индексы для likes
    await database.likes.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
    await database.likes.create_index("to_user_id")
    
    # Индексы для dislikes
    await database.dislikes.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
    
    # И т.д. для других коллекций
    
    print("✅ Индексы созданы")
```

Запустите один раз:

```python
import asyncio
from database.indexes import create_indexes

asyncio.run(create_indexes())
```

## 🔄 Миграция данных из SQLite в MongoDB

### Создайте скрипт миграции:

```python
# scripts/migrate_to_mongodb.py
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from database.models import User, Like, Dislike  # и т.д.

async def migrate():
    # Подключение к SQLite
    engine = create_engine("sqlite:///./test_bot.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Подключение к MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DATABASE]
    
    # Миграция пользователей
    users = session.query(User).all()
    for user in users:
        user_dict = {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "name": user.name,
            "age": user.age,
            # ... все поля
        }
        await db.users.insert_one(user_dict)
    
    # Аналогично для других таблиц
    
    session.close()
    client.close()
    print("✅ Миграция завершена")

if __name__ == "__main__":
    asyncio.run(migrate())
```

## ⚠️ Важные замечания

1. **Обратная совместимость:**
   - SQLite продолжает работать
   - Можно постепенно переходить на MongoDB

2. **Данные:**
   - SQLite и MongoDB - это разные базы данных
   - Данные не синхронизируются автоматически
   - Нужно выбрать одну БД или мигрировать данные

3. **Обработчики:**
   - Сейчас все обработчики используют SQLite
   - Для использования MongoDB нужно обновить каждый обработчик
   - Это большая работа, можно делать постепенно

## 🚀 Рекомендации

1. **Для начала:**
   - Оставьте SQLite для разработки
   - Настройте MongoDB для продакшена
   - Постепенно переходите на MongoDB

2. **Для продакшена:**
   - Используйте MongoDB Atlas
   - Создайте индексы
   - Мигрируйте данные из SQLite

3. **Постепенный переход:**
   - Начните с новых функций (используйте MongoDB)
   - Старые функции оставьте на SQLite
   - Постепенно мигрируйте

---

**Текущий статус:** MongoDB интегрирована в код, но обработчики еще используют SQLite. Можно постепенно переходить на MongoDB.

