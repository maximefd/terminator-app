# DANS backend/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

# On crée les instances "vides" de nos extensions ici.
# Elles seront configurées plus tard par notre create_app().
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()