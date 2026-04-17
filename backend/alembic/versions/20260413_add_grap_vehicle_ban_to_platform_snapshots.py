"""add_grap_vehicle_ban_to_platform_snapshots

Revision ID: 20260413_add_grap_vehicle_ban_to_platform_snapshots
Revises: 20260401_create_policies_and_micro_slots
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_add_grap_vehicle_ban_to_platform_snapshots"
down_revision = "20260401_create_policies_and_micro_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_snapshots",
        sa.Column("grap_vehicle_ban", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("platform_snapshots", "grap_vehicle_ban")
