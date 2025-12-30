import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Like, Dislike
from config import settings


def generate_referral_code() -> str:
    """Генерирует уникальный реферальный код"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


async def reset_daily_limits(session: AsyncSession, user: User):
    """Сбрасывает дневные лимиты пользователя"""
    now = datetime.utcnow()
    if user.last_limit_reset.date() < now.date():
        user.daily_likes_used = 0
        user.daily_dislikes_used = 0
        user.last_limit_reset = now
        await session.commit()


async def can_like(session: AsyncSession, user: User) -> tuple[bool, str]:
    """Проверяет, может ли пользователь поставить лайк"""
    # БЕЗЛИМИТНО для всех - убраны все проверки лимитов
    await reset_daily_limits(session, user)
    return True, ""


async def can_dislike(session: AsyncSession, user: User) -> tuple[bool, str]:
    """Проверяет, может ли пользователь поставить дизлайк"""
    # БЕЗЛИМИТНО для всех - убраны все проверки лимитов
    await reset_daily_limits(session, user)
    return True, ""


async def check_mutual_like(session: AsyncSession, from_user_id: int, to_user_id: int) -> bool:
    """Проверяет взаимную симпатию"""
    from sqlalchemy import select
    mutual_like = await session.execute(
        select(Like).where(
            Like.from_user_id == to_user_id,
            Like.to_user_id == from_user_id
        )
    )
    return mutual_like.scalar_one_or_none() is not None


async def get_next_profile(session: AsyncSession, user: User) -> Optional[User]:
    """Получает следующую анкету для просмотра"""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import select, and_, not_, or_
    # Получаем ID пользователей, которых уже лайкнули/дизлайкнули
    liked_result = await session.execute(
        select(Like.to_user_id).where(Like.from_user_id == user.id)
    )
    disliked_result = await session.execute(
        select(Dislike.to_user_id).where(Dislike.from_user_id == user.id)
    )
    
    liked_ids = set(liked_result.scalars().all())
    disliked_ids = set(disliked_result.scalars().all())
    excluded_ids = {user.id} | liked_ids | disliked_ids
    
    # Базовые условия (обязательные)
    base_conditions = [
        User.id != user.id,
        User.is_active == True,
        User.is_banned == False,
        User.is_hidden == False,
    ]
    
    # Проверка на заполненность анкеты (есть имя)
    base_conditions.append(User.name.isnot(None))
    
    # Добавляем исключения только если они есть
    if excluded_ids:
        base_conditions.append(~User.id.in_(excluded_ids))
    
    # Фильтры (необязательные - если нет результатов, показываем без фильтров)
    interest_filter = None
    if user.interest and user.interest.value == "male":
        interest_filter = User.gender == "male"
    elif user.interest and user.interest.value == "female":
        interest_filter = User.gender == "female"
    
    city_filter = None
    if user.city:
        city_filter = User.city == user.city
    
    # Пробуем найти с фильтрами
    conditions = base_conditions.copy()
    if interest_filter:
        conditions.append(interest_filter)
    if city_filter:
        conditions.append(city_filter)
    
    query = select(User).where(and_(*conditions))
    
    # Boost пользователи в приоритете
    from database.models import Boost
    boosted_result = await session.execute(
        select(Boost.user_id).where(Boost.expires_at > datetime.utcnow())
    )
    boosted_ids = set(boosted_result.scalars().all())
    
    result = await session.execute(query)
    profiles = result.scalars().all()
    
    # Сортируем: сначала boost, потом остальные
    boosted_profiles = [p for p in profiles if p.id in boosted_ids]
    other_profiles = [p for p in profiles if p.id not in boosted_ids]
    all_profiles = boosted_profiles + other_profiles
    
    # Если нашли с фильтрами - возвращаем
    if all_profiles:
        logger.info(f"Найдено {len(all_profiles)} анкет с фильтрами для пользователя {user.id}")
        return all_profiles[0]
    
    # Если не нашли с фильтрами - пробуем без фильтра по городу
    if city_filter:
        conditions = base_conditions.copy()
        if interest_filter:
            conditions.append(interest_filter)
        
        query = select(User).where(and_(*conditions))
        result = await session.execute(query)
        profiles = result.scalars().all()
        
        boosted_profiles = [p for p in profiles if p.id in boosted_ids]
        other_profiles = [p for p in profiles if p.id not in boosted_ids]
        all_profiles = boosted_profiles + other_profiles
        
        if all_profiles:
            return all_profiles[0]
    
    # Если не нашли - пробуем без фильтра по полу
    if interest_filter:
        conditions = base_conditions.copy()
        if city_filter:
            conditions.append(city_filter)
        
        query = select(User).where(and_(*conditions))
        result = await session.execute(query)
        profiles = result.scalars().all()
        
        boosted_profiles = [p for p in profiles if p.id in boosted_ids]
        other_profiles = [p for p in profiles if p.id not in boosted_ids]
        all_profiles = boosted_profiles + other_profiles
        
        if all_profiles:
            return all_profiles[0]
    
    # Если все еще не нашли - показываем любые анкеты (только базовые условия)
    conditions = base_conditions.copy()
    query = select(User).where(and_(*conditions))
    result = await session.execute(query)
    profiles = result.scalars().all()
    
    boosted_profiles = [p for p in profiles if p.id in boosted_ids]
    other_profiles = [p for p in profiles if p.id not in boosted_ids]
    all_profiles = boosted_profiles + other_profiles
    
    if all_profiles:
        logger.info(f"Найдено {len(all_profiles)} анкет без фильтров для пользователя {user.id}")
        return all_profiles[0]
    else:
        logger.warning(f"Не найдено анкет для пользователя {user.id}. Всего пользователей в базе: {len(profiles)}")
        return None


def format_profile_text(user: User) -> str:
    """Форматирует текст анкеты"""
    text = f"👤 {user.name or 'Не указано'}\n"
    if user.age:
        text += f"🎂 {user.age} лет\n"
    if user.city:
        text += f"📍 {user.city}\n"
    if user.description:
        text += f"\n{user.description}\n"
    if user.is_verified:
        text += "\n✅ Проверен"
    if user.instagram:
        text += f"\n📷 Instagram: @{user.instagram}"
    if user.vk:
        text += f"\n🔵 VK: {user.vk}"
    return text

