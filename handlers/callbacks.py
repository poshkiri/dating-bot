from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Like, Dislike, Event, EventParticipant, Complaint, Boost, Payment
from database.connection import get_session
from keyboards.common import *
from utils.helpers import (
    can_like, can_dislike, check_mutual_like, get_next_profile, 
    format_profile_text, reset_daily_limits
)
from utils.locales import get_text
from datetime import datetime, timedelta
from services.telegram_payments import telegram_payment_service
from services.crypto_payments import crypto_payment_service
from aiogram.types import LabeledPrice
from aiogram import Bot
from config import settings
from handlers.states import ProfileCreation, EventCreation, SuperLike, CryptoPayment

router = Router()


@router.callback_query(F.data == "view_profiles")
async def callback_view_profiles(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Просмотр анкет"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.name:
        await callback.answer("Сначала заполни анкету!", show_alert=True)
        return
    
    if not user.is_active:
        await callback.answer("Твоя анкета отключена. Включи её в настройках!", show_alert=True)
        return
    
    next_profile = await get_next_profile(session, user)
    
    lang = user.language or 'ru'
    
    if not next_profile:
        await callback.message.edit_text(
            get_text(lang, 'no_profiles'),
            reply_markup=get_pause_menu_keyboard(lang)
        )
        return
    
    text = format_profile_text(next_profile)
    
    # Сохраняем ID текущего профиля в состояние для жалоб
    await state.update_data(last_viewed_user_id=next_profile.id)
    
    keyboard = get_profile_view_keyboard(lang)
    # Добавляем ID профиля в callback_data
    keyboard.inline_keyboard[0][0].callback_data = f"like_{next_profile.id}"
    keyboard.inline_keyboard[0][1].callback_data = f"dislike_{next_profile.id}"
    keyboard.inline_keyboard[0][2].callback_data = f"super_like_{next_profile.id}"
    keyboard.inline_keyboard[1][0].callback_data = f"next_profile"
    
    # Приоритет: сначала видео, потом фото
    if next_profile.videos and len(next_profile.videos) > 0:
        try:
            await callback.message.delete()
        except:
            pass
        try:
            await callback.message.answer_video(next_profile.videos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить видео профиля: {e}. Пробуем фото.")
            # Если видео не отправилось, пробуем фото
            if next_profile.photos and len(next_profile.photos) > 0:
                try:
                    await callback.message.answer_photo(next_profile.photos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
                except:
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    elif next_profile.photos and len(next_profile.photos) > 0:
        try:
            await callback.message.delete()
        except:
            pass
        try:
            await callback.message.answer_photo(next_profile.photos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            # Если file_id невалиден (например, от старого бота), отправляем только текст
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить фото профиля: {e}. Отправляем текст без фото.")
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data.startswith("like"))
async def callback_like(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Лайк"""
    user_id = callback.from_user.id
    
    # Получаем ID целевого пользователя из callback_data или из состояния
    if "_" in callback.data:
        target_user_id = int(callback.data.split("_")[1])
    else:
        # Пытаемся получить из состояния (последний просмотренный профиль)
        data = await state.get_data()
        target_user_id = data.get("last_viewed_user_id")
        if not target_user_id:
            await callback.answer("Ошибка! Профиль не найден.", show_alert=True)
            return
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    result_target = await session.execute(select(User).where(User.id == target_user_id))
    target_user = result_target.scalar_one_or_none()
    
    if not user or not target_user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    can, error_msg = await can_like(session, user)
    if not can:
        await callback.answer(error_msg, show_alert=True)
        return
    
    # Проверяем, не лайкали ли уже
    existing_like = await session.execute(
        select(Like).where(Like.from_user_id == user.id, Like.to_user_id == target_user_id)
    )
    if existing_like.scalar_one_or_none():
        await callback.answer("Вы уже лайкнули этого пользователя!", show_alert=True)
        return
    
    # Создаем лайк
    like = Like(from_user_id=user.id, to_user_id=target_user_id)
    session.add(like)
    
    # Обновляем счетчики
    user.daily_likes_used += 1
    user.total_likes += 1
    target_user.total_likes += 1
    
    # Проверяем взаимную симпатию
    is_mutual = await check_mutual_like(session, user.id, target_user_id)
    if is_mutual:
        like.is_mutual = True
        # Обновляем предыдущий лайк
        prev_like = await session.execute(
            select(Like).where(Like.from_user_id == target_user_id, Like.to_user_id == user.id)
        )
        prev_like_obj = prev_like.scalar_one_or_none()
        if prev_like_obj:
            prev_like_obj.is_mutual = True
        
        # Показываем взаимную симпатию
        target_username = target_user.username or "пользователь"
        await callback.message.answer(
            f"💕 Взаимная симпатия!\n\n"
            f"Вы понравились друг другу! Напишите @{target_username}"
        )
    
    await session.commit()
    await callback.answer("❤️ Лайк поставлен!")
    
    # УВЕДОМЛЯЕМ пользователя, которому поставили лайк (для всех, включая бесплатных)
    try:
        liker_name = user.name or user.first_name or "Кто-то"
        liker_username = user.username or ""
        
        notification_text = f"❤️ Вам поставили лайк!\n\n"
        notification_text += f"👤 {liker_name}"
        if liker_username:
            notification_text += f" (@{liker_username})"
        
        # Отправляем уведомление
        await callback.bot.send_message(
            target_user.telegram_id,
            notification_text
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось отправить уведомление о лайке пользователю {target_user.telegram_id}: {e}")
    
    # Показываем следующую анкету
    await callback_view_profiles(callback, session, state)


@router.callback_query(F.data.startswith("dislike"))
async def callback_dislike(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Дизлайк"""
    user_id = callback.from_user.id
    
    # Получаем ID целевого пользователя из callback_data или из состояния
    if "_" in callback.data:
        target_user_id = int(callback.data.split("_")[1])
    else:
        # Пытаемся получить из состояния (последний просмотренный профиль)
        data = await state.get_data()
        target_user_id = data.get("last_viewed_user_id")
        if not target_user_id:
            await callback.answer("Ошибка! Профиль не найден.", show_alert=True)
            return
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    can, error_msg = await can_dislike(session, user)
    if not can:
        await callback.answer(error_msg, show_alert=True)
        return
    
    # Проверяем, не дизлайкали ли уже
    existing_dislike = await session.execute(
        select(Dislike).where(Dislike.from_user_id == user.id, Dislike.to_user_id == target_user_id)
    )
    if existing_dislike.scalar_one_or_none():
        await callback.answer("Следующая анкета", show_alert=False)
        await callback_view_profiles(callback, session, state)
        return
    
    # Создаем дизлайк
    dislike = Dislike(from_user_id=user.id, to_user_id=target_user_id)
    session.add(dislike)
    
    user.daily_dislikes_used += 1
    user.total_dislikes += 1
    
    await session.commit()
    await callback.answer("👎🏼 Дизлайк")
    
    # Показываем следующую анкету
    await callback_view_profiles(callback, session, state)


@router.callback_query(F.data.startswith("super_like"))
async def callback_super_like(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Суперлайк"""
    user_id = callback.from_user.id
    
    # Получаем ID целевого пользователя из callback_data или из состояния
    if "_" in callback.data and callback.data.count("_") >= 2:
        target_user_id = int(callback.data.split("_")[2])
    else:
        # Пытаемся получить из состояния (последний просмотренный профиль)
        data = await state.get_data()
        target_user_id = data.get("last_viewed_user_id")
        if not target_user_id:
            await callback.answer("Ошибка! Профиль не найден.", show_alert=True)
            return
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Проверяем оплату
    # В реальности здесь будет проверка через платежную систему
    await state.update_data(target_user_id=target_user_id)
    await callback.message.answer(
        "💌 Суперлайк\n\n"
        "Напиши сообщение для этого пользователя или запиши короткое видео (до 15 сек)",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(SuperLike.message)
    await callback.answer()


@router.callback_query(F.data == "next_profile")
async def callback_next_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Следующая анкета"""
    try:
        await callback.answer()  # Отвечаем на callback сразу, чтобы избежать ошибок
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Ошибка при ответе на callback: {e}")
    
    # Вызываем функцию просмотра анкет
    try:
        await callback_view_profiles(callback, session, state)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при показе следующей анкеты: {e}")
        try:
            await callback.message.answer("Произошла ошибка. Попробуйте еще раз.")
        except:
            pass


@router.callback_query(F.data == "edit_profile")
async def callback_edit_profile(callback: CallbackQuery, state: FSMContext):
    """Редактирование анкеты"""
    await callback.message.answer("Сколько тебе лет?")
    await state.set_state(ProfileCreation.age)
    await callback.answer()


@router.callback_query(F.data.startswith("complaint_"))
async def callback_complaint(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка жалобы"""
    from database.models import ComplaintReason
    reason_map = {
        "complaint_adult": ComplaintReason.ADULT_CONTENT,
        "complaint_selling": ComplaintReason.SELLING,
        "complaint_dislike": ComplaintReason.DISLIKE,
        "complaint_other": ComplaintReason.OTHER
    }
    
    reason_str = callback.data
    reason = reason_map.get(reason_str, ComplaintReason.OTHER)
    
    # Получаем ID пользователя, на которого жалуются из состояния
    # В реальности это будет из контекста (последний просмотренный профиль)
    data = await state.get_data()
    reported_user_id = data.get("last_viewed_user_id")
    
    if not reported_user_id:
        await callback.answer("Ошибка! Пользователь не найден.", show_alert=True)
        return
    
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Создаем жалобу
    complaint = Complaint(
        reporter_id=user.id,
        reported_user_id=reported_user_id,
        reason=reason
    )
    session.add(complaint)
    await session.commit()
    
    lang = user.language or 'ru'
    await callback.message.answer(
        get_text(lang, 'complaint_sent'),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer(get_text(lang, 'complaint_sent'))


@router.callback_query(F.data == "event_create")
async def callback_event_create(callback: CallbackQuery, state: FSMContext):
    """Создание события"""
    await callback.message.answer("Как называется мероприятие?")
    await state.set_state(EventCreation.title)
    await callback.answer()


# Обработчики событий перенесены в handlers/events.py


@router.callback_query(F.data == "buy_subscription")
async def callback_buy_subscription(
    callback: CallbackQuery, 
    session: AsyncSession,
    bot: Bot
):
    """Покупка подписки"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    lang = user.language or 'ru'
    
    # Показываем выбор способа оплаты
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Криптоплатежи (если настроены)
    available_networks = crypto_payment_service.get_available_networks()
    if available_networks:
        crypto_row = []
        for network in available_networks[:3]:  # Максимум 3 кнопки в ряд
            network_names = {
                "BEP20": "BSC",
                "ERC20": "ETH",
                "TRC20": "TRON",
                "POLYGON": "POLYGON"
            }
            crypto_row.append(
                InlineKeyboardButton(
                    text=f"💰 {network_names.get(network, network)}",
                    callback_data=f"crypto_pay_subscription_{network}"
                )
            )
        if crypto_row:
            keyboard.inline_keyboard.append(crypto_row)
    
    # Telegram Payments (карты)
    if settings.PAYMENT_PROVIDER_TOKEN:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="💳 Оплатить картой",
                callback_data="card_pay_subscription"
            )
        ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    ])
    
    price_usd = settings.SUBSCRIPTION_PRICE / 100  # Конвертируем центы в доллары
    text = (
        f"💎 Подписка MeetUp Premium - ${price_usd:.2f}\n\n"
        f"С подпиской вы получаете:\n"
        f"• Неограниченные лайки\n"
        f"• Приоритет в показе анкет\n"
        f"• Ранний доступ к новым функциям\n\n"
        f"Выберите способ оплаты:"
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("buy_super_like"))
async def callback_buy_super_like(
    callback: CallbackQuery, 
    session: AsyncSession,
    bot: Bot,
    state: FSMContext
):
    """Покупка суперлайка"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = callback.from_user.id
    
    # Получаем ID целевого пользователя из callback_data (если есть)
    target_user_id = None
    if "_" in callback.data:
        try:
            parts = callback.data.split("_")
            if len(parts) >= 4:
                target_user_id = int(parts[-1])
        except:
            pass
    
    # Сохраняем target_user_id в state для использования после оплаты
    if target_user_id:
        await state.update_data(super_like_target=target_user_id)
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    lang = user.language if user else 'ru'
    
    # Показываем выбор способа оплаты
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Криптоплатежи (если настроены)
    available_networks = crypto_payment_service.get_available_networks()
    if available_networks:
        crypto_row = []
        for network in available_networks[:3]:
            network_names = {
                "BEP20": "BSC",
                "ERC20": "ETH",
                "TRC20": "TRON",
                "POLYGON": "POLYGON"
            }
            crypto_row.append(
                InlineKeyboardButton(
                    text=f"💰 {network_names.get(network, network)}",
                    callback_data=f"crypto_pay_super_like_{network}_{target_user_id or 0}"
                )
            )
        if crypto_row:
            keyboard.inline_keyboard.append(crypto_row)
    
    # Telegram Payments (карты)
    if settings.PAYMENT_PROVIDER_TOKEN:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="💳 Оплатить картой",
                callback_data="card_pay_super_like"
            )
        ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    ])
    
    price_usd = settings.SUPER_LIKE_PRICE / 100  # Конвертируем центы в доллары
    text = (
        f"💌 Суперлайк - ${price_usd:.2f}\n\n"
        f"Суперлайк позволяет:\n"
        f"• Отправить сообщение или видео\n"
        f"• Привлечь больше внимания\n"
        f"• Выделиться среди других\n\n"
        f"Выберите способ оплаты:"
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "boost")
async def callback_boost(callback: CallbackQuery, session: AsyncSession):
    """Boost анкеты"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Проверяем, есть ли активный boost
    existing_boost = await session.execute(
        select(Boost).where(Boost.user_id == user.id, Boost.expires_at > datetime.utcnow())
    )
    if existing_boost.scalar_one_or_none():
        await callback.answer("У вас уже есть активный boost!", show_alert=True)
        return
    
    # Создаем boost на 24 часа
    boost = Boost(
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    session.add(boost)
    await session.commit()
    
    await callback.answer("💎 Ваша анкета поднята в топ на 24 часа!")


@router.callback_query(F.data.in_(["gender_male", "gender_female"]))
async def callback_gender(callback: CallbackQuery, state: FSMContext):
    """Выбор пола"""
    gender = callback.data
    await state.update_data(gender=gender)
    await callback.message.answer("Кто тебе интересен?", reply_markup=get_interest_keyboard())
    await state.set_state(ProfileCreation.interest)
    await callback.answer()


@router.callback_query(F.data.startswith("interest_"))
async def callback_interest(callback: CallbackQuery, state: FSMContext):
    """Выбор интереса"""
    interest = callback.data
    await state.update_data(interest=interest)
    await callback.message.answer("Из какого ты города?", reply_markup=None)
    await state.set_state(ProfileCreation.city)
    await callback.answer()


@router.callback_query(F.data == "city_location")
async def callback_city_location(callback: CallbackQuery, state: FSMContext):
    """Получение города по геолокации"""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True
    )
    await callback.message.answer(
        "Отправьте свою геолокацию, нажав на кнопку ниже:",
        reply_markup=keyboard
    )
    await state.set_state(ProfileCreation.city)
    await callback.answer()


@router.callback_query(F.data == "city_manual")
async def callback_city_manual(callback: CallbackQuery, state: FSMContext):
    """Ввод города вручную"""
    await callback.message.answer("Напиши название города:")
    await state.set_state(ProfileCreation.city_manual)
    await callback.answer()


@router.callback_query(F.data == "confirm_yes")
async def callback_confirm_yes(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение анкеты"""
    data = await state.get_data()
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Обновляем данные
        user.age = data.get("age")
        user.name = data.get("name")
        user.description = data.get("description")
        user.city = data.get("city")
        user.photos = data.get("photos", [])
        user.videos = data.get("videos", [])
        
        if data.get("gender") == "gender_male":
            from database.models import Gender
            user.gender = Gender.MALE
        elif data.get("gender") == "gender_female":
            from database.models import Gender
            user.gender = Gender.FEMALE
        
        if data.get("interest") == "interest_male":
            from database.models import Interest
            user.interest = Interest.MALE
        elif data.get("interest") == "interest_female":
            from database.models import Interest
            user.interest = Interest.FEMALE
        elif data.get("interest") == "interest_all":
            from database.models import Interest
            user.interest = Interest.ALL
        
        await session.commit()
    
    lang = user.language or 'ru'
    await callback.message.answer(
        get_text(lang, 'profile_created'),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "confirm_no")
async def callback_confirm_no(callback: CallbackQuery, state: FSMContext):
    """Изменение анкеты"""
    await callback.message.answer("Сколько тебе лет?")
    await state.set_state(ProfileCreation.age)
    await callback.answer()


@router.callback_query(F.data == "pause_confirm")
async def callback_pause_confirm(callback: CallbackQuery):
    """Подтверждение паузы"""
    await callback.message.edit_text(
        "Так ты не узнаешь, что кому-то нравишься... Точно хочешь отключить свою анкету?",
        reply_markup=get_pause_confirm_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "pause_yes")
async def callback_pause_yes(callback: CallbackQuery, session: AsyncSession):
    """Отключение анкеты"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        user.is_active = False
        await session.commit()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Смотреть анкеты", callback_data="view_profiles")
    ]])
    
    await callback.message.edit_text(
        "Надеюсь ты нашел кого-то благодаря мне! Рад был с тобой пообщаться, будет скучно – пиши, обязательно найдем тебе кого-нибудь",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "social_menu")
async def callback_social_menu(callback: CallbackQuery):
    """Меню соцсетей"""
    await callback.message.answer(
        "📱 Социальные сети\n\n"
        "Добавь свои соцсети в анкету:",
        reply_markup=get_social_network_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "edit_media")
async def callback_edit_media(callback: CallbackQuery, state: FSMContext):
    """Изменение фото/видео"""
    await callback.message.answer(
        "Пришли новое фото или запиши видео 👍 (до 15 сек)\n\n"
        "Можно отправить несколько фото. Нажмите /done когда закончите."
    )
    await state.set_state(ProfileCreation.photo)
    await callback.answer()


@router.callback_query(F.data == "edit_text")
async def callback_edit_text(callback: CallbackQuery, state: FSMContext):
    """Изменение текста анкеты"""
    await callback.message.answer(
        "Расскажи о себе и кого хочешь найти, чем предлагаешь заняться. Это поможет лучше подобрать тебе компанию."
    )
    await state.set_state(ProfileCreation.description)
    await callback.answer()


@router.callback_query(F.data == "filters")
async def callback_filters(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Фильтры"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Сначала создай анкету!", show_alert=True)
        return
    
    text = f"""⚙️ Фильтры поиска

Текущие настройки:
• Пол: {user.gender.value if user.gender else 'Не указан'}
• Интерес: {user.interest.value if user.interest else 'Не указан'}
• Город: {user.city or 'Не указан'}

Изменить фильтры можно при редактировании анкеты."""
    
    await callback.message.answer(text, reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "subscription")
async def callback_subscription(callback: CallbackQuery, session: AsyncSession):
    """Меню подписки"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    is_active = user.subscription_status.value == "active" and user.subscription_expires_at and user.subscription_expires_at > datetime.utcnow()
    
    text = f"""💳 Подписка

Статус: {"✅ Активна" if is_active else "❌ Неактивна"}"""
    
    if is_active:
        text += f"\nИстекает: {user.subscription_expires_at.strftime('%d.%m.%Y %H:%M')}"
    else:
        text += "\n\nС подпиской вы получаете:\n• Неограниченные лайки\n• Приоритет в показе анкет\n• Дополнительные функции"
    
    await callback.message.answer(text, reply_markup=get_subscription_keyboard())
    await callback.answer()


@router.callback_query(F.data == "my_profile")
async def callback_my_profile(callback: CallbackQuery, session: AsyncSession):
    """Моя анкета через callback"""
    from handlers.commands import cmd_my_profile
    # Создаем фиктивный message объект из callback
    class FakeMessage:
        def __init__(self, callback):
            self.from_user = callback.from_user
            self.answer = callback.message.answer
            self.text = None
    
    fake_message = FakeMessage(callback)
    await cmd_my_profile(fake_message, session)
    await callback.answer()


@router.callback_query(F.data == "invite_friends")
async def callback_invite_friends(callback: CallbackQuery, session: AsyncSession):
    """Пригласить друзей через callback"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Сначала создай анкету!", show_alert=True)
        return
    
    from sqlalchemy import func
    from datetime import timedelta
    
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
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отправить друзьям в Telegram", url=f"https://t.me/share/url?url={referral_link}&text=MeetUp ❤️")
    ]])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "events_menu")
async def callback_events_menu(callback: CallbackQuery):
    """Меню событий"""
    from keyboards.common import get_events_menu_keyboard
    await callback.message.edit_text(
        "🎉 Мероприятия и события\n\n"
        "Создавай события и находи единомышленников!",
        reply_markup=get_events_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event_edit_"))
async def callback_event_edit(callback: CallbackQuery):
    """Редактирование события"""
    await callback.answer("Функция редактирования событий в разработке", show_alert=True)


@router.callback_query(F.data.startswith("event_delete_"))
async def callback_event_delete(callback: CallbackQuery, session: AsyncSession):
    """Удаление события"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    event = await session.get(Event, event_id)
    if not event or event.creator_id != user.id:
        await callback.answer("Событие не найдено или у вас нет прав!", show_alert=True)
        return
    
    # Удаляем участников
    participants = await session.execute(
        select(EventParticipant).where(EventParticipant.event_id == event_id)
    )
    for participant in participants.scalars().all():
        await session.delete(participant)
    
    await session.delete(event)
    await session.commit()
    
    await callback.answer("✅ Событие удалено!")
    await callback.message.edit_text(
        "✅ Событие удалено",
        reply_markup=get_events_menu_keyboard()
    )




@router.callback_query(F.data.startswith("crypto_pay_subscription_"))
async def callback_crypto_pay_subscription(callback: CallbackQuery, session: AsyncSession):
    """Обработка выбора криптоплатежа для подписки"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.models import Payment
    
    network = callback.data.split("_")[-1]  # BEP20, ERC20, TRC20, POLYGON
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Создаем информацию о платеже
    price_usd = settings.SUBSCRIPTION_PRICE / 100  # Конвертируем центы в доллары
    payment_info = crypto_payment_service.create_payment_info(
        amount_usd=price_usd,
        network=network,
        currency="USDT",
        payment_type="subscription"
    )
    
    if not payment_info:
        await callback.answer("Ошибка создания платежа!", show_alert=True)
        return
    
    # Сохраняем платеж в БД
    payment = Payment(
        user_id=user.id,
        payment_type="subscription",
        amount=settings.SUBSCRIPTION_PRICE,
        crypto_network=network,
        crypto_address=payment_info["wallet_address"],
        crypto_amount=str(payment_info["crypto_amount"]),
        crypto_currency="USDT",
        status="pending",
        expires_at=payment_info["expires_at"]
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    
    # Формируем сообщение
    message_text = crypto_payment_service.format_payment_message(payment_info)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Проверить платеж",
                callback_data=f"check_crypto_payment_{payment.id}"
            )
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back")
        ]
    ])
    
    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("crypto_pay_super_like_"))
async def callback_crypto_pay_super_like(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка выбора криптоплатежа для суперлайка"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from database.models import Payment
    
    parts = callback.data.split("_")
    network = parts[3]  # BEP20, ERC20, TRC20, POLYGON
    target_user_id = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
    
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Сохраняем target_user_id в state
    if target_user_id:
        await state.update_data(super_like_target=target_user_id)
    
    # Создаем информацию о платеже
    price_usd = settings.SUPER_LIKE_PRICE / 100  # Конвертируем центы в доллары
    payment_info = crypto_payment_service.create_payment_info(
        amount_usd=price_usd,
        network=network,
        currency="USDT",
        payment_type="super_like"
    )
    
    if not payment_info:
        await callback.answer("Ошибка создания платежа!", show_alert=True)
        return
    
    # Сохраняем платеж в БД
    payment = Payment(
        user_id=user.id,
        payment_type="super_like",
        amount=settings.SUPER_LIKE_PRICE,
        crypto_network=network,
        crypto_address=payment_info["wallet_address"],
        crypto_amount=str(payment_info["crypto_amount"]),
        crypto_currency="USDT",
        status="pending",
        expires_at=payment_info["expires_at"]
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    
    # Формируем сообщение
    message_text = crypto_payment_service.format_payment_message(payment_info)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Проверить платеж",
                callback_data=f"check_crypto_payment_{payment.id}"
            )
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back")
        ]
    ])
    
    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "card_pay_subscription")
async def callback_card_pay_subscription(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Оплата подписки картой через Telegram Payments"""
    user_id = callback.from_user.id
    
    if not settings.PAYMENT_PROVIDER_TOKEN:
        await callback.answer("Оплата картой недоступна", show_alert=True)
        return
    
    prices = [LabeledPrice(label="Подписка на месяц", amount=settings.SUBSCRIPTION_PRICE)]
    await telegram_payment_service.create_subscription_invoice(
        bot=bot,
        chat_id=callback.message.chat.id,
        user_id=user_id,
        prices=prices
    )
    await callback.answer()


@router.callback_query(F.data == "card_pay_super_like")
async def callback_card_pay_super_like(callback: CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    """Оплата суперлайка картой через Telegram Payments"""
    user_id = callback.from_user.id
    
    # Получаем target_user_id из state
    data = await state.get_data()
    target_user_id = data.get("super_like_target")
    
    if not settings.PAYMENT_PROVIDER_TOKEN:
        await callback.answer("Оплата картой недоступна", show_alert=True)
        return
    
    prices = [LabeledPrice(label="Суперлайк", amount=settings.SUPER_LIKE_PRICE)]
    await telegram_payment_service.create_super_like_invoice(
        bot=bot,
        chat_id=callback.message.chat.id,
        user_id=user_id,
        target_user_id=target_user_id or user_id,
        prices=prices
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_crypto_payment_"))
async def callback_check_crypto_payment(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Проверка криптоплатежа"""
    from database.models import Payment, SubscriptionStatus
    from datetime import datetime, timedelta
    
    payment_id = int(callback.data.split("_")[-1])
    
    payment = await session.get(Payment, payment_id)
    if not payment:
        await callback.answer("Платеж не найден!", show_alert=True)
        return
    
    if payment.status == "completed":
        await callback.answer("✅ Платеж уже подтвержден!", show_alert=True)
        return
    
    if payment.status == "expired":
        await callback.answer("❌ Время платежа истекло!", show_alert=True)
        return
    
    # Проверяем транзакцию
    is_paid, tx_hash = await crypto_payment_service.check_transaction(
        network=payment.crypto_network,
        wallet_address=payment.crypto_address,
        amount=float(payment.crypto_amount),
        currency=payment.crypto_currency,
        transaction_hash=payment.transaction_hash
    )
    
    if is_paid:
        # Обновляем платеж
        payment.status = "completed"
        payment.transaction_hash = tx_hash
        payment.completed_at = datetime.now()
        
        # Обрабатываем в зависимости от типа платежа
        result = await session.execute(select(User).where(User.id == payment.user_id))
        user = result.scalar_one_or_none()
        
        if user:
            if payment.payment_type == "subscription":
                user.subscription_status = SubscriptionStatus.ACTIVE
                user.subscription_expires_at = datetime.now() + timedelta(days=30)
                
                await callback.message.answer(
                    "✅ Подписка успешно активирована!\n\n"
                    f"Теперь у вас:\n"
                    f"• Неограниченные лайки\n"
                    f"• Приоритет в показе анкет\n"
                    f"• Ранний доступ к новым функциям\n\n"
                    f"Подписка активна до {user.subscription_expires_at.strftime('%d.%m.%Y')}",
                    parse_mode="HTML"
                )
            
            elif payment.payment_type == "super_like":
                await callback.message.answer(
                    "✅ Суперлайк оплачен!\n\n"
                    "Теперь вы можете отправить суперлайк при просмотре профилей."
                )
        
        await session.commit()
        await callback.answer("✅ Платеж подтвержден!", show_alert=True)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"✅ <b>Платеж подтвержден!</b>\n\n"
            f"Транзакция: <code>{tx_hash}</code>\n"
            f"Сумма: {payment.crypto_amount} {payment.crypto_currency}",
            parse_mode="HTML"
        )
    else:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Предлагаем ввести хеш транзакции вручную
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Ввести хеш транзакции",
                    callback_data=f"enter_tx_hash_{payment.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить снова",
                    callback_data=f"check_crypto_payment_{payment.id}"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back")
            ]
        ])
        
        await callback.message.edit_text(
            f"⏳ <b>Платеж еще не найден</b>\n\n"
            f"Попробуйте:\n"
            f"• Подождать 1-2 минуты и нажать 'Проверить снова'\n"
            f"• Или ввести хеш транзакции вручную\n\n"
            f"<b>Убедитесь, что:</b>\n"
            f"• Вы отправили правильную сумму ({payment.crypto_amount} {payment.crypto_currency})\n"
            f"• Использовали правильную сеть ({payment.crypto_network})\n"
            f"• Отправили на адрес: <code>{payment.crypto_address}</code>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Платеж не найден. Попробуйте позже или введите хеш транзакции.")


@router.callback_query(F.data.startswith("enter_tx_hash_"))
async def callback_enter_tx_hash(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод хеша транзакции"""
    payment_id = int(callback.data.split("_")[-1])
    await state.update_data(payment_id=payment_id)
    await state.set_state(CryptoPayment.transaction_hash)
    
    await callback.message.answer(
        "📝 <b>Введите хеш транзакции</b>\n\n"
        "Скопируйте хеш транзакции из вашего кошелька и отправьте его сюда.\n\n"
        "Хеш транзакции выглядит так:\n"
        "• BEP20/ERC20/Polygon: <code>0x1234...abcd</code>\n"
        "• TRC20: <code>abc123...def456</code>\n\n"
        "Или отправьте /cancel для отмены",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CryptoPayment.transaction_hash)
async def process_transaction_hash(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Обработка введенного хеша транзакции"""
    from database.models import Payment, SubscriptionStatus
    from datetime import datetime, timedelta
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    tx_hash = message.text.strip()
    data = await state.get_data()
    payment_id = data.get("payment_id")
    
    if not payment_id:
        await message.answer("Ошибка! Начните заново.")
        await state.clear()
        return
    
    payment = await session.get(Payment, payment_id)
    if not payment:
        await message.answer("Платеж не найден!")
        await state.clear()
        return
    
    if payment.status == "completed":
        await message.answer("✅ Платеж уже подтвержден!")
        await state.clear()
        return
    
    # Проверяем транзакцию с указанным хешем
    is_paid, verified_tx_hash = await crypto_payment_service.check_transaction(
        network=payment.crypto_network,
        wallet_address=payment.crypto_address,
        amount=float(payment.crypto_amount),
        currency=payment.crypto_currency,
        transaction_hash=tx_hash
    )
    
    if is_paid:
        # Обновляем платеж
        payment.status = "completed"
        payment.transaction_hash = verified_tx_hash or tx_hash
        payment.completed_at = datetime.now()
        
        # Обрабатываем в зависимости от типа платежа
        result = await session.execute(select(User).where(User.id == payment.user_id))
        user = result.scalar_one_or_none()
        
        if user:
            if payment.payment_type == "subscription":
                user.subscription_status = SubscriptionStatus.ACTIVE
                user.subscription_expires_at = datetime.now() + timedelta(days=30)
                
                await message.answer(
                    "✅ Подписка успешно активирована!\n\n"
                    f"Теперь у вас:\n"
                    f"• Неограниченные лайки\n"
                    f"• Приоритет в показе анкет\n"
                    f"• Ранний доступ к новым функциям\n\n"
                    f"Подписка активна до {user.subscription_expires_at.strftime('%d.%m.%Y')}",
                    parse_mode="HTML"
                )
            
            elif payment.payment_type == "super_like":
                await message.answer(
                    "✅ Суперлайк оплачен!\n\n"
                    "Теперь вы можете отправить суперлайк при просмотре профилей."
                )
        
        await session.commit()
        await message.answer(
            f"✅ <b>Платеж подтвержден!</b>\n\n"
            f"Транзакция: <code>{payment.transaction_hash}</code>\n"
            f"Сумма: {payment.crypto_amount} {payment.crypto_currency}",
            parse_mode="HTML"
        )
        await state.clear()
    else:
        await message.answer(
            "❌ <b>Транзакция не найдена или неверна</b>\n\n"
            "Проверьте:\n"
            "• Правильность хеша транзакции\n"
            "• Что транзакция отправлена на правильный адрес\n"
            "• Что транзакция подтверждена в блокчейне\n\n"
            "Попробуйте ввести хеш еще раз или отправьте /cancel",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery):
    """Назад"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()

