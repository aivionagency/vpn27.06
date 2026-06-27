import json
import logging
from datetime import datetime, timezone

from aiohttp import web
from sqlalchemy.exc import IntegrityError

from config import config
from models import PaymentEvent
from repositories.users import UserRepository
from services.payments import PaymentsService
from services.billing import BillingService

logger = logging.getLogger(__name__)

# aiohttp app keys
SESSION_POOL_KEY = "session_pool"
BOT_KEY = "bot"


async def handle_tribute_webhook(request: web.Request) -> web.Response:
    payments = PaymentsService()

    # 1. raw body FIRST (signature is computed over the exact bytes)
    raw_body = await request.read()
    signature = request.headers.get("trbt-signature")

    # 2. verify signature
    if not payments.verify_signature(raw_body, signature):
        logger.warning("Tribute webhook: invalid signature")
        return web.json_response({"ok": False, "error": "bad signature"}, status=401)

    # 3. parse JSON
    try:
        envelope = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("Tribute webhook: invalid JSON")
        return web.json_response({"ok": False, "error": "bad json"}, status=400)

    event_name = envelope.get("name")

    # 4. only donations are top-ups; ack-and-ignore everything else
    if not payments.is_donation_event(event_name):
        logger.info("Tribute webhook: ignoring event '%s'", event_name)
        return web.json_response({"ok": True, "ignored": True})

    data = payments.parse_donation(envelope)
    amount_kopecks = data["amount_kopecks"] or 0
    # Tribute may send the currency in any case (e.g. "rub"); normalise it so the
    # validation below doesn't reject a valid RUB donation as "unsupported".
    currency = (data["currency"] or "").upper()
    telegram_user_id = data["telegram_user_id"]
    created_at = data["created_at"]

    idem_key = payments.build_idempotency_key(telegram_user_id, amount_kopecks, created_at)
    raw_text = raw_body.decode("utf-8", errors="replace")
    now = datetime.now(timezone.utc)

    session_pool = request.app[SESSION_POOL_KEY]
    bot = request.app[BOT_KEY]

    notify = None  # (telegram_id, text) to send after commit

    async with session_pool() as session:
        event = PaymentEvent(
            provider="tribute",
            idempotency_key=idem_key,
            event_name=event_name,
            telegram_user_id=telegram_user_id,
            amount_kopecks=amount_kopecks,
            currency=currency,
            status="received",
            raw_payload=raw_text,
        )
        session.add(event)
        try:
            await session.flush()
        except IntegrityError:
            # duplicate delivery — already processed
            await session.rollback()
            logger.info("Tribute webhook: duplicate event ignored (key=%s)", idem_key)
            return web.json_response({"ok": True, "duplicate": True})

        # 5. reject anonymous / unattributable donations (we keep a record, don't credit)
        if data["anonymously"] or not telegram_user_id:
            event.status = "quarantine"
            event.processed_at = now
            await session.commit()
            await _alert_admins(bot, f"⚠️ Анонимный/непривязанный донат Tribute на {amount_kopecks/100:.2f} {currency}. Зачисление пропущено.")
            return web.json_response({"ok": True, "quarantined": True})

        # 6. validate currency
        if currency != "RUB":
            event.status = "ignored"
            event.processed_at = now
            await session.commit()
            logger.warning("Tribute webhook: unsupported currency %s", currency)
            return web.json_response({"ok": True, "ignored": True})

        rubles = amount_kopecks // 100

        # 7. sanity limits
        if rubles < config.topup_min_rub or rubles > config.topup_max_rub:
            event.status = "ignored"
            event.processed_at = now
            await session.commit()
            await _alert_admins(bot, f"⚠️ Донат на {rubles} ₽ вне лимитов, пропущен. tg_id={telegram_user_id}")
            return web.json_response({"ok": True, "ignored": True})

        # 8. find the user
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_user_id)
        if not user:
            event.status = "quarantine"
            event.processed_at = now
            await session.commit()
            await _alert_admins(bot, f"⚠️ Донат на {rubles} ₽ от tg_id={telegram_user_id}, но пользователя нет в базе. В карантине.")
            return web.json_response({"ok": True, "quarantined": True})

        # 9. credit balance + record transaction (atomic)
        billing = BillingService(session)
        await billing.credit_topup(user, rubles, comment=f"Tribute top-up {rubles} ₽")
        event.user_id = user.id
        event.status = "credited"
        event.processed_at = now
        await session.commit()

        notify = (user.telegram_id, f"✅ Баланс пополнен на {rubles} ₽.\nТекущий баланс: {user.balance} ₽")

    # 10. fast 200 already guaranteed; notify the user after commit
    if notify:
        try:
            await bot.send_message(chat_id=notify[0], text=notify[1])
        except Exception:
            logger.exception("Failed to notify user about top-up")

    return web.json_response({"ok": True, "credited": True})


async def _alert_admins(bot, text: str) -> None:
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            logger.exception("Failed to alert admin %s", admin_id)


def create_webhook_app(session_pool, bot) -> web.Application:
    from web.dashboard import setup_dashboard, SESSION_POOL_KEY as DASH_POOL_KEY

    app = web.Application()
    app[SESSION_POOL_KEY] = session_pool
    app[DASH_POOL_KEY] = session_pool
    app[BOT_KEY] = bot
    app.router.add_post(config.webhook_path, handle_tribute_webhook)
    # simple health check
    app.router.add_get("/health", lambda r: web.json_response({"ok": True}))
    # owner dashboard (DB, payments, logs) on the same host/port
    setup_dashboard(app)
    return app
