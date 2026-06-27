from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from repositories.users import UserRepository
from repositories.transactions import TransactionRepository
import texts
import keyboards

router = Router()

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "my_subscription"))
async def show_subscription(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    user_repo = UserRepository(session)
    tx_repo = TransactionRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    
    if not user:
        return
        
    now = datetime.now(timezone.utc)
    
    devices = texts.devices_phrase(user.devices)

    if user.subscription_expires_at and user.subscription_expires_at > now:
        has_purchase = await tx_repo.has_purchase_transaction(user.id)
        if user.trial_used and not has_purchase:
            days_left = (user.subscription_expires_at - now).days
            text = texts.SUBSCRIPTION_TRIAL.format(
                days_left=days_left,
                balance=user.balance,
                devices=devices,
                vpn_key=user.vpn_key
            )
        else:
            expires_at_str = user.subscription_expires_at.strftime("%d.%m.%Y, %H:%M")
            text = texts.SUBSCRIPTION_ACTIVE.format(
                expires_at=expires_at_str,
                tariff_name="Стандартный тариф",
                balance=user.balance,
                devices=devices,
                vpn_key=user.vpn_key
            )
    else:
        text = texts.SUBSCRIPTION_EXPIRED.format(
            balance=user.balance,
            devices=devices,
            vpn_key=user.vpn_key
        )

    await callback.message.edit_text(text, reply_markup=keyboards.subscription_keyboard(), parse_mode="HTML")
