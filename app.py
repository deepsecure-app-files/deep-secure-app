from flask import Flask
from config import Config
from models import db
from routes import main as main_blueprint   # fixed import (no dot)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init database
    db.init_app(app)

    # register blueprint
    app.register_blueprint(main_blueprint)

    # setup database with app context
    with app.app_context():
        db.create_all()

    return app


# create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
