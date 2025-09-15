from flask import render_template, request, redirect, url_for, session, Blueprint, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from models import db, User, Child, Geofence
from datetime import datetime, timedelta
import uuid

# Flask-WTF CSRF Protection (You need to configure this in your app.py)
from flask_wtf.csrf import CSRFProtect

main = Blueprint('main', __name__)

# --- Helper Functions ---

def generate_pairing_code():
    return secrets.token_hex(3).upper()

def get_current_user():
    if 'phone_number' in session:
        return User.query.filter_by(phone_number=session['phone_number']).first()
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash("Please log in to access this page.", 'info')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def parent_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_parent:
            flash("Access Denied: You are not a parent.", 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def child_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_child:
            flash("Access Denied: You are not a child user.", 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@main.route('/')
def home():
    user = get_current_user()
    if user:
        if user.is_parent:
            return redirect(url_for('main.parent_dashboard'))
        else:
            return redirect(url_for('main.child_dashboard'))
    return render_template('pages/home.html')

@main.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        user = User.query.filter_by(phone_number=phone_number).first()
        if user and check_password_hash(user.password_hash, password):
            session.permanent = True
            session['phone_number'] = phone_number
            if user.is_parent:
                return redirect(url_for('main.parent_dashboard'))
            else:
                return redirect(url_for('main.child_dashboard'))
        else:
            flash("Invalid phone number or password.", 'danger')
    return render_template('pages/login.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']
        role = request.form['role']
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            flash("Phone number already exists. Please login or use a different number.", 'danger')
            return redirect(url_for('main.signup'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            phone_number=phone_number,
            password_hash=hashed_password,
            is_parent=(role == 'parent'),
            is_child=(role == 'child')
        )
        db.session.add(new_user)
        db.session.commit()
        session.permanent = True
        session['phone_number'] = phone_number
        if new_user.is_parent:
            return redirect(url_for('main.parent_dashboard'))
        else:
            return redirect(url_for('main.child_dashboard'))
    return render_template('pages/signup.html')

@main.route('/logout')
@login_required
def logout():
    session.pop('phone_number', None)
    flash("You have been logged out.", 'info')
    return redirect(url_for('main.home'))

@main.route('/parent_dashboard')
@parent_required
def parent_dashboard():
    parent_user = get_current_user()
    children = parent_user.children
    return render_template('pages/parent_dashboard.html', parent=parent_user, children=children)

@main.route('/add_child_page')
@parent_required
def add_child_page():
    return render_template('pages/add_child.html')

@main.route('/add_child', methods=['POST'])
@parent_required
def add_child():
    parent_user = get_current_user()
    child_name = request.form.get('child_name')
    if not child_name:
        flash("Child name cannot be empty.", 'danger')
        return redirect(url_for('main.add_child_page'))
    try:
        new_pairing_code = generate_pairing_code()
        while Child.query.filter_by(pairing_code=new_pairing_code).first():
            new_pairing_code = generate_pairing_code()
        new_child_entry = Child(
            name=child_name,
            pairing_code=new_pairing_code,
            parent_id=parent_user.id
        )
        db.session.add(new_child_entry)
        db.session.commit()
        flash(f"Child added successfully! The pairing code is: {new_child_entry.pairing_code}", 'success')
        return redirect(url_for('main.parent_dashboard'))
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while adding the child. Please try again.", 'danger')
        return redirect(url_for('main.add_child_page'))

@main.route('/child_profile/<int:child_id>')
@parent_required
def child_profile(child_id):
    parent_user = get_current_user()
    child_profile = Child.query.get(child_id)
    if not child_profile or child_profile.parent_id != parent_user.id:
        flash("Child not found or you don't have access.", 'danger')
        return redirect(url_for('main.parent_dashboard'))
    return render_template('pages/child_profile.html', child=child_profile)

@main.route('/child_dashboard')
@child_required
def child_dashboard():
    child_user = get_current_user()
    child_profile = Child.query.filter_by(child_id=child_user.id).first()
    if not child_profile:
        return redirect(url_for('main.pair_child'))
    return render_template('pages/child_dashboard.html', child=child_profile)

@main.route('/pair_child', methods=['GET', 'POST'])
@child_required
def pair_child():
    if request.method == 'POST':
        pairing_code = request.form.get('pairing_code')
        child_user = get_current_user()
        child_entry = Child.query.filter_by(pairing_code=pairing_code).first()
        if child_entry and not child_entry.child_id:
            child_entry.child_id = child_user.id
            child_entry.pairing_code = None
            db.session.commit()
            flash("Pairing successful! You are now connected to a parent.", 'success')
            return redirect(url_for('main.child_dashboard'))
        else:
            flash("Invalid or already used pairing code.", 'danger')
            return redirect(url_for('main.pair_child'))
    return render_template('pages/child_pairing.html')

@main.route('/api/update_location', methods=['POST'])
@child_required
def update_location():
    child_user = get_current_user()
    child_profile = Child.query.filter_by(child_id=child_user.id).first()
    if not child_profile:
        return jsonify({"success": False, "message": "Child not found."}), 404
    data = request.get_json()
    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid latitude or longitude."}), 400
    child_profile.last_latitude = latitude
    child_profile.last_longitude = longitude
    child_profile.battery_level = data.get('battery')
    child_profile.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "message": "Location updated."})

@main.route('/api/get_location/<int:child_id>')
@parent_required
def get_location(child_id):
    parent_user = get_current_user()
    child_profile = Child.query.get(child_id)
    if not child_profile or child_profile.parent_id != parent_user.id:
        return jsonify({"success": False, "message": "Child not found or you don't have access."}), 404
    location_data = {
        "latitude": child_profile.last_latitude,
        "longitude": child_profile.last_longitude,
        "last_seen": child_profile.last_seen.isoformat() if child_profile.last_seen else None,
        "battery": child_profile.battery_level
    }
    return jsonify(location_data)

@main.route('/geofence')
@parent_required
def geofence_page():
    parent_user = get_current_user()
    return render_template('pages/geofence.html', parent=parent_user)

@main.route('/api/save_geofence', methods=['POST'])
@parent_required
def save_geofence():
    parent_user = get_current_user()
    data = request.get_json()
    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        radius = int(data.get('radius'))
        location_name = data.get('location_name')
        if not location_name or not latitude or not longitude or not radius:
            return jsonify({"success": False, "message": "Missing data."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid data format."}), 400
    new_geofence = Geofence(
        parent_id=parent_user.id,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )
    db.session.add(new_geofence)
    db.session.commit()
    return jsonify({"success": True, "message": "Geofence saved successfully."})

@main.route('/api/get_geofences')
@parent_required
def get_geofences():
    parent_user = get_current_user()
    geofences = Geofence.query.filter_by(parent_id=parent_user.id).all()
    geofence_list = [{
        "id": f.id,
        "name": f.location_name,
        "lat": f.latitude,
        "lng": f.longitude,
        "radius": f.radius
    } for f in geofences]
    return jsonify({"geofences": geofence_list})

