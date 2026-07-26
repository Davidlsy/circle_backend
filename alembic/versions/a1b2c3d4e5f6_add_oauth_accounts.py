"""add oauth_accounts

Revision ID: a1b2c3d4e5f6
Revises: c0a9aa0c37a5
Create Date: 2026-07-26 10:00:00.000000

新增第三方账号绑定表 oauth_accounts，用于支持微信/抖音/支付宝第三方登录（v2）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c0a9aa0c37a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('oauth_uid', sa.String(length=100), nullable=False),
        sa.Column('access_token', sa.String(length=500), nullable=True),
        sa.Column('refresh_token', sa.String(length=500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'oauth_uid', name='uq_provider_oauth_uid'),
    )
    op.create_index('ix_oauth_accounts_id', 'oauth_accounts', ['id'])
    op.create_index('ix_user_provider', 'oauth_accounts', ['user_id', 'provider'])


def downgrade() -> None:
    op.drop_index('ix_user_provider', table_name='oauth_accounts')
    op.drop_index('ix_oauth_accounts_id', table_name='oauth_accounts')
    op.drop_table('oauth_accounts')
