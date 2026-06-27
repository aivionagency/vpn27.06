import json
from aiohttp import web
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from models import SupportMessage, User
from web.tribute_webhook import SESSION_POOL_KEY, BOT_KEY

from web.dashboard import _authorized, _deny

async def get_chats(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    session_pool = request.app[SESSION_POOL_KEY]
    async with session_pool() as db:
        stmt = select(User).join(SupportMessage).group_by(User.id).order_by(desc(User.created_at))
        result = await db.execute(stmt)
        users = result.scalars().all()
        data = [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "name": u.username or str(u.telegram_id)} for u in users]
    return web.json_response(data)

async def get_messages(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    user_id = int(request.query.get("user_id", 0))
    session_pool = request.app[SESSION_POOL_KEY]
    async with session_pool() as db:
        stmt = select(SupportMessage).where(SupportMessage.user_id == user_id).order_by(SupportMessage.created_at)
        result = await db.execute(stmt)
        messages = result.scalars().all()
        data = [{"id": m.id, "is_from_user": m.is_from_user, "text": m.text, "created_at": str(m.created_at)} for m in messages]
    return web.json_response(data)

async def reply_message(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    body = await request.json()
    user_id = int(body.get("user_id"))
    text = body.get("text")

    session_pool = request.app[SESSION_POOL_KEY]
    bot = request.app[BOT_KEY]

    async with session_pool() as db:
        user = await db.get(User, user_id)
        if not user:
            return web.json_response({"ok": False, "error": "User not found"}, status=404)

        msg = SupportMessage(user_id=user.id, is_from_user=False, text=text)
        db.add(msg)
        await db.commit()

        try:
            await bot.send_message(user.telegram_id, f"💬 <b>Ответ поддержки:</b>\n{text}", parse_mode="HTML")
            success = True
        except Exception as e:
            success = False
            error = str(e)

    if success:
        return web.json_response({"ok": True})
    else:
        return web.json_response({"ok": False, "error": error}, status=500)
