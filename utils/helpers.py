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
    await reset_daily_limits(session, user)
    
    # Проверка подписки
    if user.subscription_status.value == "active" and user.subscription_expires_at > datetime.utcnow():
        return True, ""
    
    # Проверка лимита
    if user.daily_likes_used >= settings.DAILY_LIKES_LIMIT + user.referral_bonus_likes:
        return False, f"Вы исчерпали дневной лимит лайков ({settings.DAILY_LIKES_LIMIT}). Пригласите друзей или купите подписку!"
    
    return True, ""


async def can_dislike(session: AsyncSession, user: User) -> tuple[bool, str]:
    """Проверяет, может ли пользователь поставить дизлайк"""
    await reset_daily_limits(session, user)
    
    if user.daily_dislikes_used >= settings.DAILY_DISLIKES_LIMIT:
        return False, f"Вы исчерпали дневной лимит дизлайков ({settings.DAILY_DISLIKES_LIMIT})."
    
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
    from sqlalchemy import select, and_, not_
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
    
    # Фильтры
    conditions = [
        User.id != user.id,
        User.is_active == True,
        User.is_banned == False,
        User.is_hidden == False,
        ~User.id.in_(excluded_ids) if excluded_ids else True
    ]
    
    # Фильтр по полу
    if user.interest and user.interest.value == "male":
        conditions.append(User.gender == "male")
    elif user.interest and user.interest.value == "female":
        conditions.append(User.gender == "female")
    
    # Фильтр по городу (если указан)
    if user.city:
        conditions.append(User.city == user.city)
    
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
    
    return (boosted_profiles + other_profiles)[0] if (boosted_profiles + other_profiles) else None


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

