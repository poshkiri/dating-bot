import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, SupportChat
from database.connection import get_session
from keyboards.common import get_main_menu_keyboard, get_my_profile_keyboard
from utils.helpers import generate_referral_code, format_profile_text
from utils.locales import get_text
from datetime import datetime, timedelta
from handlers.states import ProfileCreation, Support

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем, существует ли пользователь
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # Создаем нового пользователя
        referral_code = generate_referral_code()
        user = User(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referral_code=referral_code,
            language='ru'  # По умолчанию русский
        )
        session.add(user)
        await session.commit()
        
        # Проверяем реферальный код
        if len(message.text.split()) > 1:
            ref_code = message.text.split()[1]
            ref_result = await session.execute(select(User).where(User.referral_code == ref_code))
            ref_user = ref_result.scalar_one_or_none()
            if ref_user:
                user.referred_by = ref_user.id
                ref_user.referral_bonus_likes += 5  # Бонус за реферала
                await session.commit()
        
        lang = user.language or 'ru'
        await message.answer(
            get_text(lang, 'welcome'),
            reply_markup=get_main_menu_keyboard(lang)
        )
        # Начинаем создание анкеты
        await message.answer(get_text(lang, 'ask_age'), reply_markup=None)
        await state.set_state(ProfileCreation.age)
    else:
        lang = user.language or 'ru'
        if not user.name or not user.age:
            # Анкета не заполнена
            await message.answer(
                get_text(lang, 'welcome_back'),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await message.answer(get_text(lang, 'ask_age'), reply_markup=None)
            await state.set_state(ProfileCreation.age)
        else:
            # Показываем главное меню
            await message.answer(
                get_text(lang, 'welcome_complete'),
                reply_markup=get_main_menu_keyboard(lang)
            )


@router.message(Command("myprofile"))
@router.message(F.text == "👤 Моя анкета")
async def cmd_my_profile(message: Message, session: AsyncSession, state: FSMContext):
    """Просмотр своей анкеты"""
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.name:
        await message.answer("Твоя анкета еще не заполнена. Давайте создадим её!")
        await message.answer("Сколько тебе лет?", reply_markup=None)
        await state.set_state(ProfileCreation.age)
        return
    
    text = "Так выглядит твоя анкета:\n\n"
    text += format_profile_text(user)
    
    # Приоритет: сначала видео, потом фото
    if user.videos and len(user.videos) > 0:
        try:
            await message.answer_video(user.videos[0], caption=text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось отправить видео: {e}. Пробуем фото.")
            # Если видео не отправилось, пробуем фото
            if user.photos and len(user.photos) > 0:
                try:
                    await message.answer_photo(user.photos[0], caption=text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
                except:
                    await message.answer(text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
            else:
                await message.answer(text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
    elif user.photos and len(user.photos) > 0:
        try:
            await message.answer_photo(user.photos[0], caption=text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
        except Exception as e:
            # Если file_id невалиден (например, от старого бота), отправляем только текст
            logger.warning(f"Не удалось отправить фото: {e}. Отправляем текст без фото.")
            await message.answer(text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=get_my_profile_keyboard(), parse_mode="HTML")


@router.message(Command("complaint"))
@router.message(F.text == "🚫 Пожаловаться")
async def cmd_complaint(message: Message):
    """Жалоба на пользователя"""
    from keyboards.common import get_complaint_reason_keyboard
    await message.answer(
        "Укажите причину жалобы:",
        reply_markup=get_complaint_reason_keyboard()
    )




@router.message(Command("help"))
@router.message(F.text == "📖 Руководство")
async def cmd_help(message: Message):
    """Руководство по использованию бота"""
    text = """📖 Руководство по работе с платформой MeetUp

✨ Возможности бота:
• Создание профиля с фото и видео
• Поиск пар по фильтрам (возраст, город, пол)
• Система лайков и взаимных симпатий
• Создание и участие в мероприятиях
• Реферальная система с бонусами
• Подписка для неограниченных лайков
• Анонимная поддержка от администраторов
• Статистика активности и симпатий

1️⃣ Навигация по главному меню
/start - Начать работу с ботом

2️⃣ Моя анкета
Просмотр и редактирование своей анкеты

3️⃣ Фильтры
Настройка параметров поиска (город, возраст, пол)

4️⃣ Найти пару
Поиск и просмотр анкет других пользователей

5️⃣ Руководство
Инструкция по использованию бота (это сообщение)

6️⃣ Тусовки
Календарь мероприятий от пользователей

7️⃣ Статистика
Персональная статистика и активность

8️⃣ Поддержка
Связь с администратором (анонимный чат внутри бота)

💡 Советы:
• Заполни анкету полностью для лучших результатов
• Используй фильтры для точного поиска
• Приглашай друзей и получай бонусные лайки
• Подписка дает неограниченные лайки на месяц"""
    
    await message.answer(text, reply_markup=None)


@router.message(Command("events"))
@router.message(F.text == "🎉 Тусовки")
async def cmd_events(message: Message):
    """Мероприятия"""
    from keyboards.common import get_events_menu_keyboard
    await message.answer(
        "🎉 Мероприятия и события\n\n"
        "Создавай события и находи единомышленников!",
        reply_markup=get_events_menu_keyboard()
    )


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message, session: AsyncSession):
    """Статистика пользователя"""
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала создай анкету!")
        return
    
    from database.models import Like, Dislike
    from sqlalchemy import func
    
    # Получаем статистику
    likes_received = await session.execute(
        select(func.count(Like.id)).where(Like.to_user_id == user.id)
    )
    likes_given = await session.execute(
        select(func.count(Like.id)).where(Like.from_user_id == user.id)
    )
    mutual_likes = await session.execute(
        select(func.count(Like.id)).where(
            Like.to_user_id == user.id,
            Like.is_mutual == True
        )
    )
    
    text = f"""📊 Твоя статистика

❤️ Получено лайков: {likes_received.scalar() or 0}
💌 Отправлено лайков: {likes_given.scalar() or 0}
💕 Взаимных симпатий: {mutual_likes.scalar() or 0}
👎🏼 Дизлайков: {user.total_dislikes}

📈 Лайков сегодня: {user.daily_likes_used}/{10 + user.referral_bonus_likes}
🎁 Бонусных лайков: {user.referral_bonus_likes}

💎 Подписка: {"✅ Активна" if user.subscription_status.value == "active" and user.subscription_expires_at > datetime.utcnow() else "❌ Неактивна"}"""
    
    await message.answer(text, reply_markup=None)


@router.message(Command("support"))
@router.message(F.text == "💬 Поддержка")
async def cmd_support(message: Message, session: AsyncSession, state: FSMContext):
    """Поддержка"""
    from sqlalchemy import select
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала создай анкету!")
        return
    
    # Проверяем, есть ли активный чат поддержки
    existing_chat = await session.execute(
        select(SupportChat).where(
            SupportChat.user_id == user.id,
            SupportChat.is_active == True
        )
    )
    chat = existing_chat.scalar_one_or_none()
    
    if not chat:
        # Создаем новый чат поддержки
        chat = SupportChat(user_id=user.id)
        session.add(chat)
        await session.commit()
    
    await state.set_state(Support.waiting_message)
    await message.answer(
        "💬 Поддержка\n\n"
        "Напиши свой вопрос, и администратор свяжется с тобой!\n\n"
        "Для отмены отправь /cancel",
        reply_markup=None
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Действие отменено", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("Нет активных действий для отмены")


@router.message(Command("invite"))
@router.message(F.text == "👥 Пригласи друзей")
async def cmd_invite(message: Message, session: AsyncSession):
    """Приглашение друзей"""
    from sqlalchemy import func
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала создай анкету!")
        return
    
    # Подсчитываем рефералов за 14 дней
    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
    referrals_count = await session.execute(
        select(func.count(User.id)).where(
            User.referred_by == user.id,
            User.created_at >= fourteen_days_ago
        )
    )
    
    from config import settings
    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}"
    
    text = f"""Пригласи друзей и получи больше лайков! 😎

Твоя статистика:
Пришло за 14 дней: {referrals_count.scalar() or 0}
Бонус к силе анкеты: {user.referral_bonus_likes * 10}%

Перешли друзьям или размести в своих соцсетях.

Вот твоя личная ссылка 👇

MeetUp ❤️ в Telegram! Найдет друзей или даже половинку 👫

👉 {referral_link}"""
    
    from keyboards.common import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отправить друзьям в Telegram", url=f"https://t.me/share/url?url={referral_link}&text=MeetUp ❤️")
    ]])
    
    await message.answer(text, reply_markup=keyboard)

