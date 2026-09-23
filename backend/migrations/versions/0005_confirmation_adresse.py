"""Confirmation de l'adresse e-mail ([ADR 0014](../../../docs/adr/0014-emails-du-compte.md)).

Les comptes existants ne sont pas confirmés : leur adresse n'a jamais été vérifiée. Ils peuvent demander le
lien depuis « Mon compte », et changer de mot de passe par e-mail les confirme aussi.

Revision ID: 0005_confirmation_adresse
Revises: 0004_notes_archivage_cles
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = '0005_confirmation_adresse'
down_revision = '0004_notes_archivage_cles'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('email_verified_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('user', 'email_verified_at')
