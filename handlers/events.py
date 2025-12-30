from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import User, Event, EventParticipant
from keyboards.common import get_events_menu_keyboard, get_event_keyboard
from datetime import datetime
from utils.helpers import format_profile_text

router = Router()


@router.callback_query(F.data == "event_all")
async def callback_event_all(callback: CallbackQuery, session: AsyncSession):
    """Просмотр всех событий"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.city:
        await callback.answer("Сначала заполни анкету и укажи город!", show_alert=True)
        return
    
    # Получаем все события (не только в городе пользователя)
    events_result = await session.execute(
        select(Event).where(
            Event.event_date >= datetime.utcnow()
        ).order_by(Event.event_date)
    )
    events = events_result.scalars().all()
    
    if not events:
        await callback.message.edit_text(
            "Пока нет событий.\n\nСоздай первое событие!",
            reply_markup=get_events_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Показываем первое событие
    event = events[0]
    await show_event(callback, event, session, user, events)
    await callback.answer()


@router.callback_query(F.data == "event_my")
async def callback_event_my(callback: CallbackQuery, session: AsyncSession):
    """Мои события"""
    user_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # События, созданные пользователем
    created_events_result = await session.execute(
        select(Event).where(Event.creator_id == user.id).order_by(Event.event_date.desc())
    )
    created_events = created_events_result.scalars().all()
    
    # События, в которых участвует пользователь
    participant_events_result = await session.execute(
        select(Event).join(EventParticipant).where(
            EventParticipant.user_id == user.id
        ).order_by(Event.event_date.desc())
    )
    participant_events = participant_events_result.scalars().all()
    
    text = "📅 Мои события\n\n"
    
    if created_events:
        text += "Созданные мной:\n"
        for event in created_events[:5]:
            text += f"• {event.title} - {event.event_date.strftime('%d.%m.%Y %H:%M')}\n"
        text += "\n"
    
    if participant_events:
        text += "Участвую:\n"
        for event in participant_events[:5]:
            text += f"• {event.title} - {event.event_date.strftime('%d.%m.%Y %H:%M')}\n"
    
    if not created_events and not participant_events:
        text += "У тебя пока нет событий."
    
    await callback.message.edit_text(text, reply_markup=get_events_menu_keyboard())
    await callback.answer()


async def show_event(callback: CallbackQuery, event: Event, session: AsyncSession, user: User, all_events: list):
    """Показывает событие"""
    creator = await session.get(User, event.creator_id)
    
    # Проверяем участие
    participation = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == user.id
        )
    )
    is_participant = participation.scalar_one_or_none() is not None
    is_creator = event.creator_id == user.id
    
    text = f"🎉 {event.title}\n\n"
    if event.description:
        text += f"{event.description}\n\n"
    text += f"📍 Город: {event.city}\n"
    text += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"👤 Создатель: {creator.name if creator else 'Неизвестен'}\n"
    
    # Количество участников
    participants_count = await session.execute(
        select(EventParticipant).where(EventParticipant.event_id == event.id)
    )
    count = len(participants_count.scalars().all())
    text += f"👥 Участников: {count}\n"
    
    keyboard = get_event_keyboard(event.id, is_creator, is_participant)
    
    if event.photo:
        await callback.message.delete()
        await callback.message.answer_photo(event.photo, caption=text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("event_join_"))
async def callback_event_join(callback: CallbackQuery, session: AsyncSession):
    """Участие в событии"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    event = await session.get(Event, event_id)
    if not event:
        await callback.answer("Событие не найдено!", show_alert=True)
        return
    
    # Проверяем, не участвует ли уже
    existing = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        await callback.answer("Вы уже участвуете в этом событии!", show_alert=True)
        return
    
    participant = EventParticipant(event_id=event_id, user_id=user.id)
    session.add(participant)
    await session.commit()
    
    await callback.answer("✅ Вы участвуете в событии!")
    
    # Обновляем отображение
    all_events_result = await session.execute(
        select(Event).where(Event.city == user.city, Event.event_date >= datetime.utcnow())
    )
    all_events = all_events_result.scalars().all()
    await show_event(callback, event, session, user, all_events)


@router.callback_query(F.data.startswith("event_leave_"))
async def callback_event_leave(callback: CallbackQuery, session: AsyncSession):
    """Отмена участия в событии"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    participant_result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user.id
        )
    )
    participant = participant_result.scalar_one_or_none()
    
    if participant:
        await session.delete(participant)
        await session.commit()
        await callback.answer("❌ Участие отменено")
        
        event = await session.get(Event, event_id)
        if event:
            all_events_result = await session.execute(
                select(Event).where(Event.city == user.city, Event.event_date >= datetime.utcnow())
            )
            all_events = all_events_result.scalars().all()
            await show_event(callback, event, session, user, all_events)

