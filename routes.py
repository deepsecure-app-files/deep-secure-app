from flask import render_template, flash, redirect, url_for, Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Child, db
from .forms import LoginForm, RegistrationForm, GeofenceForm # Assuming forms.py exists
from .utils import calculate_distance
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    if current_user.is_authenticated:
        if current_user.role == 'parent':
            return redirect(url_for('main.parent_dashboard'))
        elif current_user.role == 'child':
            return redirect(url_for('main.child_dashboard'))
    return render_template('pages/home.html')

@main.route("/signup", methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password, role=form.role.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('pages/signup.html', form=form)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            if user.role == 'parent':
                return redirect(url_for('main.parent_dashboard'))
            elif user.role == 'child':
                return redirect(url_for('main.child_dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('pages/login.html', form=form)

@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main.route("/parent_dashboard")
@login_required
def parent_dashboard():
    if current_user.role != 'parent':
        return redirect(url_for('main.home'))
    children = Child.query.filter_by(parent_id=current_user.id).all()
    return render_template('pages/parent_dashboard.html', children=children)

@main.route("/child_dashboard")
@login_required
def child_dashboard():
    if current_user.role != 'child':
        return redirect(url_for('main.home'))
    return render_template('pages/child_dashboard.html')

@main.route("/child_pairing", methods=['GET', 'POST'])
@login_required
def child_pairing():
    if current_user.role != 'parent':
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        pairing_code = request.form.get('pairing_code')
        child = Child.query.filter_by(pairing_code=pairing_code).first()

        if child and not child.parent_id:
            child.parent_id = current_user.id
            db.session.commit()
            flash(f"Child {child.name} has been paired successfully!", "success")
            return redirect(url_for('main.parent_dashboard'))
        else:
            flash("Invalid or used pairing code.", "danger")

    return render_template('pages/child_pairing.html')

@main.route("/child_profile/<int:child_id>")
@login_required
def child_profile(child_id):
    if current_user.role != 'parent':
        return redirect(url_for('main.home'))
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    geofences = child.geofences
    return render_template('pages/child_profile.html', child=child, geofences=geofences)

@main.route("/geofence/<int:child_id>", methods=['GET', 'POST'])
@login_required
def geofence(child_id):
    if current_user.role != 'parent':
        return redirect(url_for('main.home'))
    child = Child.query.filter_by(id=child_id, parent_id=current_user.id).first_or_404()
    return render_template('pages/geofence.html', child=child)

# API Endpoints
@main.route("/api/location", methods=['POST'])
def update_location():
    data = request.json
    try:
        child = User.query.filter_by(id=data['user_id']).first()
        if child and child.role == 'child':
            child_instance = Child.query.filter_by(user_id=child.id).first()
            if child_instance:
                child_instance.latitude = data['latitude']
                child_instance.longitude = data['longitude']
                child_instance.battery_level = data.get('battery_level')
                db.session.commit()
                return jsonify({"status": "success"})
            return jsonify({"status": "error", "message": "Child instance not found."}), 404
        return jsonify({"status": "error", "message": "User not found or is not a child."}), 404
    except KeyError:
        return jsonify({"status": "error", "message": "Invalid data format."}), 400

@main.route("/api/geofence/<int:child_id>", methods=['POST'])
@login_required
def save_geofence(child_id):
    if current_user.role != 'parent':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    data = request.json
    geofence_data = Geofence(
        name=data['name'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        radius=data['radius'],
        child_id=child_id
    )
    db.session.add(geofence_data)
    db.session.commit()
    return jsonify({"status": "success", "message": "Geofence saved."})
