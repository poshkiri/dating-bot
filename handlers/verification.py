from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User
from keyboards.common import get_back_keyboard
from datetime import datetime

router = Router()


from handlers.states import Verification


@router.callback_query(F.data == "verify")
async def callback_verify(callback: CallbackQuery, state: FSMContext):
    """Начало верификации"""
    try:
        await callback.answer()  # Отвечаем сразу, чтобы избежать timeout
    except:
        pass  # Игнорируем ошибки если callback уже устарел
    
    await callback.message.answer(
        "✅ Верификация\n\n"
        "Для верификации нужно отправить фото с жестом 🤚🏼 (покажи руку)\n\n"
        "Это подтверждает, что ты не бот. Отправь фото:",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(Verification.photo)


@router.message(Verification.photo, F.photo)
async def process_verification_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка фото для верификации"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Получено фото для верификации от пользователя {message.from_user.id}")
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Ошибка! Начните с /start")
        await state.clear()
        return
    
    photo = message.photo[-1]
    user.verification_photo = photo.file_id
    # is_verified остается False до одобрения админом
    # В реальности здесь будет отправка фото админам для проверки
    # Пока просто сохраняем фото
    await session.commit()
    logger.info(f"Фото верификации сохранено для пользователя {user_id}")
    
    await message.answer(
        "✅ Фото отправлено на проверку!\n\n"
        "Администратор проверит твою верификацию в ближайшее время.",
        reply_markup=get_back_keyboard()
    )
    await state.clear()
    
    # Уведомляем админов (в реальности)
    # from config import settings
    # for admin_id in settings.admin_ids:
    #     try:
    #         await message.bot.send_photo(
    #             admin_id,
    #             photo.file_id,
    #             caption=f"Верификация от @{message.from_user.username or 'пользователь'}"
    #         )
    #     except:
    #         pass


@router.message(Verification.photo)
async def process_verification_other(message: Message, state: FSMContext):
    """Обработка других сообщений в состоянии верификации"""
    await message.answer(
        "❌ Пожалуйста, отправь фото для верификации.\n\n"
        "Нужно отправить фото с жестом 🤚🏼 (покажи руку)."
    )

