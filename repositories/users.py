from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        referred_by: Optional[int] = None,
        referral_code: str = ""
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            referred_by=referred_by,
            referral_code=referral_code
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_user_count_by_referral(self, user_id: int) -> int:
        stmt = select(User).where(User.referred_by == user_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get_by_referral_code(self, code: str) -> Optional[User]:
        stmt = select(User).where(User.referral_code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
