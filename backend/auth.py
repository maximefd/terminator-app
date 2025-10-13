# DANS backend/auth.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from extensions import db, bcrypt # MODIFICATION ICI : On importe depuis notre fichier central
from models import User # MODIFICATION ICI : Import direct, sans le "."

# On crée le Blueprint "vide"
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Crée un nouvel utilisateur."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Cet email est déjà utilisé."}), 409

    # On utilise l'objet 'bcrypt' importé pour hacher le mot de passe
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    new_user = User(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": f"Utilisateur {email} créé avec succès."}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Connecte un utilisateur et renvoie les tokens JWT."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    user = User.query.filter_by(email=email).first()

    # On utilise l'objet 'bcrypt' importé pour vérifier le mot de passe
    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200

    return jsonify({"error": "Identifiants invalides."}), 401