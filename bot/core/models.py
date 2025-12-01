from sqlalchemy import BigInteger, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from bot.core.database import Base

class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rsi_handle: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_code: Mapped[str] = mapped_column(String, nullable=True) # The random code they need to put in bio

    # Metadata
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Privacy
    pii_blob: Mapped[str] = mapped_column(String, nullable=True) # Encrypted PII data
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)

    # Resilience / AfK
    is_afk: Mapped[bool] = mapped_column(Boolean, default=False)
    afk_reason: Mapped[str] = mapped_column(String, nullable=True)
    afk_until: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    currency_type: Mapped[str] = mapped_column(String, default="NC")
    account_type: Mapped[str] = mapped_column(String, default="USER") # USER, TREASURY, ESCROW
    last_daily_claim: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

class ReputationRank(Base):
    __tablename__ = "reputation_ranks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    min_reputation: Mapped[int] = mapped_column(BigInteger)
    salary: Mapped[int] = mapped_column(BigInteger, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), nullable=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(String, nullable=True)
