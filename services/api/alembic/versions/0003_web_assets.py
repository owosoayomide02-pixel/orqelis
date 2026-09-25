"""Web assets, scan jobs, polymorphic events.

Revision ID: 0003_web_assets
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_web_assets"
down_revision = "0002_demo_workspaces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("verification_method", sa.String(32), nullable=False, server_default="dns_txt"),
        sa.Column("verification_token", sa.String(64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_verify_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "domain", name="uq_org_domain"),
    )
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("web_asset_id", sa.String(36), sa.ForeignKey("web_assets.id"), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="hunter"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("tools_run", sa.JSON(), nullable=True),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("current_tool", sa.String(64), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requested_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    with op.batch_alter_table("events") as batch:
        batch.alter_column("device_id", existing_type=sa.String(36), nullable=True)
        batch.add_column(sa.Column("source", sa.String(32), nullable=False, server_default="device"))
        batch.add_column(sa.Column("source_id", sa.String(36), nullable=True))

    # Backfill polymorphic source fields for existing device events
    op.execute("UPDATE events SET source = 'device', source_id = device_id WHERE source_id IS NULL")
    op.create_index("ix_events_source", "events", ["source"])
    op.create_index("ix_events_source_id", "events", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_events_source_id", table_name="events")
    op.drop_index("ix_events_source", table_name="events")
    with op.batch_alter_table("events") as batch:
        batch.drop_column("source_id")
        batch.drop_column("source")
        batch.alter_column("device_id", existing_type=sa.String(36), nullable=False)
    op.drop_table("scan_jobs")
    op.drop_table("web_assets")
