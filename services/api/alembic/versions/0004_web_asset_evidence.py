"""Store scoped image evidence with integrity metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0004_web_asset_evidence"
down_revision = "0003_web_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_asset_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("web_asset_id", sa.String(36), sa.ForeignKey("web_assets.id"), nullable=False, index=True),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False, server_default="evidence"),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("web_asset_evidence")