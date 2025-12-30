from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import User, AdminMessage, Complaint, Like, Dislike, Event
from config import settings
from keyboards.common import get_back_keyboard
import json

router = Router()


from handlers.states import AdminBroadcast, AdminSupportReply


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in settings.admin_ids


@router.message(F.text == "/admin")
async def cmd_admin(message: Message, session: AsyncSession):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещен!")
        return
    
    text = """🔧 Админ-панель

Выберите действие:
1. 📊 Статистика
2. 📢 Рассылка
3. 🛡️ Модерация
4. 👥 Пользователи
5. 📝 События"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🛡️ Модерация", callback_data="admin_moderation")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📝 События", callback_data="admin_events")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика для админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    # Общая статистика
    total_users = await session.execute(select(func.count(User.id)))
    active_users = await session.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total_likes = await session.execute(select(func.count(Like.id)))
    total_events = await session.execute(select(func.count(Event.id)))
    pending_complaints = await session.execute(
        select(func.count(Complaint.id)).where(Complaint.is_resolved == False)
    )
    
    text = f"""📊 Статистика бота

👥 Всего пользователей: {total_users.scalar()}
✅ Активных: {active_users.scalar()}
❤️ Всего лайков: {total_likes.scalar()}
🎉 Событий: {total_events.scalar()}
🚫 Жалоб на модерации: {pending_complaints.scalar()}"""
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Рассылка"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    await callback.message.answer(
        "📢 Создание рассылки\n\n"
        "Отправьте текст сообщения или фото/видео с подписью:"
    )
    await state.set_state(AdminBroadcast.message)
    await callback.answer()


@router.message(AdminBroadcast.message)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка сообщения для рассылки"""
    broadcast_text = None
    photo = None
    video = None
    
    if message.text:
        broadcast_text = message.text
    elif message.caption:
        broadcast_text = message.caption
        if message.photo:
            photo = message.photo[-1].file_id
        elif message.video:
            video = message.video.file_id
    
    await state.update_data(
        text=broadcast_text,
        photo=photo,
        video=video
    )
    
    await message.answer(
        "Добавить кнопки? (формат: Текст кнопки | URL)\n"
        "Каждая кнопка с новой строки\n"
        "Или /skip для пропуска"
    )
    await state.set_state(AdminBroadcast.buttons)


@router.message(AdminBroadcast.buttons)
async def process_broadcast_buttons(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка кнопок для рассылки"""
    buttons = []
    if message.text != "/skip":
        lines = message.text.strip().split("\n")
        for line in lines:
            if "|" in line:
                text, url = line.split("|", 1)
                buttons.append({"text": text.strip(), "url": url.strip()})
    
    data = await state.get_data()
    
    # Сохраняем рассылку
    admin_msg = AdminMessage(
        admin_id=message.from_user.id,
        message_text=data.get("text"),
        photo=data.get("photo"),
        video=data.get("video"),
        buttons=buttons if buttons else None
    )
    session.add(admin_msg)
    await session.commit()
    
    # Показываем превью
    preview_text = "📢 Превью рассылки:\n\n"
    if data.get("text"):
        preview_text += data.get("text") + "\n\n"
    if buttons:
        preview_text += "Кнопки:\n"
        for btn in buttons:
            preview_text += f"• {btn['text']}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data=f"broadcast_send_{admin_msg.id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_broadcast")]
    ])
    
    if data.get("photo"):
        await message.answer_photo(data.get("photo"), caption=preview_text, reply_markup=keyboard)
    elif data.get("video"):
        await message.answer_video(data.get("video"), caption=preview_text, reply_markup=keyboard)
    else:
        await message.answer(preview_text, reply_markup=keyboard)
    
    await state.clear()


@router.callback_query(F.data.startswith("broadcast_send_"))
async def callback_broadcast_send(callback: CallbackQuery, session: AsyncSession):
    """Отправка рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    admin_msg_id = int(callback.data.split("_")[2])
    result = await session.execute(select(AdminMessage).where(AdminMessage.id == admin_msg_id))
    admin_msg = result.scalar_one_or_none()
    
    if not admin_msg:
        await callback.answer("Рассылка не найдена!", show_alert=True)
        return
    
    # Получаем всех активных пользователей
    users_result = await session.execute(
        select(User).where(User.is_active == True, User.is_banned == False)
    )
    users = users_result.scalars().all()
    
    sent_count = 0
    for user in users:
        try:
            # Создаем клавиатуру с кнопками
            keyboard = None
            if admin_msg.buttons:
                inline_buttons = []
                for btn in admin_msg.buttons:
                    inline_buttons.append([InlineKeyboardButton(
                        text=btn["text"],
                        url=btn["url"]
                    )])
                keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
            
            # Отправляем сообщение
            if admin_msg.photo:
                await callback.bot.send_photo(
                    user.telegram_id,
                    admin_msg.photo,
                    caption=admin_msg.message_text,
                    reply_markup=keyboard
                )
            elif admin_msg.video:
                await callback.bot.send_video(
                    user.telegram_id,
                    admin_msg.video,
                    caption=admin_msg.message_text,
                    reply_markup=keyboard
                )
            else:
                await callback.bot.send_message(
                    user.telegram_id,
                    admin_msg.message_text,
                    reply_markup=keyboard
                )
            sent_count += 1
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
    
    admin_msg.sent_count = sent_count
    admin_msg.sent_at = func.now()
    await session.commit()
    
    await callback.answer(f"Рассылка отправлена {sent_count} пользователям!")
    await callback.message.edit_text(f"✅ Рассылка отправлена {sent_count} пользователям!")


@router.callback_query(F.data == "admin_moderation")
async def callback_admin_moderation(callback: CallbackQuery, session: AsyncSession):
    """Модерация"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    # Получаем нерешенные жалобы
    complaints_result = await session.execute(
        select(Complaint).where(Complaint.is_resolved == False).limit(10)
    )
    complaints = complaints_result.scalars().all()
    
    if not complaints:
        await callback.message.edit_text("Нет жалоб на модерации", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    text = "🛡️ Жалобы на модерации:\n\n"
    keyboard_buttons = []
    
    for complaint in complaints[:5]:  # Показываем первые 5
        reported_user = await session.get(User, complaint.reported_user_id)
        text += f"ID: {complaint.id}\n"
        text += f"Пользователь: {reported_user.name if reported_user else 'Не найден'}\n"
        text += f"Причина: {complaint.reason.value}\n\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"Просмотр #{complaint.id}",
                callback_data=f"complaint_view_{complaint.id}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("complaint_view_"))
async def callback_complaint_view(callback: CallbackQuery, session: AsyncSession):
    """Просмотр жалобы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    complaint_id = int(callback.data.split("_")[2])
    complaint = await session.get(Complaint, complaint_id)
    
    if not complaint:
        await callback.answer("Жалоба не найдена!", show_alert=True)
        return
    
    reported_user = await session.get(User, complaint.reported_user_id)
    
    text = f"🛡️ Жалоба #{complaint.id}\n\n"
    text += f"На пользователя: {reported_user.name if reported_user else 'Не найден'}\n"
    text += f"Причина: {complaint.reason.value}\n"
    if complaint.description:
        text += f"Описание: {complaint.description}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"complaint_ban_{complaint.id}")],
        [InlineKeyboardButton(text="✅ Отклонить", callback_data=f"complaint_reject_{complaint.id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_moderation")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("complaint_ban_"))
async def callback_complaint_ban(callback: CallbackQuery, session: AsyncSession):
    """Бан пользователя по жалобе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    complaint_id = int(callback.data.split("_")[2])
    complaint = await session.get(Complaint, complaint_id)
    
    if not complaint:
        await callback.answer("Жалоба не найдена!", show_alert=True)
        return
    
    reported_user = await session.get(User, complaint.reported_user_id)
    if reported_user:
        reported_user.is_banned = True
        reported_user.ban_reason = f"Жалоба #{complaint.id}: {complaint.reason.value}"
        complaint.is_resolved = True
        await session.commit()
        
        try:
            await callback.bot.send_message(
                reported_user.telegram_id,
                f"Ваша анкета была заблокирована по причине: {complaint.reason.value}"
            )
        except:
            pass
    
    await callback.answer("Пользователь забанен!")
    await callback.message.edit_text("✅ Пользователь забанен", reply_markup=get_back_keyboard())


@router.callback_query(F.data.startswith("complaint_reject_"))
async def callback_complaint_reject(callback: CallbackQuery, session: AsyncSession):
    """Отклонение жалобы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    complaint_id = int(callback.data.split("_")[2])
    complaint = await session.get(Complaint, complaint_id)
    
    if not complaint:
        await callback.answer("Жалоба не найдена!", show_alert=True)
        return
    
    complaint.is_resolved = True
    await session.commit()
    
    await callback.answer("Жалоба отклонена!")
    await callback.message.edit_text("✅ Жалоба отклонена", reply_markup=get_back_keyboard())


@router.callback_query(F.data.startswith("support_reply_"))
async def callback_support_reply(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Ответ администратора в поддержку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    chat_id = int(callback.data.split("_")[2])
    from database.models import SupportChat
    chat = await session.get(SupportChat, chat_id)
    
    if not chat:
        await callback.answer("Чат поддержки не найден!", show_alert=True)
        return
    
    await state.update_data(support_chat_id=chat_id)
    await state.set_state(AdminSupportReply.waiting_reply)
    
    await callback.message.answer(
        f"💬 Ответ на сообщение в поддержку (чат #{chat_id})\n\n"
        "Напишите ответ пользователю. Для отмены отправьте /cancel",
        reply_markup=None
    )
    await callback.answer()


@router.message(AdminSupportReply.waiting_reply)
async def process_admin_support_reply(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ответа администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещен!")
        await state.clear()
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Ответ отменен")
        return
    
    data = await state.get_data()
    chat_id = data.get("support_chat_id")
    
    if not chat_id:
        await message.answer("Ошибка! Начните заново.")
        await state.clear()
        return
    
    from database.models import SupportChat, SupportMessage
    chat = await session.get(SupportChat, chat_id)
    
    if not chat:
        await message.answer("Чат поддержки не найден!")
        await state.clear()
        return
    
    # Получаем пользователя
    user = await session.get(User, chat.user_id)
    if not user:
        await message.answer("Пользователь не найден!")
        await state.clear()
        return
    
    # Сохраняем сообщение администратора
    support_message = SupportMessage(
        chat_id=chat.id,
        from_user_id=message.from_user.id,
        is_from_admin=True,
        message_text=message.text if message.text else None,
        photo=message.photo[-1].file_id if message.photo else None,
        video=message.video.file_id if message.video else None
    )
    session.add(support_message)
    
    # Обновляем чат
    chat.admin_id = message.from_user.id
    await session.commit()
    
    # Отправляем ответ пользователю
    admin_name = message.from_user.first_name or "Администратор"
    reply_text = f"💬 Ответ от {admin_name}:\n\n"
    
    try:
        if message.photo:
            await message.bot.send_photo(
                user.telegram_id,
                message.photo[-1].file_id,
                caption=reply_text + (message.caption or "")
            )
        elif message.video:
            await message.bot.send_video(
                user.telegram_id,
                message.video.file_id,
                caption=reply_text + (message.caption or "")
            )
        else:
            await message.bot.send_message(
                user.telegram_id,
                reply_text + (message.text or "")
            )
        
        await message.answer("✅ Ответ отправлен пользователю!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки ответа: {e}")
    
    await state.clear()


@router.callback_query(F.data == "admin_back")
async def callback_admin_back(callback: CallbackQuery, session: AsyncSession):
    """Назад в админ-панель"""
    # Создаем фиктивный message объект из callback
    class FakeMessage:
        def __init__(self, callback):
            self.from_user = callback.from_user
            self.answer = callback.message.answer
            self.text = None
    
    fake_message = FakeMessage(callback)
    await cmd_admin(fake_message, session)

