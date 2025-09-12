from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    is_parent = db.Column(db.Boolean, default=False)
    is_child = db.Column(db.Boolean, default=False)
    children = db.relationship('Child', backref='parent', lazy=True, foreign_keys='Child.parent_id')

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    pairing_code = db.Column(db.String(6), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # This line has been corrected
    child_id = db.Column(db.String(36), unique=True, nullable=True)
    last_latitude = db.Column(db.String(255))
    last_longitude = db.Column(db.String(255))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    battery_level = db.Column(db.Integer)

class Geofence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_name = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.String(255), nullable=False)
    longitude = db.Column(db.String(255), nullable=False)
    radius = db.Column(db.Integer, nullable=False)
