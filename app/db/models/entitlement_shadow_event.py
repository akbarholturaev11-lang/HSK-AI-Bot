from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntitlementShadowEvent(Base):
    """Eski qaror bilan yangi dvigatel qarorining yonma-yon yozuvi.

    Ko'chirish "umid qilaman to'g'ridir" bilan emas, o'lchov bilan boradi:
    dvigatel avval hech narsani o'zgartirmasdan ishlaydi va har bir qaror
    eski yo'l bilan solishtiriladi.

    Unique kalitda `agree` bor — ya'ni bir kunda bir foydalanuvchi × harakat ×
    klient uchun ko'pi bilan BITTA "mos keldi" va BITTA "mos kelmadi" qatori
    yoziladi. Shunday qilib jadval hajmi cheklanadi, lekin ikkala son ham
    saqlanadi: nomuvofiqliklar ro'yxati ham, halol namuna soni ham.
    """

    __tablename__ = "entitlement_shadow_events"
    __table_args__ = (
        UniqueConstraint(
            "telegram_id",
            "action",
            "client",
            "day_key",
            "agree",
            name="uq_entitlement_shadow_events_daily",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    client: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    agree: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)

    legacy_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    legacy_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    legacy_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    legacy_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    engine_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    engine_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    engine_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    engine_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    state: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    detail_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    day_key: Mapped[str] = mapped_column(String(16), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
