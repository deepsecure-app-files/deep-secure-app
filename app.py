from flask import Flask
from config import Config
from models import db
from routes import main as main_blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    # Import and register blueprints
    app.register_blueprint(main_blueprint)
    
    # Setup database with app context
    with app.app_context():
        db.create_all()
    
    return app

# create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
