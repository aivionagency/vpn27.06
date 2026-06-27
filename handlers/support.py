import re
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config
import texts
import keyboards

logger = logging.getLogger(__name__)
router = Router()

# In-memory map: message_id posted in the support group -> user's telegram_id.
# Lets an admin reply to either the header or the copied message. Survives only
# within a running process; the #id tag in the header text is the restart-safe
# fallback (see _resolve_target).
RELAY_MAP: dict[int, int] = {}

_ID_RE = re.compile(r"#id(\d+)")


class SupportStates(StatesGroup):
    waiting_for_message = State()


@router.callback_query(keyboards.ActionCallbackData.filter(F.action == "support"))
async def start_support(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(texts.SUPPORT_TEXT, reply_markup=keyboards.support_keyboard())
    await state.set_state(SupportStates.waiting_for_message)


@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    """User -> support group. Posts a header (the reply anchor) + the content."""
    if config.support_chat_id:
        try:
            u = message.from_user
            uname = f"@{u.username}" if u.username else "без username"
            header = (
                f"💬 <b>Новое обращение в поддержку</b>\n"
                f"От: {u.full_name} ({uname})\n"
                f"ID: <code>{u.id}</code>  #id{u.id}\n\n"
                f"↩️ <i>Ответьте на это сообщение, чтобы написать пользователю.</i>"
            )
            anchor = await message.bot.send_message(
                config.support_chat_id, header, parse_mode="HTML"
            )
            copied = await message.copy_to(config.support_chat_id)
            # Both the header and the copied content map back to this user.
            RELAY_MAP[anchor.message_id] = u.id
            RELAY_MAP[copied.message_id] = u.id
            await message.answer(texts.SUPPORT_SENT)
        except Exception:
            logger.exception("Failed to relay support message to group")
            await message.answer(texts.SUPPORT_ERROR)
    else:
        await message.answer(texts.SUPPORT_STUB)

    await state.clear()


def _resolve_target(replied: Message) -> int | None:
    """Find the user a support reply is meant for."""
    target = RELAY_MAP.get(replied.message_id)
    if target:
        return target
    # restart-safe fallback: read the #id tag out of the header text
    text = replied.text or replied.caption or ""
    m = _ID_RE.search(text)
    return int(m.group(1)) if m else None


@router.message(F.reply_to_message)
async def support_reply(message: Message):
    """Support group -> user. Admin replies to a relayed message; we forward it back."""
    if not config.support_chat_id or message.chat.id != config.support_chat_id:
        return

    target_id = _resolve_target(message.reply_to_message)
    if not target_id:
        return  # reply wasn't to a tracked support message — ignore

    try:
        await message.bot.send_message(target_id, "💬 <b>Ответ поддержки:</b>", parse_mode="HTML")
        await message.copy_to(target_id)
        await message.reply("✅ Отправлено пользователю.")
    except Exception:
        logger.exception("Failed to deliver support reply to user %s", target_id)
        await message.reply("⚠️ Не удалось отправить (пользователь мог заблокировать бота).")
