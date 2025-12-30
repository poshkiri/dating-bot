from aiogram import Router, F
from aiogram.types import Message, PhotoSize, Video
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Event, EventParticipant
from keyboards.common import *
from utils.helpers import format_profile_text
from utils.locales import get_text
from datetime import datetime
import re
from handlers.states import ProfileCreation, EventCreation, SuperLike, Support

router = Router()


@router.message(F.text == "❤️ Смотреть анкеты")
async def message_view_profiles(message: Message, session: AsyncSession, state: FSMContext):
    """Просмотр анкет через кнопку"""
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    lang = user.language if user else 'ru'
    
    if not user or not user.name:
        await message.answer(get_text(lang, 'profile_not_filled'))
        return
    
    if not user.is_active:
        await message.answer(get_text(lang, 'profile_disabled'))
        return
    
    from utils.helpers import get_next_profile
    next_profile = await get_next_profile(session, user)
    
    if not next_profile:
        await message.answer(
            get_text(lang, 'no_profiles'),
            reply_markup=get_pause_menu_keyboard(lang)
        )
        return
    
    text = format_profile_text(next_profile)
    # Сохраняем ID профиля для жалоб
    await state.update_data(last_viewed_user_id=next_profile.id)
    
    keyboard = get_profile_view_keyboard(lang)
    keyboard.inline_keyboard[0][0].callback_data = f"like_{next_profile.id}"
    keyboard.inline_keyboard[0][1].callback_data = f"dislike_{next_profile.id}"
    keyboard.inline_keyboard[0][2].callback_data = f"super_like_{next_profile.id}"
    keyboard.inline_keyboard[1][0].callback_data = f"next_profile"
    
    # Приоритет: сначала видео, потом фото
    if next_profile.videos and len(next_profile.videos) > 0:
        try:
            await message.answer_video(next_profile.videos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить видео профиля: {e}. Пробуем фото.")
            # Если видео не отправилось, пробуем фото
            if next_profile.photos and len(next_profile.photos) > 0:
                try:
                    await message.answer_photo(next_profile.photos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
                except:
                    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    elif next_profile.photos and len(next_profile.photos) > 0:
        try:
            await message.answer_photo(next_profile.photos[0], caption=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            # Если file_id невалиден (например, от старого бота), отправляем только текст
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить фото профиля: {e}. Отправляем текст без фото.")
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(ProfileCreation.age)
async def process_age(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка возраста"""
    try:
        age = int(message.text)
        if age < 18 or age > 100:
            await message.answer("Пожалуйста, введите реальный возраст (18-100 лет)")
            return
        await state.update_data(age=age)
        await message.answer(
            "Теперь определимся с полом",
            reply_markup=get_gender_keyboard()
        )
        await state.set_state(ProfileCreation.gender)
    except ValueError:
        await message.answer("Пожалуйста, введите число")


@router.message(ProfileCreation.city)
async def process_city(message: Message, state: FSMContext):
    """Обработка города"""
    city = message.text.strip()
    await state.update_data(city=city)
    await message.answer("Как мне тебя называть?")
    await state.set_state(ProfileCreation.name)


# Обработка геолокации убрана - теперь только текстовый ввод города


@router.message(ProfileCreation.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени"""
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(
        "Расскажи о себе и кого хочешь найти, чем предлагаешь заняться. Это поможет лучше подобрать тебе компанию."
    )
    await state.set_state(ProfileCreation.description)


@router.message(ProfileCreation.description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания"""
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer(
        "Пришли фото или запиши видео 👍 (до 15 сек)\n\n"
        "Можно отправить несколько фото"
    )
    await state.set_state(ProfileCreation.photo)


@router.message(ProfileCreation.photo, F.photo)
async def process_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка фото"""
    photo = message.photo[-1]  # Берем самое большое фото
    file_id = photo.file_id
    
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(file_id)
    await state.update_data(photos=photos)
    
    await message.answer("Фото добавлено! Отправьте еще или нажмите /done для завершения")


@router.message(ProfileCreation.photo, F.video)
async def process_video(message: Message, state: FSMContext):
    """Обработка видео"""
    video = message.video
    if video.duration and video.duration > 15:
        await message.answer("Видео должно быть не более 15 секунд!")
        return
    
    file_id = video.file_id
    data = await state.get_data()
    videos = data.get("videos", [])
    videos.append(file_id)
    await state.update_data(videos=videos)
    
    await message.answer("Видео добавлено! Отправьте фото или нажмите /done для завершения")


@router.message(ProfileCreation.photo, F.text == "/done")
async def process_done(message: Message, state: FSMContext, session: AsyncSession):
    """Завершение создания анкеты"""
    data = await state.get_data()
    user_id = message.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Ошибка! Начните с /start")
        await state.clear()
        return
    
    # Обновляем данные пользователя
    from database.models import Gender, Interest
    user.age = data.get("age")
    user.name = data.get("name")
    user.description = data.get("description")
    user.city = data.get("city")
    user.photos = data.get("photos", [])
    user.videos = data.get("videos", [])
    user.latitude = data.get("latitude")
    user.longitude = data.get("longitude")
    
    if data.get("gender") == "gender_male":
        user.gender = Gender.MALE
    elif data.get("gender") == "gender_female":
        user.gender = Gender.FEMALE
    
    if data.get("interest") == "interest_male":
        user.interest = Interest.MALE
    elif data.get("interest") == "interest_female":
        user.interest = Interest.FEMALE
    elif data.get("interest") == "interest_all":
        user.interest = Interest.ALL
    
    await session.commit()
    
    # Показываем анкету для подтверждения
    text = "Так выглядит твоя анкета:\n\n"
    text += format_profile_text(user)
    
    if user.photos and len(user.photos) > 0:
        try:
            await message.answer_photo(user.photos[0], caption=text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
        except Exception as e:
            # Если file_id невалиден (например, от старого бота), отправляем только текст
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить фото: {e}. Отправляем текст без фото.")
            await message.answer(text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=get_confirm_keyboard(), parse_mode="HTML")
    
    await state.set_state(ProfileCreation.confirm)


@router.message(EventCreation.title)
async def process_event_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    title = message.text.strip()
    await state.update_data(title=title)
    await message.answer("Опиши событие подробнее:")
    await state.set_state(EventCreation.description)


@router.message(EventCreation.description)
async def process_event_description(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка описания события"""
    description = message.text.strip()
    await state.update_data(description=description)
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if user and user.city:
        await message.answer(f"Город: {user.city}\n\nИли введи другой город:")
        await state.set_state(EventCreation.city)
    else:
        await message.answer("Какой город?")
        await state.set_state(EventCreation.city)


@router.message(EventCreation.city)
async def process_event_city(message: Message, state: FSMContext):
    """Обработка города события"""
    city = message.text.strip()
    await state.update_data(city=city)
    await message.answer("Когда состоится событие? (формат: ДД.ММ.ГГГГ ЧЧ:ММ)")
    await state.set_state(EventCreation.date)


@router.message(EventCreation.date)
async def process_event_date(message: Message, state: FSMContext):
    """Обработка даты события"""
    try:
        date_str = message.text.strip()
        event_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        await state.update_data(event_date=event_date)
        await message.answer("Пришли фото события (или /skip для пропуска):")
        await state.set_state(EventCreation.photo)
    except ValueError:
        await message.answer("Неверный формат даты! Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")


@router.message(EventCreation.photo, F.photo)
async def process_event_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка фото события"""
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(photo=file_id)
    await create_event(message, state, session)


@router.message(EventCreation.photo, F.text == "/skip")
async def process_event_photo_skip(message: Message, state: FSMContext, session: AsyncSession):
    """Пропуск фото события"""
    await create_event(message, state, session)


async def create_event(message: Message, state: FSMContext, session: AsyncSession):
    """Создание события"""
    data = await state.get_data()
    user_id = message.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Ошибка!")
        await state.clear()
        return
    
    event = Event(
        creator_id=user.id,
        title=data.get("title"),
        description=data.get("description"),
        city=data.get("city"),
        event_date=data.get("event_date"),
        photo=data.get("photo")
    )
    session.add(event)
    await session.commit()
    
    await message.answer(
        f"✅ Событие '{event.title}' создано!\n\n"
        f"Город: {event.city}\n"
        f"Дата: {event.event_date.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=get_events_menu_keyboard()
    )
    await state.clear()


@router.message(SuperLike.message)
async def process_super_like_message(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка сообщения для суперлайка"""
    user_id = message.from_user.id
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    
    if not target_user_id:
        await message.answer("Ошибка! Пользователь не найден.")
        await state.clear()
        return
    
    # Получаем пользователей
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    result_target = await session.execute(select(User).where(User.id == target_user_id))
    target_user = result_target.scalar_one_or_none()
    
    if not user or not target_user:
        await message.answer("Ошибка!")
        await state.clear()
        return
    
    # Создаем суперлайк
    from database.models import Like
    like = Like(
        from_user_id=user.id,
        to_user_id=target_user_id,
        is_super_like=True
    )
    
    if message.text:
        like.message = message.text
        await message.answer("💌 Суперлайк отправлен!")
    elif message.video:
        if message.video.duration and message.video.duration > 15:
            await message.answer("Видео должно быть не более 15 секунд!")
            return
        like.video = message.video.file_id
        await message.answer("💌 Суперлайк с видео отправлен!")
    else:
        await message.answer("Отправьте текст или видео!")
        return
    
    session.add(like)
    user.total_likes += 1
    target_user.total_likes += 1
    
    # Проверяем взаимную симпатию
    from utils.helpers import check_mutual_like
    is_mutual = await check_mutual_like(session, user.id, target_user_id)
    if is_mutual:
        like.is_mutual = True
        prev_like = await session.execute(
            select(Like).where(Like.from_user_id == target_user_id, Like.to_user_id == user.id)
        )
        prev_like_obj = prev_like.scalar_one_or_none()
        if prev_like_obj:
            prev_like_obj.is_mutual = True
        
        target_name = target_user.name or target_user.first_name or "Пользователь"
        target_username = target_user.username or ""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        mutual_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👤 Посмотреть анкету", callback_data=f"view_profile_{target_user.id}")
        ]])
        
        mutual_text = f"💕 Взаимная симпатия!\n\n"
        mutual_text += f"👤 {target_name}"
        if target_username:
            mutual_text += f" (@{target_username})"
        mutual_text += f"\n\nВы понравились друг другу!"
        
        await message.answer(
            mutual_text,
            reply_markup=mutual_keyboard
        )
    
    await session.commit()
    
    # УВЕДОМЛЯЕМ пользователя о суперлайке (для всех, включая бесплатных)
    try:
        liker_name = user.name or user.first_name or "Кто-то"
        liker_username = user.username or ""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        notification_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👤 Посмотреть анкету", callback_data=f"view_profile_{user.id}")
        ]])
        
        notification_text = f"⭐ Вам поставили суперлайк!\n\n"
        notification_text += f"👤 {liker_name}"
        if liker_username:
            notification_text += f" (@{liker_username})"
        
        if message.text:
            notification_text += f"\n\n💬 Сообщение: {message.text}"
        
        # Отправляем уведомление
        if message.video:
            await message.bot.send_video(
                target_user.telegram_id,
                message.video.file_id,
                caption=notification_text,
                reply_markup=notification_keyboard
            )
        else:
            await message.bot.send_message(
                target_user.telegram_id,
                notification_text,
                reply_markup=notification_keyboard
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось отправить уведомление о суперлайке пользователю {target_user.telegram_id}: {e}")
    
    await state.clear()


@router.message(Support.waiting_message)
async def process_support_message(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка сообщений в поддержку"""
    from database.models import SupportChat, SupportMessage
    from sqlalchemy import select
    from config import settings
    
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Ошибка! Начните с /start")
        await state.clear()
        return
    
    # Проверяем команду отмены
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отправка сообщения в поддержку отменена", reply_markup=get_main_menu_keyboard())
        return
    
    # Находим активный чат поддержки
    chat_result = await session.execute(
        select(SupportChat).where(
            SupportChat.user_id == user.id,
            SupportChat.is_active == True
        )
    )
    chat = chat_result.scalar_one_or_none()
    
    if not chat:
        # Создаем новый чат
        chat = SupportChat(user_id=user.id)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    
    # Сохраняем сообщение
    support_message = SupportMessage(
        chat_id=chat.id,
        from_user_id=user.id,
        is_from_admin=False,
        message_text=message.text if message.text else None,
        photo=message.photo[-1].file_id if message.photo else None,
        video=message.video.file_id if message.video else None
    )
    session.add(support_message)
    await session.commit()
    
    # Формируем сообщение для администраторов
    user_info = f"Пользователь: {user.name or 'Без имени'}\n"
    user_info += f"ID: {user.telegram_id}\n"
    if user.username:
        user_info += f"Username: @{user.username}\n"
    user_info += f"Чат поддержки ID: {chat.id}\n\n"
    
    admin_text = f"💬 Новое сообщение в поддержку\n\n{user_info}"
    
    if message.text:
        admin_text += f"Сообщение: {message.text}"
    else:
        admin_text += "Сообщение с медиа"
    
    # Отправляем администраторам
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"support_reply_{chat.id}")
    ]])
    
    sent_to_admins = False
    for admin_id in settings.admin_ids:
        try:
            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=admin_text,
                    reply_markup=keyboard
                )
            elif message.video:
                await message.bot.send_video(
                    admin_id,
                    message.video.file_id,
                    caption=admin_text,
                    reply_markup=keyboard
                )
            else:
                await message.bot.send_message(
                    admin_id,
                    admin_text,
                    reply_markup=keyboard
                )
            sent_to_admins = True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки сообщения администратору {admin_id}: {e}")
    
    if sent_to_admins:
        await message.answer(
            "✅ Ваше сообщение отправлено администратору. Ожидайте ответа!\n\n"
            "Для отмены отправьте /cancel",
            reply_markup=None
        )
    else:
        await message.answer(
            "⚠️ К сожалению, администраторы сейчас недоступны. Попробуйте позже.\n\n"
            "Для отмены отправьте /cancel",
            reply_markup=None
        )


@router.message()
async def process_other_messages(message: Message):
    """Обработка остальных сообщений"""
    # Игнорируем команды и сообщения, которые уже обработаны другими обработчиками
    pass

