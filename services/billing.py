from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from repositories.users import UserRepository
from repositories.transactions import TransactionRepository
from repositories.referrals import ReferralRepository
from services.vpn_panel import VpnPanelService
from config import config

class BillingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.tx_repo = TransactionRepository(session)
        self.ref_repo = ReferralRepository(session)
        self.vpn_panel = VpnPanelService()

    async def provide_trial(self, user: User) -> bool:
        if user.trial_used:
            return False

        now = datetime.now(timezone.utc)
        user.trial_used = True
        user.subscription_expires_at = now + timedelta(days=config.trial_days)

        if not user.vpn_key:
            user.vpn_key = self.vpn_panel.create_key(user.telegram_id)

        await self.tx_repo.create_transaction(
            user_id=user.id,
            amount=0,
            type="trial",
            comment=f"{config.trial_days} days trial"
        )

        self.vpn_panel.activate(user.telegram_id, config.trial_days)
        await self.session.commit()
        return True

    async def credit_topup(self, user: User, amount_rub: int, comment: str = "Tribute top-up") -> None:
        """Credit a balance top-up and record the transaction.

        Idempotency is enforced upstream by the payment_events unique key, so this
        method just applies the balance change. Caller commits the session.
        """
        user.balance += amount_rub
        await self.tx_repo.create_transaction(
            user_id=user.id,
            amount=amount_rub,
            type="topup",
            comment=comment,
        )

    async def process_purchase(self, user: User, price: int, days: int, devices: int | None = None) -> bool:
        if user.balance < price:
            return False

        user.balance -= price
        if devices is not None:
            user.devices = devices
        now = datetime.now(timezone.utc)

        if user.subscription_expires_at and user.subscription_expires_at > now:
            user.subscription_expires_at += timedelta(days=days)
        else:
            user.subscription_expires_at = now + timedelta(days=days)

        if not user.vpn_key:
            user.vpn_key = self.vpn_panel.create_key(user.telegram_id)

        await self.tx_repo.create_transaction(
            user_id=user.id,
            amount=-price,
            type="purchase",
            comment=f"Purchase {days} days, {user.devices} device(s)"
        )

        self.vpn_panel.activate(user.telegram_id, days)

        # Process referral bonus if any
        notifications = await self._process_referral_bonus(user)

        await self.session.commit()
        return {"success": True, "notifications": notifications}

    async def _process_referral_bonus(self, user: User) -> list:
        notifications = []
        if not user.referred_by:
            return notifications

        referral = await self.ref_repo.get_by_referred_id(user.id)
        if not referral or referral.reward_paid:
            return notifications

        referrer = await self.user_repo.get_by_telegram_id(user.referred_by)
        if referrer:
            # Add reward to referrer
            referrer.balance += config.referral_reward
            await self.tx_repo.create_transaction(
                user_id=referrer.id,
                amount=config.referral_reward,
                type="referral_reward",
                comment=f"Reward for user {user.telegram_id}"
            )

            # Add bonus to referred
            user.balance += config.referral_bonus
            await self.tx_repo.create_transaction(
                user_id=user.id,
                amount=config.referral_bonus,
                type="referral_bonus",
                comment=f"Bonus for being referred"
            )

            referral.reward_paid = True

            notifications.append({
                "telegram_id": referrer.telegram_id,
                "text": f"🎉 По вашей ссылке оформлена подписка! На баланс зачислено {config.referral_reward} ₽"
            })
            notifications.append({
                "telegram_id": user.telegram_id,
                "text": f"🎁 Вам начислен стартовый реферальный бонус +{config.referral_bonus} ₽!"
            })

        return notifications
