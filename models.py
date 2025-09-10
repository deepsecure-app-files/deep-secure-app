from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_parent = db.Column(db.Boolean, default=False)
    is_child = db.Column(db.Boolean, default=False)
    
    # Relationship for parent users
    children = db.relationship('Child', foreign_keys='Child.parent_id', backref='parent', lazy=True)
    
    # Relationship for child users
    parent_of_child = db.relationship('Child', foreign_keys='Child.child_id', backref='child_user', lazy=True)
    
    geofences = db.relationship('Geofence', backref='parent', lazy=True)

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    pairing_code = db.Column(db.String(6), unique=True, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_latitude = db.Column(db.Float)
    last_longitude = db.Column(db.Float)
    battery_level = db.Column(db.Integer)
    
class Geofence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, nullable=False)
