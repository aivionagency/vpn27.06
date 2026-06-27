from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class TZDateTime(TypeDecorator):
    """DateTime that always returns timezone-aware UTC values.

    SQLite does not persist timezone info, so naive datetimes come back from the
    DB. This stores everything as naive UTC and re-attaches UTC tzinfo on read,
    so application code can always assume aware UTC datetimes.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
    devices: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    vpn_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) # telegram_id of the referrer
    referral_code: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user")
    
    # We could model referrals relationship if we want, but sticking to simple is better right now
    
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String) # topup, purchase, referral_bonus, referral_reward, trial
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="transactions")

class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    referred_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reward_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())


class PaymentEvent(Base):
    """Journal of incoming Tribute payment webhooks (audit + idempotency)."""
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, default="tribute")
    # synthetic dedup key: hash(telegram_user_id + amount + created_at) — Tribute donations have no unique payment id
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    event_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    amount_kopecks: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # received | credited | quarantine | ignored | error
    status: Mapped[str] = mapped_column(String, default="received")
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime, nullable=True)
