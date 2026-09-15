"""add provider and model metadata to messages

Revision ID: 9b7e9a5c2d01
Revises: 6ade3ce896dd
"""

from alembic import op
import sqlalchemy as sa

revision = "9b7e9a5c2d01"
down_revision = "6ade3ce896dd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("provider", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "model")
    op.drop_column("messages", "provider")
