from .app import db
from flask_login import UserMixin
import secrets

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='parent')
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    children = db.relationship('Child', backref='parent', lazy=True)
    
    def __repr__(self):
        return f"User('{self.email}', '{self.role}')"

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    pairing_code = db.Column(db.String(20), unique=True, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    battery_level = db.Column(db.Float)
    
    # Relationships
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    geofences = db.relationship('Geofence', backref='child', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __init__(self, **kwargs):
        super(Child, self).__init__(**kwargs)
        if not self.pairing_code:
            self.pairing_code = secrets.token_hex(4).upper()

    def __repr__(self):
        return f"Child('{self.name}', '{self.pairing_code}')"

class Geofence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)

    def __repr__(self):
        return f"Geofence('{self.name}', '{self.latitude}', '{self.longitude}')"
