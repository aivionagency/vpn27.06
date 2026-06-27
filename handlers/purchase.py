from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.users import UserRepository
from repositories.transactions import TransactionRepository
from services.billing import BillingService
from services.payments import PaymentsService
from config import config
import texts
import keyboards

router = Router()

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "buy"))
async def show_devices(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    await callback.message.edit_text(
        texts.CHOOSE_DEVICES,
        reply_markup=keyboards.devices_keyboard(),
        parse_mode="HTML",
    )

@router.callback_query(keyboards.DeviceCallbackData.filter())
async def show_tariffs(callback: CallbackQuery, callback_data: keyboards.DeviceCallbackData, session: AsyncSession):
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    devices = callback_data.count
    text = texts.CHOOSE_TARIFF.format(
        devices=texts.devices_phrase(devices),
        balance=user.balance,
    )
    await callback.message.edit_text(text, reply_markup=keyboards.tariffs_keyboard(devices))

@router.callback_query(keyboards.TariffCallbackData.filter())
async def show_tariff_confirmation(callback: CallbackQuery, callback_data: keyboards.TariffCallbackData, session: AsyncSession):
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    tariff = keyboards.get_tariff_by_id(callback_data.id)
    if not tariff or not user:
        return

    devices = callback_data.devices
    text = texts.TARIFF_CONFIRMATION.format(
        title=tariff["title"],
        devices=texts.devices_phrase(devices),
        days=tariff["days"],
        price=keyboards.tariff_price(tariff, devices),
        balance=user.balance
    )

    await callback.message.edit_text(text, reply_markup=keyboards.tariff_confirmation_keyboard(tariff["id"], devices))

@router.callback_query(keyboards.PayCallbackData.filter())
async def process_payment(callback: CallbackQuery, callback_data: keyboards.PayCallbackData, session: AsyncSession):
    # Basic Anti-double-click is handled by simple fast execution and not much delay, but can be improved with a locking mechanism in a real app
    await callback.answer()

    tariff = keyboards.get_tariff_by_id(callback_data.tariff_id)
    if not tariff:
        return

    devices = callback_data.devices
    price = keyboards.tariff_price(tariff, devices)

    user_repo = UserRepository(session)
    billing_service = BillingService(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    if user.balance >= price:
        result = await billing_service.process_purchase(user, price, tariff["days"], devices=devices)
        if result and result.get("success"):
            expires_at_str = user.subscription_expires_at.strftime("%d.%m.%Y, %H:%M")
            text = texts.SUCCESSFUL_PURCHASE.format(
                price=price,
                balance=user.balance,
                expires_at=expires_at_str
            )
            await callback.message.edit_text(text, reply_markup=keyboards.successful_purchase_keyboard())

            for notif in result.get("notifications", []):
                try:
                    await callback.bot.send_message(
                        chat_id=notif["telegram_id"],
                        text=notif["text"]
                    )
                except Exception:
                    pass # ignore if blocked
    else:
        diff = price - user.balance
        text = texts.INSUFFICIENT_FUNDS.format(
            price=price,
            balance=user.balance,
            diff=diff
        )

        payments_service = PaymentsService()
        topup_url = payments_service.get_topup_link(user.telegram_id)

        await callback.message.edit_text(text, reply_markup=keyboards.insufficient_funds_keyboard(topup_url))

@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message, session: AsyncSession):
    if message.from_user.id not in config.admin_ids:
        return
        
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(texts.ADD_BALANCE_USAGE)
        return
        
    try:
        amount = int(parts[1])
    except ValueError:
        await message.answer(texts.ADD_BALANCE_INVALID)
        return
        
    user_repo = UserRepository(session)
    tx_repo = TransactionRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        return
        
    user.balance += amount
    await tx_repo.create_transaction(
        user_id=user.id,
        amount=amount,
        type="topup",
        comment="Admin manual topup"
    )
    await session.commit()
    
    await message.answer(texts.ADD_BALANCE_SUCCESS.format(amount=amount, balance=user.balance))