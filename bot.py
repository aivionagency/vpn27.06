import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import config
from handlers import start, menu, subscription, purchase, referral, support
from web.tribute_webhook import create_webhook_app
from web.dashboard import install_log_capture

logging.basicConfig(level=logging.INFO)
install_log_capture()  # feed logs into the dashboard's live journal

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(self, handler, event: Update, data: dict):
        async with self.session_pool() as session:
            data['session'] = session
            return await handler(event, data)

async def main():
    proxy_url = config.proxy_url or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy_url:
        logging.info("Using proxy for Telegram API: %s", proxy_url)
        session = AiohttpSession(proxy=proxy_url)
    else:
        session = None
    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher(storage=MemoryStorage())
    
    engine = create_async_engine(config.database_url, echo=False)
    session_pool = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    dp.update.middleware(DbSessionMiddleware(session_pool))
    
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(subscription.router)
    dp.include_router(purchase.router)
    dp.include_router(referral.router)
    dp.include_router(support.router)
    
    # Start the Tribute webhook web server alongside long-polling
    webhook_app = create_webhook_app(session_pool, bot)
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, host=config.webhook_host, port=config.webhook_port)
    await site.start()
    logging.info(
        "Tribute webhook server listening on http://%s:%s%s",
        config.webhook_host, config.webhook_port, config.webhook_path,
    )

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")