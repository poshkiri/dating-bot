"""
Система локализации для бота знакомств
"""
from typing import Dict, Callable, Any


def get_text(lang: str, key: str, **kwargs) -> str:
    """
    Получить текст на нужном языке
    
    Args:
        lang: Код языка (ru, en)
        key: Ключ текста
        **kwargs: Параметры для форматирования текста
    
    Returns:
        Текст на нужном языке
    """
    texts = TRANSLATIONS.get(lang, TRANSLATIONS['ru'])
    text = texts.get(key, TRANSLATIONS['ru'].get(key, key))
    
    # Если текст - функция, вызываем её
    if callable(text):
        return text(**kwargs)
    
    # Форматирование, если есть параметры
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text


TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    'ru': {
        # Приветствие
        'welcome': '👋 Добро пожаловать в бот знакомств Лилит! 🍷\n\nДавайте создадим твою анкету, чтобы найти интересных людей!',
        'welcome_back': '👋 С возвращением!\n\nТвоя анкета еще не заполнена. Давайте создадим её!',
        'welcome_complete': '👋 С возвращением!',
        
        # Создание анкеты
        'ask_age': 'Сколько тебе лет?',
        'ask_name': 'Как тебя зовут?',
        'ask_gender': 'Какой у тебя пол?',
        'ask_interest': 'Кого ты ищешь?',
        'ask_city': 'В каком городе ты находишься?',
        'ask_description': 'Расскажи о себе:',
        'ask_photo': 'Отправь свое фото (можно несколько):',
        'ask_video': 'Отправь видео (опционально):',
        'profile_created': '✅ Анкета создана! Теперь ты можешь искать интересных людей!',
        
        # Кнопки главного меню
        'btn_my_profile': '👤 Моя анкета',
        'btn_view_profiles': '❤️ Смотреть анкеты',
        'btn_complaint': '🚫 Пожаловаться',
        'btn_language': '🌍 Язык',
        'btn_help': '📖 Руководство',
        'btn_events': '🎉 Тусовки',
        'btn_stats': '📊 Статистика',
        'btn_support': '💬 Поддержка',
        'btn_invite': '👥 Пригласи друзей',
        
        # Профиль
        'profile_not_filled': 'Сначала заполни анкету!',
        'profile_disabled': 'Твоя анкета отключена. Включи её в настройках!',
        'no_profiles': '💤 Подождем пока кто-то увидит твою анкету\n\nПока новых анкет нет. Попробуй позже!',
        
        # Язык
        'select_language': '🌍 Выберите язык / Choose language:',
        'language_changed_ru': '✅ Язык изменен на русский',
        'language_changed_en': '✅ Language changed to English',
        'error_start': 'Ошибка! Начните с /start',
        
        # Лайки
        'like_sent': '❤️ Лайк отправлен!',
        'mutual_like': '💕 Взаимная симпатия! Теперь вы можете видеть username друг друга.',
        'dislike_sent': '👎 Дизлайк отправлен',
        'super_like_sent': '💌 Суперлайк отправлен!',
        
        # Ошибки
        'error': 'Ошибка!',
        'error_not_found': 'Не найдено',
        
        # Кнопки просмотра профиля
        'btn_like': '❤️ Лайк',
        'btn_dislike': '👎🏼 Дизлайк',
        'btn_super_like': '💌 Суперлайк',
        'btn_next': '⏭️ Следующая',
        
        # Пол
        'gender_female': '👩 Я девушка',
        'gender_male': '👨 Я парень',
        
        # Интересы
        'interest_female': '👩 Девушки',
        'interest_male': '👨 Парни',
        'interest_all': '👥 Всё равно',
        
        # Город
        'city_location': '📍 Показать мои координаты',
        'city_manual': '✏️ Ввести вручную',
        
        # Подтверждение
        'btn_yes': '✅ Да',
        'btn_no': '✏️ Изменить',
        
        # Жалобы
        'complaint_reason': 'Почему ты хочешь пожаловаться?',
        'complaint_adult': '🔞 Материал для взрослых',
        'complaint_selling': '💰 Продажа товаров и услуг',
        'complaint_dislike': '💩 Не нравится',
        'complaint_other': '🦨 Другое',
        'complaint_sent': '✅ Жалоба отправлена. Спасибо!',
        
        # Назад
        'btn_back': '🔙 Назад',
        
        # События
        'btn_create_event': '➕ Создать событие',
        'btn_my_events': '📅 Мои события',
        'btn_all_events': '🎉 Все события',
        
        # Подписка
        'subscription_price': '💳 Купить подписку ($9.99)',
        'super_like_price': '💳 Купить суперлайк ($1.99)',
        
        # Соцсети
        'social_instagram': '📷 Instagram',
        'social_vk': '🔵 VK',
        'social_skip': '⏭️ Пропустить',
        
        # Верификация
        'verify': '✅ Верификация',
        
        # Boost
        'boost': '💎 Boost анкеты',
        
        # Подписка
        'subscription': '💳 Подписка',
    },
    'en': {
        # Welcome
        'welcome': '👋 Welcome to Lilith dating bot! 🍷\n\nLet\'s create your profile to find interesting people!',
        'welcome_back': '👋 Welcome back!\n\nYour profile is not filled yet. Let\'s create it!',
        'welcome_complete': '👋 Welcome back!',
        
        # Profile creation
        'ask_age': 'How old are you?',
        'ask_name': 'What\'s your name?',
        'ask_gender': 'What\'s your gender?',
        'ask_interest': 'Who are you looking for?',
        'ask_city': 'What city are you in?',
        'ask_description': 'Tell us about yourself:',
        'ask_photo': 'Send your photo (you can send several):',
        'ask_video': 'Send a video (optional):',
        'profile_created': '✅ Profile created! Now you can search for interesting people!',
        
        # Main menu buttons
        'btn_my_profile': '👤 My Profile',
        'btn_view_profiles': '❤️ View Profiles',
        'btn_complaint': '🚫 Report',
        'btn_language': '🌍 Language',
        'btn_help': '📖 Guide',
        'btn_events': '🎉 Events',
        'btn_stats': '📊 Statistics',
        'btn_support': '💬 Support',
        'btn_invite': '👥 Invite Friends',
        
        # Profile
        'profile_not_filled': 'Fill in your profile first!',
        'profile_disabled': 'Your profile is disabled. Enable it in settings!',
        'no_profiles': '💤 Let\'s wait until someone sees your profile\n\nNo new profiles yet. Try again later!',
        
        # Language
        'select_language': '🌍 Choose language / Выберите язык:',
        'language_changed_ru': '✅ Language changed to Russian',
        'language_changed_en': '✅ Language changed to English',
        'error_start': 'Error! Start with /start',
        
        # Likes
        'like_sent': '❤️ Like sent!',
        'mutual_like': '💕 Mutual like! Now you can see each other\'s username.',
        'dislike_sent': '👎 Dislike sent',
        'super_like_sent': '💌 Super like sent!',
        
        # Errors
        'error': 'Error!',
        'error_not_found': 'Not found',
        
        # Profile view buttons
        'btn_like': '❤️ Like',
        'btn_dislike': '👎 Dislike',
        'btn_super_like': '💌 Super Like',
        'btn_next': '⏭️ Next',
        
        # Gender
        'gender_female': '👩 I\'m a girl',
        'gender_male': '👨 I\'m a guy',
        
        # Interests
        'interest_female': '👩 Girls',
        'interest_male': '👨 Guys',
        'interest_all': '👥 Anyone',
        
        # City
        'city_location': '📍 Show my location',
        'city_manual': '✏️ Enter manually',
        
        # Confirmation
        'btn_yes': '✅ Yes',
        'btn_no': '✏️ Edit',
        
        # Complaints
        'complaint_reason': 'Why do you want to report?',
        'complaint_adult': '🔞 Adult content',
        'complaint_selling': '💰 Selling goods and services',
        'complaint_dislike': '💩 Don\'t like',
        'complaint_other': '🦨 Other',
        'complaint_sent': '✅ Report sent. Thank you!',
        
        # Back
        'btn_back': '🔙 Back',
        
        # Events
        'btn_create_event': '➕ Create Event',
        'btn_my_events': '📅 My Events',
        'btn_all_events': '🎉 All Events',
        
        # Subscription
        'subscription_price': '💳 Buy subscription ($9.99)',
        'super_like_price': '💳 Buy super like ($1.99)',
        
        # Social networks
        'social_instagram': '📷 Instagram',
        'social_vk': '🔵 VK',
        'social_skip': '⏭️ Skip',
        
        # Verification
        'verify': '✅ Verification',
        
        # Boost
        'boost': '💎 Boost profile',
        
        # Subscription
        'subscription': '💳 Subscription',
    }
}

