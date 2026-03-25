"""add_email_auth_and_balance_fields

Revision ID: 561f8b003c04
Revises: fbc4bc23de4d
Create Date: 2026-03-22 13:44:04.999011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '561f8b003c04'
down_revision: Union[str, None] = 'fbc4bc23de4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to existing users table
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('auth_method', sa.String(length=16), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('otp_code', sa.String(length=6), nullable=True))
    op.add_column('users', sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('country', sa.String(length=2), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('account_balance', sa.Numeric(precision=18, scale=8), nullable=True))
    
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'account_balance')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'country')
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'otp_expires_at')
    op.drop_column('users', 'otp_code')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'auth_method')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email')
