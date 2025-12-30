from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User
from keyboards.common import get_social_network_keyboard, get_back_keyboard
import re

router = Router()


from handlers.states import SocialNetwork


@router.callback_query(F.data == "social_instagram")
async def callback_social_instagram(callback: CallbackQuery, state: FSMContext):
    """Добавление Instagram"""
    await callback.message.answer(
        "📷 Instagram\n\n"
        "Введи свой Instagram username (без @):",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(SocialNetwork.instagram)
    await callback.answer()


@router.message(SocialNetwork.instagram)
async def process_instagram(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка Instagram"""
    username = message.text.strip()
    
    # Убираем https://instagram.com/ если пользователь вставил полную ссылку
    if username.startswith("https://instagram.com/"):
        username = username.replace("https://instagram.com/", "")
    elif username.startswith("https://www.instagram.com/"):
        username = username.replace("https://www.instagram.com/", "")
    elif username.startswith("instagram.com/"):
        username = username.replace("instagram.com/", "")
    elif username.startswith("www.instagram.com/"):
        username = username.replace("www.instagram.com/", "")
    
    # Убираем @ и пробелы
    username = username.replace("@", "").strip()
    
    # Простая валидация
    if not username or not re.match(r'^[a-zA-Z0-9._]+$', username):
        await message.answer("Неверный формат username! Введи только username без @ и ссылок:")
        return
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        user.instagram = username
        await session.commit()
        await message.answer(f"✅ Instagram добавлен: @{username}", reply_markup=None)
    
    await state.clear()


@router.callback_query(F.data == "social_vk")
async def callback_social_vk(callback: CallbackQuery, state: FSMContext):
    """Добавление VK"""
    await callback.message.answer(
        "🔵 VK\n\n"
        "Введи свой VK username или ID:",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(SocialNetwork.vk)
    await callback.answer()


@router.message(SocialNetwork.vk)
async def process_vk(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка VK"""
    vk_input = message.text.strip()
    
    # Убираем https://vk.com/ если пользователь вставил полную ссылку
    if vk_input.startswith("https://vk.com/"):
        vk_input = vk_input.replace("https://vk.com/", "")
    elif vk_input.startswith("vk.com/"):
        vk_input = vk_input.replace("vk.com/", "")
    elif vk_input.startswith("http://vk.com/"):
        vk_input = vk_input.replace("http://vk.com/", "")
    
    # Убираем @ если есть
    vk_input = vk_input.replace("@", "")
    
    # Валидация: должен быть username или id123456789 или числовой ID
    if not vk_input:
        await message.answer("Неверный формат! Введи username или ID:")
        return
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        user.vk = vk_input
        await session.commit()
        await message.answer(f"✅ VK добавлен: {vk_input}", reply_markup=None)
    
    await state.clear()


@router.callback_query(F.data == "social_skip")
async def callback_social_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск добавления соцсети"""
    await callback.message.answer("Соцсети можно добавить позже в настройках профиля.")
    await state.clear()
    await callback.answer()

