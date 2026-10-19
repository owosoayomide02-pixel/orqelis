"""Persist website waitlist signups and delivery state."""

from alembic import op
import sqlalchemy as sa

revision = "0005_waitlist_entries"
down_revision = "0004_web_asset_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resend_contact_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_waitlist_entries_email"),
    )

def downgrade() -> None:
    op.drop_table("waitlist_entries")
