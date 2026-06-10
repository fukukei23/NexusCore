"""add openrouter_key_enc to users"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("openrouter_key_enc", sa.String(512), nullable=True))


def downgrade():
    op.drop_column("users", "openrouter_key_enc")
