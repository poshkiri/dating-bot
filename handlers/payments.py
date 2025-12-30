"""
Обработчики платежей через Telegram Payments
"""
from aiogram import Router, F, Bot
from aiogram.types import PreCheckoutQuery, Message, SuccessfulPayment
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from services.telegram_payments import telegram_payment_service
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
    bot: Bot,
    session: AsyncSession
):
    """Обработка запроса перед оплатой"""
    await telegram_payment_service.process_pre_checkout(
        pre_checkout_query=pre_checkout_query,
        bot=bot,
        session=session
    )


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    payment: SuccessfulPayment,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка успешного платежа"""
    await telegram_payment_service.process_successful_payment(
        message=message,
        payment=payment,
        session=session
    )
    
    # Если это был суперлайк, можно перейти к выбору получателя
    payload = payment.invoice_payload
    if payload.startswith("super_like"):
        # Сохраняем информацию о том, что суперлайк оплачен
        await state.update_data(super_like_paid=True)
        # Можно показать инструкции или перейти к выбору профиля

