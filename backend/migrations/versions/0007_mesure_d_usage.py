"""Mesure d'usage côté serveur ([ADR 0016](../../../docs/adr/0016-mesure-d-usage-sans-cookie.md)).

- `usage_event` : un fait d'usage (génération, recherche, compte, grille conservée, erreur) ;
- `visitor_salt` : le sel du jour de l'empreinte des visiteurs, détruit le lendemain ;
- `user.created_at` et `user.last_login_at` : la seconde fixe la suppression des comptes inactifs.
  Vides pour les comptes existants : leur date d'inscription n'est pas connue.

Revision ID: 0007_mesure_d_usage
Revises: 0006_session_revocation
Create Date: 2026-09-25
"""
import sqlalchemy as sa
from alembic import op

revision = '0007_mesure_d_usage'
down_revision = '0006_session_revocation'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.create_table(
        'usage_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('outcome', sa.String(length=40), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('route', sa.String(length=80), nullable=True),
        sa.Column('site', sa.String(length=10), nullable=False),
        sa.Column('lang', sa.String(length=5), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('visitor', sa.String(length=32), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('cpu_ms', sa.Integer(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('words', sa.JSON(), nullable=True),
    )
    op.create_index('ix_usage_event_created_at', 'usage_event', ['created_at'])
    op.create_index('ix_usage_event_user_id', 'usage_event', ['user_id'])
    op.create_index('ix_usage_event_kind_date', 'usage_event', ['kind', 'created_at'])
    op.create_table(
        'visitor_salt',
        sa.Column('day', sa.Date(), primary_key=True),
        sa.Column('salt', sa.String(length=64), nullable=False),
    )


def downgrade():
    op.drop_table('visitor_salt')
    op.drop_index('ix_usage_event_kind_date', table_name='usage_event')
    op.drop_index('ix_usage_event_user_id', table_name='usage_event')
    op.drop_index('ix_usage_event_created_at', table_name='usage_event')
    op.drop_table('usage_event')
    op.drop_column('user', 'last_login_at')
    op.drop_column('user', 'created_at')
