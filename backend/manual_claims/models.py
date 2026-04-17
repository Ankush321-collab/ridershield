"""
Dev 5: Manual Claims ORM Model
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, DECIMAL
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class ManualClaim(Base):
    __tablename__ = "manual_claims"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("riders.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)

    disruption_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    photo_exif_lat: Mapped[float | None] = mapped_column(DECIMAL(10, 8), nullable=True)
    photo_exif_lon: Mapped[float | None] = mapped_column(DECIMAL(11, 8), nullable=True)
    telemetry_lat: Mapped[float | None] = mapped_column(DECIMAL(10, 8), nullable=True)
    telemetry_lon: Mapped[float | None] = mapped_column(DECIMAL(11, 8), nullable=True)
    gps_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    spam_score: Mapped[int] = mapped_column(Integer, default=0)
    geo_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    traffic_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
