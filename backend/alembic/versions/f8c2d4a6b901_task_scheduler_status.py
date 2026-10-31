"""Convert task scheduler enabled flag to integer status."""

import sqlalchemy as sa

from alembic import op

revision = 'f8c2d4a6b901'
down_revision = 'e09c43940664'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('task_scheduler', 'enabled', existing_type=sa.Boolean(), server_default=None)
    op.alter_column(
        'task_scheduler',
        'enabled',
        new_column_name='status',
        existing_type=sa.Boolean(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using='CASE WHEN enabled THEN 1 ELSE 0 END',
        comment='状态（0停用 1正常）',
    )


def downgrade() -> None:
    op.alter_column('task_scheduler', 'status', existing_type=sa.Integer(), server_default=None)
    op.alter_column(
        'task_scheduler',
        'status',
        new_column_name='enabled',
        existing_type=sa.Integer(),
        type_=sa.Boolean(),
        existing_nullable=False,
        postgresql_using='status = 1',
        comment='是否启用任务',
    )
