"""
Dev 4: Claims + Payouts ORM Models
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    disruption_event_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("disruption_events.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # auto, manual
    disruption_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    income_loss: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_earnings: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_earnings: Mapped[int] = mapped_column(Integer, nullable=False)
    payout_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fraud_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, under_review, approved, paid, rejected, flagged
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(20), default="upi")
    upi_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
