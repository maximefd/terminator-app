# DANS backend/models.py

from datetime import datetime
from extensions import db # MODIFICATION ICI : On importe 'db' depuis notre fichier central

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    
    dictionaries = db.relationship('Dictionary', backref='user', lazy='selectin', cascade="all, delete-orphan")

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