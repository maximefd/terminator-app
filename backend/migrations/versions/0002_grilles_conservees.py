"""Grilles conservées (#24).

Le contenu de la grille est stocké en JSON, tel que la génération l'a renvoyé : le lexique
est curé au fil des semaines et le catalogue de layouts s'enrichit, si bien que la même seed
ne redonnerait pas la même grille plus tard.

Revision ID: 0002_grilles_conservees
Revises: 0001_schema_initial
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

revision = '0002_grilles_conservees'
down_revision = '0001_schema_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_grid',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('layout_id', sa.String(length=30), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('date_creation', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Le seul accès : « mes grilles, la plus récente d'abord »
    op.create_index('ix_saved_grid_user_date', 'saved_grid', ['user_id', 'date_creation'])


def downgrade():
    op.drop_index('ix_saved_grid_user_date', table_name='saved_grid')
    op.drop_table('saved_grid')
