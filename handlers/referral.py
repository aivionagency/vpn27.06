from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.users import UserRepository
from repositories.referrals import ReferralRepository
from repositories.transactions import TransactionRepository
from config import config
import texts
import keyboards

router = Router()

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "referral"))
async def show_referral(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    
    user_repo = UserRepository(session)
    ref_repo = ReferralRepository(session)
    tx_repo = TransactionRepository(session)
    
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return
        
    invited_count = await user_repo.get_user_count_by_referral(user.id)
    purchased_count = await ref_repo.get_purchased_referrals_count(user.id)
    earned_total = await tx_repo.get_total_earned_from_referrals(user.id)
    
    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref{user.telegram_id}"
    
    text = texts.REFERRAL_MENU.format(
        referral_reward=config.referral_reward,
        referral_bonus=config.referral_bonus,
        invited_count=invited_count,
        purchased_count=purchased_count,
        earned_total=earned_total,
        referral_link=referral_link
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.referral_keyboard(referral_link),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "referral_terms"))
async def show_referral_terms(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Заглушка: условия реферальной программы.", reply_markup=keyboards.support_keyboard())