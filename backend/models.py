# DANS backend/models.py

from datetime import datetime

from engine.arrows import clues_from_grid_data
from extensions import db # MODIFICATION ICI : On importe 'db' depuis notre fichier central

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    
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
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Le seul accès : « mes grilles, la plus récente d'abord »
    __table_args__ = (
        db.Index('ix_saved_grid_user_date', 'user_id', 'date_creation'),
    )

    def __repr__(self):
        return f"<SavedGrid '{self.name}' ({self.layout_id})>"

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
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
        }

    def to_json(self):
        # Les flèches ne sont pas stockées : elles se déduisent des cases noires et des débuts de mots,
        # si bien qu'une grille conservée avant leur arrivée en reçoit aussi (#26).
        grid = dict(self.payload) if isinstance(self.payload, dict) else {}
        grid['clues'] = clues_from_grid_data(grid.get('cells', []), grid.get('words', []))
        return {**self.summary(), 'grid': grid}
