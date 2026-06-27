from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Referral

class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_referral(
        self,
        referrer_id: int,
        referred_id: int
    ) -> Referral:
        referral = Referral(
            referrer_id=referrer_id,
            referred_id=referred_id
        )
        self.session.add(referral)
        await self.session.flush()
        return referral

    async def get_by_referred_id(self, referred_id: int) -> Optional[Referral]:
        stmt = select(Referral).where(Referral.referred_id == referred_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_purchased_referrals_count(self, referrer_id: int) -> int:
        stmt = select(Referral).where(
            Referral.referrer_id == referrer_id,
            Referral.reward_paid == True
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
