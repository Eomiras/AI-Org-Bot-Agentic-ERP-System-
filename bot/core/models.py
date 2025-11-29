from sqlalchemy import BigInteger, String, Boolean, DateTime, func
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
