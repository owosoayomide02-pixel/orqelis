"""Demo workspace marker.

Revision ID: 0002_demo_workspaces
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_demo_workspaces"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_workspaces",
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False, server_default="LABELED DEMO — not live telemetry"),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("demo_workspaces")
