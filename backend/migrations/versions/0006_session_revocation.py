"""Révocation des sessions ([ADR 0015](../../../docs/adr/0015-session-en-cookies.md)).

- `revoked_token` : les jetons révoqués à la déconnexion, gardés jusqu'à leur expiration ;
- `user.sessions_revoked_at` : changer de mot de passe ferme toutes les sessions ouvertes avant.

Revision ID: 0006_session_revocation
Revises: 0005_confirmation_adresse
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = '0006_session_revocation'
down_revision = '0005_confirmation_adresse'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('sessions_revoked_at', sa.DateTime(), nullable=True))
    op.create_table(
        'revoked_token',
        sa.Column('jti', sa.String(length=64), primary_key=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_revoked_token_expires_at', 'revoked_token', ['expires_at'])


def downgrade():
    op.drop_index('ix_revoked_token_expires_at', table_name='revoked_token')
    op.drop_table('revoked_token')
    op.drop_column('user', 'sessions_revoked_at')
