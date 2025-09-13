from flask import render_template, request, redirect, url_for, session, Blueprint, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from models import db, User, Child, Geofence
from datetime import datetime
import uuid

main = Blueprint('main', __name__)

def generate_pairing_code():
    return secrets.token_hex(3).upper()

def is_parent_user():
    if 'phone_number' not in session:
        return False
    user = User.query.filter_by(phone_number=session['phone_number']).first()
    return user and user.is_parent

def is_child_user():
    if 'phone_number' not in session:
        return False
    user = User.query.filter_by(phone_number=session['phone_number']).first()
    return user and user.is_child

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'phone_number' not in session:
            flash("Please log in to access this page.", 'info')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def home():
    if 'phone_number' in session:
        user = User.query.filter_by(phone_number=session['phone_number']).first()
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
            session['phone_number'] = phone_number
            if user.is_parent:
                return redirect(url_for('main.parent_dashboard'))
            else:
                return redirect(url_for('main.child_dashboard'))
        else:
            flash("Invalid phone number or password.", 'danger')
            return render_template('pages/login.html')
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
        session['phone_number'] = phone_number
        if new_user.is_parent:
            return redirect(url_for('main.parent_dashboard'))
        else:
            return redirect(url_for('main.child_dashboard'))
    return render_template('pages/signup.html')
    
@main.route('/logout')
def logout():
    session.pop('phone_number', None)
    flash("You have been logged out.", 'info')
    return redirect(url_for('main.home'))

@main.route('/parent_dashboard')
@login_required
def parent_dashboard():
    if not is_parent_user():
        flash("Access Denied: You are not a parent.", 'danger')
        return redirect(url_for('main.home'))
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    children = parent_user.children
    return render_template('pages/parent_dashboard.html', parent=parent_user,
                          
                           @main.route('/add_child', methods=['POST'])
@login_required
def add_child():
    if not is_parent_user():
        flash("Access Denied: You are not a parent.", 'danger')
        return redirect(url_for('main.home'))
    
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    child_name = request.form.get('child_name')

    if not child_name:
        flash("Child name cannot be empty.", 'danger')
        return redirect(url_for('main.add_child_page'))

    try:
        # ✅ 6 digit random pairing code
        import random, string
        new_pairing_code = ''.join(random.choices(string.digits, k=6))
        while Child.query.filter_by(pairing_code=new_pairing_code).first():
            new_pairing_code = ''.join(random.choices(string.digits, k=6))

        new_child_entry = Child(
            name=child_name,
            pairing_code=new_pairing_code,
            parent_id=parent_user.id
        )
        db.session.add(new_child_entry)
        db.session.commit()

        # ✅ नया child जोड़ने के बाद सीधे code दिखाएगा
        return render_template('pages/child_added.html', child=new_child_entry)

    except Exception as e:
        db.session.rollback()
        flash("Error while adding child, try again.", 'danger')
        return redirect(url_for('main.add_child_page'))

@main.route('/add_child', methods=['POST'])
@login_required
def add_child():
    if not is_parent_user():
        flash("Access Denied: You are not a parent.", 'danger')
        return redirect(url_for('main.home'))
    
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
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

        # This part is updated to render a new HTML file directly
        return render_template('pages/child_added.html', child=new_child_entry)

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while adding the child. Please try again.", 'danger')
        print(f"Error: {e}")
        return redirect(url_for('main.add_child_page'))

@main.route('/child_profile/<int:child_id>')
@login_required
def child_profile(child_id):
    if not is_parent_user():
        flash("Access Denied.", 'danger')
        return redirect(url_for('main.home'))
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    child_profile = Child.query.get(child_id)
    if not child_profile or child_profile.parent_id != parent_user.id:
        flash("Child not found or you don't have access.", 'danger')
        return redirect(url_for('main.parent_dashboard'))
    return render_template('pages/child_profile.html', child=child_profile)

@main.route('/child_dashboard')
@login_required
def child_dashboard():
    if not is_child_user():
        flash("Access Denied: You are not a child user.", 'danger')
        return redirect(url_for('main.home'))
    child_user = User.query.filter_by(phone_number=session['phone_number']).first()
    child_profile = Child.query.filter_by(child_id=child_user.id).first()
    if not child_profile:
        return redirect(url_for('main.pair_child'))
    return render_template('pages/child_dashboard.html', child=child_profile)

@main.route('/pair_child', methods=['GET', 'POST'])
@login_required
def pair_child():
    if request.method == 'POST':
        pairing_code = request.form.get('pairing_code')
        child_user = User.query.filter_by(phone_number=session['phone_number']).first()
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
@login_required
def update_location():
    if not is_child_user():
        return jsonify({"success": False, "message": "Access Denied."}), 403
    child_user = User.query.filter_by(phone_number=session['phone_number']).first()
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
@login_required
def get_location(child_id):
    if not is_parent_user():
        return jsonify({"success": False, "message": "Access Denied."}), 403
    child_profile = Child.query.get(child_id)
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
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
@login_required
def geofence_page():
    if not is_parent_user():
        flash("Access Denied: Not a parent user.", 'danger')
        return redirect(url_for('main.home'))
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    return render_template('pages/geofence.html', parent=parent_user)

@main.route('/api/save_geofence', methods=['POST'])
@login_required
def save_geofence():
    if not is_parent_user():
        return jsonify({"success": False, "message": "Access Denied."}), 403
    
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    data = request.get_json()

    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        radius = int(data.get('radius'))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid data format."}), 400

    new_geofence = Geofence(
        parent_id=parent_user.id,
        location_name=data.get('location_name'),
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )
    db.session.add(new_geofence)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Geofence saved successfully."})

@main.route('/api/get_geofences')
@login_required
def get_geofences():
    if not is_parent_user():
        return jsonify({"success": False, "message": "Access Denied."}), 403
    parent_user = User.query.filter_by(phone_number=session['phone_number']).first()
    geofences = Geofence.query.filter_by(parent_id=parent_user.id).all()
    geofence_list = [{
        "id": f.id,
        "name": f.location_name,
        "lat": f.latitude,
        "lng": f.longitude,
        "radius": f.radius
    } for f in geofences]
    return jsonify({"geofences": geofence_list})
