
"""Modelos SQLAlchemy para Inbox/Outbox/State/Cart."""
from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, JSON, UniqueConstraint, BigInteger, TIMESTAMP
from datetime import datetime

class Base(DeclarativeBase):
    """Base declarativa."""
    pass

class InboxMessage(Base):
    __tablename__ = "inbox_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64))
    provider_message_id: Mapped[str] = mapped_column(String(64))
    wa_id: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False), default=datetime.utcnow)
    trace_id: Mapped[str] = mapped_column(String(64), default="-")
    __table_args__ = (
        UniqueConstraint("conversation_id", "provider_message_id", name="uq_inbox_idem"),
    )

class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64))
    body: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|sent|dead_letter
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None]
    provider_message_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False), default=datetime.utcnow)
    sent_at: Mapped[datetime | None]

class ConversationState(Base):
    __tablename__ = "conversation_state"
    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_summary: Mapped[str | None]
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

class ConversationEvent(Base):
    __tablename__ = "conversation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSON)
    ts: Mapped[int] = mapped_column(BigInteger)  # epoch ms

class CartItem(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64))
    sku: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    qty: Mapped[int] = mapped_column(Integer)
    unit_price_cents: Mapped[int] = mapped_column(Integer)
