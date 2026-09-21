"""Schéma initial : comptes, dictionnaires personnels et leurs mots.

Cette révision décrit la base **telle qu'elle existait avant Alembic**, quand
`db.create_all()` la fabriquait au démarrage. Sur une base déjà en place, elle n'est
jamais rejouée : l'application la marque comme appliquée (voir `app.prepare_database`).

Revision ID: 0001_schema_initial
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from alembic import op

revision = '0001_schema_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password', sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_table(
        'dictionary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uix_user_dico_name'),
    )
    op.create_table(
        'personal_word',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mot', sa.String(length=50), nullable=False),
        sa.Column('mot_affiche', sa.String(length=50), nullable=False),
        sa.Column('definition', sa.String(length=255), nullable=True),
        sa.Column('date_ajout', sa.DateTime(), nullable=True),
        sa.Column('dictionary_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['dictionary_id'], ['dictionary.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('personal_word')
    op.drop_table('dictionary')
    op.drop_table('user')
