"""create_policies_and_micro_slots

Revision ID: 20260401_create_policies_and_micro_slots
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260401_create_policies_and_micro_slots"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_tier", sa.String(length=20), nullable=False),
        sa.Column("week", sa.String(length=10), nullable=False),
        sa.Column("premium", sa.Integer(), nullable=False),
        sa.Column("coverage_limit", sa.Integer(), nullable=False),
        sa.Column("coverage_pct", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("slots_covered", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("coverage_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rider_id"], ["riders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rider_id", "week", name="uq_policies_rider_id_week"),
    )
    op.create_index(op.f("ix_policies_rider_id"), "policies", ["rider_id"], unique=False)

    op.create_table(
        "micro_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("time_start", sa.Time(), nullable=False),
        sa.Column("time_end", sa.Time(), nullable=False),
        sa.Column("expected_earnings", sa.Integer(), nullable=False),
        sa.Column("disruption_probability", sa.Numeric(4, 2), nullable=False),
        sa.Column("weather_risk_score", sa.Integer(), nullable=True),
        sa.Column("traffic_risk_score", sa.Integer(), nullable=True),
        sa.Column("store_risk_score", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_micro_slots_zone_id"), "micro_slots", ["zone_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_micro_slots_zone_id"), table_name="micro_slots")
    op.drop_table("micro_slots")
    op.drop_index(op.f("ix_policies_rider_id"), table_name="policies")
    op.drop_table("policies")
