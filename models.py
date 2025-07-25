# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

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

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    address = db.Column(db.String(255), nullable=False)
    alert_type = db.Column(db.String(100), nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    false_votes = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='alerts')

class AlertVote(db.Model):
    __tablename__ = 'alert_votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'), nullable=False)
    is_false = db.Column(db.Boolean, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'alert_id', name='_user_alert_uc'),)