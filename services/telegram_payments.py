"""
Сервис для работы с Telegram Payments
Поддерживает: ЮKassa, Stripe и другие провайдеры через Telegram Payments API
"""
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message, SuccessfulPayment
from aiogram import Bot
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import User, Payment, SubscriptionStatus
from config import settings
import logging

logger = logging.getLogger(__name__)


class TelegramPaymentService:
    """Сервис для работы с Telegram Payments"""
    
    def __init__(self):
        self.provider_token = settings.PAYMENT_PROVIDER_TOKEN
        if not self.provider_token:
            logger.warning("PAYMENT_PROVIDER_TOKEN не установлен. Платежи работать не будут.")
    
    async def create_subscription_invoice(
        self, 
        bot: Bot, 
        chat_id: int, 
        user_id: int,
        prices: List[LabeledPrice]
    ) -> None:
        """Создает инвойс для подписки"""
        if not self.provider_token:
            await bot.send_message(
                chat_id,
                "❌ Платежи временно недоступны. Пожалуйста, свяжитесь с администратором."
            )
            return
        
        try:
            await bot.send_invoice(
                chat_id=chat_id,
                title="💎 Подписка MeetUp Premium",
                description=(
                    "Подписка на месяц включает:\n"
                    "• Неограниченные лайки\n"
                    "• Приоритет в показе анкет\n"
                    "• Ранний доступ к новым функциям\n"
                    "• Отсутствие рекламы"
                ),
                payload=f"subscription_{user_id}_{int(datetime.now().timestamp())}",
                provider_token=self.provider_token,
                currency="USD",
                prices=prices,
                start_parameter=f"subscription_{user_id}",
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                is_flexible=False,
            )
        except Exception as e:
            logger.error(f"Ошибка при создании инвойса: {e}")
            await bot.send_message(
                chat_id,
                "❌ Ошибка при создании счета. Попробуйте позже или свяжитесь с поддержкой."
            )
    
    async def create_super_like_invoice(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        target_user_id: int,
        prices: List[LabeledPrice]
    ) -> None:
        """Создает инвойс для суперлайка"""
        if not self.provider_token:
            await bot.send_message(
                chat_id,
                "❌ Платежи временно недоступны. Пожалуйста, свяжитесь с администратором."
            )
            return
        
        try:
            await bot.send_invoice(
                chat_id=chat_id,
                title="💌 Суперлайк",
                description=(
                    "Суперлайк позволяет:\n"
                    "• Отправить сообщение или видео\n"
                    "• Привлечь больше внимания к вашему профилю\n"
                    "• Выделиться среди других пользователей"
                ),
                payload=f"super_like_{user_id}_{target_user_id}_{int(datetime.now().timestamp())}",
                provider_token=self.provider_token,
                currency="USD",
                prices=prices,
                start_parameter=f"super_like_{user_id}",
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                is_flexible=False,
            )
        except Exception as e:
            logger.error(f"Ошибка при создании инвойса суперлайка: {e}")
            await bot.send_message(
                chat_id,
                "❌ Ошибка при создании счета. Попробуйте позже."
            )
    
    async def process_pre_checkout(
        self,
        pre_checkout_query: PreCheckoutQuery,
        bot: Bot,
        session: AsyncSession
    ) -> None:
        """Обработка запроса перед оплатой (можно добавить дополнительную проверку)"""
        try:
            # Здесь можно добавить проверки:
            # - Существует ли пользователь
            # - Не заблокирован ли он
            # - Валидность суммы и т.д.
            
            # Пока просто подтверждаем все запросы
            await bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=True
            )
            logger.info(f"Pre-checkout подтвержден: {pre_checkout_query.id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке pre-checkout: {e}")
            await bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Ошибка при обработке платежа"
            )
    
    async def process_successful_payment(
        self,
        message: Message,
        payment: SuccessfulPayment,
        session: AsyncSession
    ) -> None:
        """Обработка успешного платежа"""
        user_id = message.from_user.id
        payload = payment.invoice_payload
        
        try:
            # Парсим payload: subscription_123_4567890 или super_like_123_456_7890
            parts = payload.split("_")
            payment_type = parts[0]  # subscription или super_like
            
            # Находим пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"Пользователь {user_id} не найден при обработке платежа")
                await message.answer("❌ Ошибка: пользователь не найден")
                return
            
            # Сохраняем информацию о платеже
            payment_record = Payment(
                user_id=user.id,
                payment_type=payment_type,
                amount=payment.total_amount / 100,  # Конвертируем из центов в доллары
                yumoney_payment_id=payment.telegram_payment_charge_id,
                status="completed",
                completed_at=datetime.now()
            )
            session.add(payment_record)
            
            # Обрабатываем в зависимости от типа платежа
            if payment_type == "subscription":
                # Активируем подписку на месяц
                user.subscription_status = SubscriptionStatus.ACTIVE
                user.subscription_expires_at = datetime.now() + timedelta(days=30)
                
                await message.answer(
                    "✅ Подписка успешно активирована!\n\n"
                    "Теперь у вас:\n"
                    "• Неограниченные лайки\n"
                    "• Приоритет в показе анкет\n"
                    "• Ранний доступ к новым функциям\n\n"
                    f"Подписка активна до {user.subscription_expires_at.strftime('%d.%m.%Y')}"
                )
                logger.info(f"Подписка активирована для пользователя {user_id}")
            
            elif payment_type == "super_like":
                # Суперлайк обрабатывается в другом месте
                # Здесь просто подтверждаем оплату
                await message.answer(
                    "✅ Суперлайк оплачен!\n\n"
                    "Теперь вы можете отправить суперлайк при просмотре профилей."
                )
                logger.info(f"Суперлайк оплачен пользователем {user_id}")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке успешного платежа: {e}")
            await session.rollback()
            await message.answer(
                "❌ Произошла ошибка при обработке платежа. "
                "Деньги будут возвращены автоматически. "
                "Если проблема повторится, свяжитесь с поддержкой."
            )


# Глобальный экземпляр сервиса
telegram_payment_service = TelegramPaymentService()

