"""Rôle d'administrateur ([ADR 0016](../../../docs/adr/0016-mesure-d-usage-sans-cookie.md), point 6).

`user.is_admin` ouvre le poste de pilotage. Il se pose en ligne de commande (`flask admin grant`), sur une
adresse confirmée, jamais par l'API. Migration additive (ADR 0019) : faux pour tous les comptes existants.

Revision ID: 0008_role_administrateur
Revises: 0007_mesure_d_usage
Create Date: 2026-09-25
"""
import sqlalchemy as sa
from alembic import op

revision = '0008_role_administrateur'
down_revision = '0007_mesure_d_usage'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('user', 'is_admin')
