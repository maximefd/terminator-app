# DANS backend/models.py

from datetime import datetime, timezone

from engine.arrows import clues_from_grid_data
from extensions import db # MODIFICATION ICI : On importe 'db' depuis notre fichier central

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    # Date à laquelle l'adresse a été confirmée par un lien reçu par e-mail ; None tant qu'elle ne l'est pas
    email_verified_at = db.Column(db.DateTime, nullable=True)
    # Les jetons émis avant cette date (UTC) sont refusés : changer de mot de passe ferme toutes les sessions
    sessions_revoked_at = db.Column(db.DateTime, nullable=True)
    # Inscription et dernière connexion (UTC) : la seconde fixe la suppression des comptes inactifs
    # (3 ans, page de confidentialité). Vides pour les comptes créés avant leur arrivée.
    created_at = db.Column(db.DateTime, nullable=True, default=lambda: _utcnow())
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    dictionaries = db.relationship('Dictionary', backref='user', lazy='selectin', cascade="all, delete-orphan")
    grids = db.relationship('SavedGrid', backref='user', lazy='selectin', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

class Dictionary(db.Model):
    __tablename__ = 'dictionary'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    words = db.relationship('PersonalWord', backref='dictionary', lazy='selectin', cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uix_user_dico_name'),
    )

    def __repr__(self):
        return f"<Dictionary {self.name} (User {self.user_id})>"

    def to_json(self, include_words=False):
        data = { 'id': self.id, 'name': self.name, 'is_active': self.is_active, 'user_id': self.user_id }
        if include_words:
            data['words'] = [w.to_json() for w in self.words]
        return data

class PersonalWord(db.Model):
    __tablename__ = 'personal_word'
    id = db.Column(db.Integer, primary_key=True)
    mot = db.Column(db.String(50), nullable=False)
    mot_affiche = db.Column(db.String(50), nullable=False)
    definition = db.Column(db.String(255), nullable=True)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)
    
    dictionary_id = db.Column(db.Integer, db.ForeignKey('dictionary.id'), nullable=False)

    def __repr__(self):
        return f"<PersonalWord '{self.mot_affiche}'>"

    def to_json(self):
        return {
            'id': self.id,
            'mot': self.mot,
            'mot_affiche': self.mot_affiche,
            'longueur': len(self.mot),
            'definition': self.definition,
            'source': 'PERSONNEL',
            'date_ajout': self.date_ajout.isoformat() if self.date_ajout else None
        }
class SavedGrid(db.Model):
    """Une grille générée que l'auteur a voulu garder.

    Le contenu est stocké **tel quel** (`payload`), et non regénéré à la demande : le lexique est
    curé de semaine en semaine et le catalogue de layouts s'enrichit, si bien que la même seed ne
    redonnerait pas la même grille six mois plus tard. Une grille conservée doit rester celle que
    l'auteur a vue.
    """
    __tablename__ = 'saved_grid'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    layout_id = db.Column(db.String(30), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    # La seed de génération, quand elle est connue : elle sert à retrouver l'origine d'une grille
    seed = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.JSON, nullable=False)
    # Définition de chaque mot, par clé « x-y-direction » — la **position**, jamais le texte : une
    # lettre corrigée à la main renomme le mot, et une clé fondée sur le texte laisserait sa
    # définition orpheline ([ADR 0012](docs/adr/0012-grille-modifiable.md)).
    definitions = db.Column(db.JSON, nullable=False, default=dict, server_default=db.text("'{}'"))
    # Bloc-notes de l'auteur : les idées viennent avant les définitions, et rarement en une fois
    notes = db.Column(db.Text, nullable=False, default="", server_default="")
    # Archivée : rangée hors de la liste courante, jamais supprimée
    archived = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Le seul accès : « mes grilles, la plus récente d'abord »
    __table_args__ = (
        db.Index('ix_saved_grid_user_date', 'user_id', 'date_creation'),
    )

    def __repr__(self):
        return f"<SavedGrid '{self.name}' ({self.layout_id})>"

    def shape(self) -> list[str]:
        """La forme de la grille, une ligne par rangée : « x » case définition, « - » case lettre.

        De quoi dessiner une miniature dans la liste sans transporter les lettres ni les mots :
        c'est la silhouette qui distingue deux grilles d'un coup d'œil, pas leur contenu.
        """
        cells = (self.payload or {}).get("cells", []) if isinstance(self.payload, dict) else []
        rows = [["-"] * self.width for _ in range(self.height)]
        for cell in cells:
            if 0 <= cell.get("y", -1) < self.height and 0 <= cell.get("x", -1) < self.width:
                rows[cell["y"]][cell["x"]] = "x" if cell.get("is_black") else "-"
        return ["".join(row) for row in rows]

    def summary(self):
        """Ce qu'il faut pour lister les grilles sans transporter toutes leurs cases."""
        words = self.payload.get('words', []) if isinstance(self.payload, dict) else []
        return {
            'id': self.id,
            'name': self.name,
            'layout': self.layout_id,
            'width': self.width,
            'height': self.height,
            'seed': self.seed,
            'word_count': len(words),
            'must_words': self.payload.get('must_words', []) if isinstance(self.payload, dict) else [],
            'defined_count': len(self.definitions or {}),
            'shape': self.shape(),
            'archived': self.archived,
            'has_notes': bool((self.notes or "").strip()),
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
        }

    def to_json(self):
        # Les flèches ne sont pas stockées : elles se déduisent des cases noires et des débuts de mots,
        # si bien qu'une grille conservée avant leur arrivée en reçoit aussi (#26).
        grid = dict(self.payload) if isinstance(self.payload, dict) else {}
        grid['clues'] = clues_from_grid_data(grid.get('cells', []), grid.get('words', []))
        return {**self.summary(), 'grid': grid, 'definitions': self.definitions or {},
                'notes': self.notes or ""}


class RevokedToken(db.Model):
    """Jeton révoqué avant son expiration, à la déconnexion ([ADR 0015](../docs/adr/0015-session-en-cookies.md)).

    Gardé jusqu'à `expires_at` seulement : au-delà, le jeton est refusé de toute façon.
    """
    __tablename__ = 'revoked_token'
    jti = db.Column(db.String(64), primary_key=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class UsageEvent(db.Model):
    """Un fait d'usage, écrit par l'API ([ADR 0016](../docs/adr/0016-mesure-d-usage-sans-cookie.md)).

    Jamais d'adresse IP : le visiteur est une empreinte du jour (usage.py). `user_id` n'est posé que là où
    un parcours en a besoin (compte, grille conservée) ; l'événement disparaît avec le compte. Les mots
    imposés en clair (`words`) sont effacés à 90 jours, les événements à 13 mois.
    """
    __tablename__ = 'usage_event'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: _utcnow(), index=True)
    # generation, search, account, grid, error
    kind = db.Column(db.String(20), nullable=False)
    # Ce qui s'est passé : « grid », « timeout », « busy_server », « register »…
    outcome = db.Column(db.String(40), nullable=True)
    status = db.Column(db.Integer, nullable=False)
    route = db.Column(db.String(80), nullable=True)
    site = db.Column(db.String(10), nullable=False)
    lang = db.Column(db.String(5), nullable=False)
    country = db.Column(db.String(2), nullable=True)
    visitor = db.Column(db.String(32), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    duration_ms = db.Column(db.Integer, nullable=True)
    cpu_ms = db.Column(db.Integer, nullable=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    # none_as_null : « pas de mots » est un NULL SQL, que la purge et les requêtes reconnaissent
    words = db.Column(db.JSON(none_as_null=True), nullable=True)

    __table_args__ = (
        db.Index('ix_usage_event_kind_date', 'kind', 'created_at'),
    )


class VisitorSalt(db.Model):
    """Le sel du jour de l'empreinte des visiteurs : secret, remplacé et détruit chaque jour (ADR 0016).

    En base, pour que les workers de gunicorn comptent le même visiteur de la même façon.
    """
    __tablename__ = 'visitor_salt'
    day = db.Column(db.Date, primary_key=True)
    salt = db.Column(db.String(64), nullable=False)
