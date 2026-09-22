"""Initial Orqelis V1 schema.

Revision ID: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are created by SQLAlchemy metadata in development (AUTO_MIGRATE).
    # This revision documents the V1 domain model.
    pass


def downgrade() -> None:
    pass
