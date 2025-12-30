from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from utils.locales import get_text


def get_main_menu_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text(lang, 'btn_my_profile')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_view_profiles')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_complaint')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_help')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_events')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_stats')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_support')))
    builder.add(KeyboardButton(text=get_text(lang, 'btn_invite')))
    builder.adjust(2, 2, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_profile_view_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Клавиатура для просмотра анкеты"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_like'), callback_data="like"))
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_dislike'), callback_data="dislike"))
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_super_like'), callback_data="super_like"))
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_next'), callback_data="next_profile"))
    builder.adjust(3, 1)
    return builder.as_markup()


def get_my_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для моей анкеты"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="1️⃣ Смотреть анкеты", callback_data="view_profiles"))
    builder.add(InlineKeyboardButton(text="2️⃣ Заполнить анкету заново", callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text="3️⃣ Изменить фото/видео", callback_data="edit_media"))
    builder.add(InlineKeyboardButton(text="4️⃣ Изменить текст анкеты", callback_data="edit_text"))
    builder.add(InlineKeyboardButton(text="⚙️ Фильтры", callback_data="filters"))
    builder.add(InlineKeyboardButton(text="✅ Верификация", callback_data="verify"))
    builder.add(InlineKeyboardButton(text="📱 Соцсети", callback_data="social_menu"))
    builder.add(InlineKeyboardButton(text="💎 Boost анкеты", callback_data="boost"))
    builder.add(InlineKeyboardButton(text="💳 Подписка", callback_data="subscription"))
    builder.adjust(1)
    return builder.as_markup()


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Выбор пола"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👩 Я девушка", callback_data="gender_female"))
    builder.add(InlineKeyboardButton(text="👨 Я парень", callback_data="gender_male"))
    return builder.as_markup()


def get_interest_keyboard() -> InlineKeyboardMarkup:
    """Выбор интереса"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👩 Девушки", callback_data="interest_female"))
    builder.add(InlineKeyboardButton(text="👨 Парни", callback_data="interest_male"))
    builder.add(InlineKeyboardButton(text="👥 Всё равно", callback_data="interest_all"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_city_keyboard() -> InlineKeyboardMarkup:
    """Выбор города"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📍 Показать мои координаты", callback_data="city_location"))
    builder.add(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="city_manual"))
    return builder.as_markup()


def get_social_network_keyboard() -> InlineKeyboardMarkup:
    """Выбор соцсети"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📷 Instagram", callback_data="social_instagram"))
    builder.add(InlineKeyboardButton(text="🔵 VK", callback_data="social_vk"))
    builder.add(InlineKeyboardButton(text="⏭️ Пропустить", callback_data="social_skip"))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"))
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm_no"))
    return builder.as_markup()


def get_complaint_reason_keyboard() -> InlineKeyboardMarkup:
    """Причины жалобы"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔞 Материал для взрослых", callback_data="complaint_adult"))
    builder.add(InlineKeyboardButton(text="💰 Продажа товаров и услуг", callback_data="complaint_selling"))
    builder.add(InlineKeyboardButton(text="💩 Не нравится", callback_data="complaint_dislike"))
    builder.add(InlineKeyboardButton(text="🦨 Другое", callback_data="complaint_other"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_events_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню мероприятий"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Создать событие", callback_data="event_create"))
    builder.add(InlineKeyboardButton(text="📅 Мои события", callback_data="event_my"))
    builder.add(InlineKeyboardButton(text="🎉 Все события", callback_data="event_all"))
    builder.adjust(1)
    return builder.as_markup()


def get_event_keyboard(event_id: int, is_creator: bool = False, is_participant: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для события"""
    builder = InlineKeyboardBuilder()
    if not is_participant:
        builder.add(InlineKeyboardButton(text="✅ Участвовать", callback_data=f"event_join_{event_id}"))
    else:
        builder.add(InlineKeyboardButton(text="❌ Отменить участие", callback_data=f"event_leave_{event_id}"))
    if is_creator:
        builder.add(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"event_edit_{event_id}"))
        builder.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"event_delete_{event_id}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="events_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подписки"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 Купить подписку ($9.99)", callback_data="buy_subscription"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    return builder.as_markup()


def get_super_like_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура суперлайка"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💳 Купить суперлайк ($1.99)", callback_data="buy_super_like"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    return builder.as_markup()


def get_pause_menu_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню паузы"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_view_profiles'), callback_data="view_profiles"))
    builder.add(InlineKeyboardButton(text=get_text(lang, 'btn_my_profile'), callback_data="my_profile"))
    # Только русский язык
    pause_text = "3️⃣ Я больше не хочу никого искать"
    invite_text = get_text(lang, 'btn_invite')
    builder.add(InlineKeyboardButton(text=pause_text, callback_data="pause_confirm"))
    builder.add(InlineKeyboardButton(text=invite_text, callback_data="invite_friends"))
    builder.adjust(1)
    return builder.as_markup()


def get_pause_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение паузы"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="😴 Отключить анкету", callback_data="pause_yes"))
    builder.add(InlineKeyboardButton(text="🚀 Смотреть анкеты", callback_data="view_profiles"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    builder.adjust(1)
    return builder.as_markup()

