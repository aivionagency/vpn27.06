from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Transaction

class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_transaction(
        self,
        user_id: int,
        amount: int,
        type: str,
        comment: Optional[str] = None
    ) -> Transaction:
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=type,
            comment=comment
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_user_transactions(self, user_id: int) -> List[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_purchase_transaction(self, user_id: int) -> bool:
        stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.type == "purchase"
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_total_earned_from_referrals(self, user_id: int) -> int:
        stmt = select(Transaction.amount).where(
            Transaction.user_id == user_id,
            Transaction.type == "referral_reward"
        )
        result = await self.session.execute(stmt)
        return sum(result.scalars().all())
