"""Définitions des grilles conservées (#27).

Une colonne à part, et non un champ du `payload` : la grille ne bouge plus une fois produite,
alors que les définitions s'écrivent au fil de la frappe.

Revision ID: 0003_definitions_des_grilles
Revises: 0002_grilles_conservees
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

revision = '0003_definitions_des_grilles'
down_revision = '0002_grilles_conservees'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('saved_grid', sa.Column('definitions', sa.JSON(), nullable=True))
    # Les grilles déjà conservées n'ont pas de définitions : un objet vide, pas NULL,
    # pour que le code n'ait qu'un seul cas à traiter.
    op.execute("UPDATE saved_grid SET definitions = '{}'")
    op.alter_column('saved_grid', 'definitions', nullable=False)


def downgrade():
    op.drop_column('saved_grid', 'definitions')
