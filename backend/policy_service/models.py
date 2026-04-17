"""
Dev 2: Policy ORM Models
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, ARRAY, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from shared.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    week: Mapped[str] = mapped_column(String(10), nullable=False)
    premium: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    slots_covered: Mapped[list | None] = mapped_column(JSON().with_variant(ARRAY(String), "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("rider_id", "week"),
    )

    # Relationships
    rider = relationship("Rider", back_populates="policies")


class MicroSlot(Base):
    __tablename__ = "micro_slots"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    time_start: Mapped[str] = mapped_column(String(10), nullable=False)
    time_end: Mapped[str] = mapped_column(String(10), nullable=False)
    expected_earnings: Mapped[int] = mapped_column(Integer, nullable=False)
    disruption_probability: Mapped[float] = mapped_column(nullable=False)
    weather_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    store_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)


def get_current_iso_week() -> str:
    return datetime.now(timezone.utc).strftime("%Y-W%V")


def get_week_expiry() -> datetime:
    now = datetime.now(timezone.utc)
    days_until_sunday = (6 - now.weekday()) % 7
    expiry = now + timedelta(days=days_until_sunday)
    # Return as naive datetime to match created_at field (TIMESTAMP WITHOUT TIME ZONE)
    return expiry.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)
