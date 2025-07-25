# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(120), unique=True, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    zip_code = db.Column(db.String(10), nullable=False)
    county_name = db.Column(db.String(100), nullable=False)
    banned = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Password setter & checker
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class ZipCode(db.Model):
    __tablename__ = 'zip_codes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zip_code = db.Column(db.String(10), primary_key=True)
    county_name = db.Column(db.String(100), nullable=False)