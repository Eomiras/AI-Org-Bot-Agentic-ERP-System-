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

    # Karma Core (Reputation)
    trust_score: Mapped[int] = mapped_column(BigInteger, default=50) # Start neutral
    duty_score: Mapped[int] = mapped_column(BigInteger, default=50)
    skill_score: Mapped[int] = mapped_column(BigInteger, default=50)
    last_activity: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lockout_until: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def effective_reputation(self) -> float:
        # ER = (0.5 * Duty) + (0.4 * Trust) + (0.1 * Skill)
        d = self.duty_score if self.duty_score is not None else 50
        t = self.trust_score if self.trust_score is not None else 50
        s = self.skill_score if self.skill_score is not None else 50
        return (0.5 * d) + (0.4 * t) + (0.1 * s)

    @property
    def risk_score(self) -> float:
        # RS = 100 - ER
        return max(0.0, 100.0 - self.effective_reputation)


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


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"))
    amount: Mapped[int] = mapped_column(BigInteger) # Principle + Interest
    initial_amount: Mapped[int] = mapped_column(BigInteger)
    interest_rate: Mapped[float] = mapped_column(default=0.05) # 5% Late Fee
    due_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="ACTIVE") # ACTIVE, PAID, DEFAULTED
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bounty(Base):
    __tablename__ = "bounties"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issuer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"))
    hunter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), nullable=True)
    target: Mapped[str] = mapped_column(String)
    reward: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String, default="OPEN") # OPEN, CLAIMED, COMPLETED, CANCELLED
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    ceo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"))
    share_price: Mapped[int] = mapped_column(BigInteger, default=100) # Initial Price
    total_shares: Mapped[int] = mapped_column(BigInteger, default=1000)
    bank_account_id: Mapped[int] = mapped_column(BigInteger) # We use a fake User ID for company accounts or link to BankAccount table directly?
    # Ideally BankAccount is keyed by UserID. We can reserve a range for Companies or use a separate ID strategy.
    # We will use negative IDs for companies to avoid collision with Discord IDs (positive).
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Shareholder(Base):
    __tablename__ = "shareholders"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id"), primary_key=True)
    shares_owned: Mapped[int] = mapped_column(BigInteger, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), nullable=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(String, nullable=True)
