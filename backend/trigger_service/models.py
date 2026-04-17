"""
Dev 3: Trigger Service ORM Models
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class DisruptionEvent(Base):
    __tablename__ = "disruption_events"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    zone_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slot_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    slot_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)   # low / medium / high / critical
    data_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    affected_riders: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherData(Base):
    __tablename__ = "weather_data"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    zone_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(DECIMAL(6, 2), nullable=True)
    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    humidity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    heat_index: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="openweathermap")


class PlatformSnapshot(Base):
    __tablename__ = "platform_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    
    # Order signals
    orders_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earnings_current_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earnings_rolling_baseline: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earnings_per_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surge_multiplier: Mapped[float | None] = mapped_column(DECIMAL(3, 2), nullable=True)
    order_rate_drop_pct: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    
    # Status flags
    rider_status: Mapped[str | None] = mapped_column(String(20), nullable=True)    # ONLINE / OFFLINE
    store_status: Mapped[str | None] = mapped_column(String(20), nullable=True)    # OPEN / CLOSED / DEGRADED
    stock_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    platform_status: Mapped[str | None] = mapped_column(String(20), nullable=True) # UP / DEGRADED / DOWN
    
    # Anomaly flags
    shadowban_active: Mapped[bool] = mapped_column(default=False)
    shadowban_duration_min: Mapped[int] = mapped_column(default=0)
    allocation_anomaly: Mapped[bool] = mapped_column(default=False)
    curfew_active: Mapped[bool] = mapped_column(default=False)
    grap_vehicle_ban: Mapped[bool] = mapped_column(default=False)
    
    # Traffic
    congestion_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    road_blocked: Mapped[bool] = mapped_column(default=False)
    
    # Store detail
    pickup_queue_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_pickup_wait_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_latency_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
