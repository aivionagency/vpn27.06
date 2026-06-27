import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from models import SupportMessage
from repositories.users import UserRepository
from config import config
import texts
import keyboards

logger = logging.getLogger(__name__)
router = Router()

class SupportStates(StatesGroup):
    waiting_for_message = State()


@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "support"))
async def start_support(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(texts.SUPPORT_TEXT, reply_markup=keyboards.support_keyboard())
    await state.set_state(SupportStates.waiting_for_message)


@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, session: AsyncSession):
    """User -> Web Dashboard. Saves message to DB."""
    try:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer(texts.SUPPORT_ERROR)
            return

        text = message.text or message.caption or "(Вложение)"

        support_msg = SupportMessage(
            user_id=user.id,
            is_from_user=True,
            text=text
        )
        session.add(support_msg)
        await session.commit()

        await message.answer(texts.SUPPORT_SENT)
    except Exception:
        logger.exception("Failed to save support message")
        await message.answer(texts.SUPPORT_ERROR)

    await state.clear()
