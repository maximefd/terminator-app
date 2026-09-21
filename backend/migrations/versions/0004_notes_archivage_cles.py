"""Bloc-notes, archivage, et clés de définitions fondées sur la position (#27).

La clé d'une définition contenait le texte du mot (« PORTE-1-2-across »). La modification
manuelle des lettres ([ADR 0012](../../../docs/adr/0012-grille-modifiable.md)) renomme les mots :
une clé fondée sur le texte laisserait chaque définition orpheline au premier « O » changé en
« E ». Les clés deviennent « 1-2-across » — la position et le sens, qui ne bougent pas.

Revision ID: 0004_notes_archivage_cles
Revises: 0003_definitions_des_grilles
Create Date: 2026-09-21
"""
import json

import sqlalchemy as sa
from alembic import op

revision = '0004_notes_archivage_cles'
down_revision = '0003_definitions_des_grilles'
branch_labels = None
depends_on = None


def _rekey(definitions: dict, to_position: bool) -> dict:
    """« PORTE-1-2-across » <-> « 1-2-across ». La position est déjà dans la clé : rien ne se perd."""
    migrated = {}
    for key, text in (definitions or {}).items():
        parts = key.split("-")
        if to_position:
            # On garde les trois derniers morceaux : x, y, direction
            migrated["-".join(parts[-3:])] = text
        else:
            migrated[key] = text
    return migrated


def _walk_grids(connection, to_position: bool):
    rows = connection.execute(sa.text("SELECT id, definitions FROM saved_grid")).fetchall()
    for row in rows:
        definitions = row[1]
        if isinstance(definitions, str):
            definitions = json.loads(definitions)
        if not definitions:
            continue
        connection.execute(
            sa.text("UPDATE saved_grid SET definitions = :definitions WHERE id = :id"),
            {"definitions": json.dumps(_rekey(definitions, to_position)), "id": row[0]},
        )


def upgrade():
    op.add_column('saved_grid', sa.Column('notes', sa.Text(), nullable=False, server_default=''))
    op.add_column('saved_grid',
                  sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.false()))
    # La liste courante n'affiche que les grilles non archivées : l'index doit le savoir
    op.create_index('ix_saved_grid_user_archived', 'saved_grid', ['user_id', 'archived', 'date_creation'])
    _walk_grids(op.get_bind(), to_position=True)


def downgrade():
    # Le texte du mot n'est pas reconstituable depuis la clé : on laisse les clés en position,
    # elles restent lisibles. Le reste se défait proprement.
    op.drop_index('ix_saved_grid_user_archived', table_name='saved_grid')
    op.drop_column('saved_grid', 'archived')
    op.drop_column('saved_grid', 'notes')
