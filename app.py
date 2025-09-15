from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from os import environ

app = Flask(__name__)

# CSRF Protection
csrf = CSRFProtect(app)

# App Configuration
app.config['SECRET_KEY'] = environ.get('SECRET_KEY', 'default-key-for-development')
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

from .models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from .routes import main as main_blueprint
app.register_blueprint(main_blueprint)

# This part is for running the app locally. You don't need it on Render.
# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True)
