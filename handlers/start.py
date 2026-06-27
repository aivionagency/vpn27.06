from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.users import UserRepository
from repositories.referrals import ReferralRepository
from services.billing import BillingService
from config import config
import texts
import keyboards

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession):
    user_repo = UserRepository(session)
    ref_repo = ReferralRepository(session)
    billing_service = BillingService(session)
    
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    is_new = user is None
    
    if is_new:
        referred_by = None
        args = command.args
        if args and args.startswith("ref"):
            try:
                referrer_id = int(args[3:])
                if referrer_id != message.from_user.id:
                    referred_by = referrer_id
            except ValueError:
                pass
                
        user = await user_repo.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            referred_by=referred_by,
            referral_code=str(message.from_user.id)
        )
        
        if referred_by:
            referrer_user = await user_repo.get_by_telegram_id(referred_by)
            if referrer_user:
                await ref_repo.create_referral(referrer_id=referrer_user.id, referred_id=user.id)

    # Provide trial if not used
    await billing_service.provide_trial(user)
    
    # Reload user after providing trial to get the updated key
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if is_new:
        text = texts.START_NEW_USER.format(vpn_key=user.vpn_key)
    else:
        text = texts.START_RETURNING_USER.format(vpn_key=user.vpn_key)
        
    await message.answer(text, reply_markup=keyboards.start_keyboard(), parse_mode="HTML")

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "instruction"))
async def show_instruction(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(texts.INSTRUCTION_STUB, reply_markup=keyboards.support_keyboard())
