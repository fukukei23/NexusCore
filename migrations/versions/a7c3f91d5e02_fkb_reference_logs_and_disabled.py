"""fkb reference logs and knowledge_entries.disabled

Revision ID: a7c3f91d5e02
Revises: 9d8346475f27
Create Date: 2026-08-17 10:45:00.000000

nexuscore-bench Phase 0:
- knowledge_reference_logs 新設（FKB参照ログ=bench主指標の前提）
- knowledge_entries.disabled 追加（論理削除・汚染スパイラル対策）
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a7c3f91d5e02'
down_revision = '9d8346475f27'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('knowledge_reference_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('knowledge_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.String(), nullable=False),
    sa.Column('step', sa.String(), nullable=True),
    sa.Column('outcome', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('knowledge_reference_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_knowledge_reference_logs_knowledge_id'), ['knowledge_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_knowledge_reference_logs_task_id'), ['task_id'], unique=False)

    with op.batch_alter_table('knowledge_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade():
    with op.batch_alter_table('knowledge_entries', schema=None) as batch_op:
        batch_op.drop_column('disabled')

    with op.batch_alter_table('knowledge_reference_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_knowledge_reference_logs_task_id'))
        batch_op.drop_index(batch_op.f('ix_knowledge_reference_logs_knowledge_id'))

    op.drop_table('knowledge_reference_logs')
