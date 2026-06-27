from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import texts
import keyboards

router = Router()

@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "main_menu"))
async def show_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    await callback.answer()
    username = callback.from_user.first_name or callback.from_user.username or "пользователь"
    # It might be an edit if it comes from a callback, or a new message
    await callback.message.edit_text(
        texts.MAIN_MENU.format(username=username),
        reply_markup=keyboards.main_menu_keyboard()
    )
