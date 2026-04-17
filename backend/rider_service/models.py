"""
Dev 1: Rider Service ORM Models

These are the SQLAlchemy ORM models for riders, risk profiles, zones, and baselines.
All other devs READ from these tables — only Dev 1 WRITES to them.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, DECIMAL, UniqueConstraint, JSON, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from shared.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    flood_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    traffic_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    store_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    composite_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    lat: Mapped[float | None] = mapped_column(DECIMAL(10, 8), nullable=True)
    lon: Mapped[float | None] = mapped_column(DECIMAL(11, 8), nullable=True)

    # Relationships
    riders = relationship("Rider", back_populates="zone")


class Rider(Base):
    __tablename__ = "riders"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    upi_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kyc_status: Mapped[str] = mapped_column(String(20), default="pending")
    trust_score: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # Relationships
    zone = relationship("Zone", back_populates="riders")
    risk_profile = relationship("RiderRiskProfile", back_populates="rider", uselist=False)
    policies = relationship("Policy", back_populates="rider")


class RiderRiskProfile(Base):
    __tablename__ = "rider_risk_profiles"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), unique=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    income_volatility: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0)
    disruption_probability: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0)
    four_week_earnings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    rider = relationship("Rider", back_populates="risk_profile")


class RiderZoneBaseline(Base):
    __tablename__ = "rider_zone_baselines"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    week: Mapped[str] = mapped_column(String(10), nullable=False)
    slot_time: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_earnings: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    disruption_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("rider_id", "zone_id", "week", "slot_time"),
    )
