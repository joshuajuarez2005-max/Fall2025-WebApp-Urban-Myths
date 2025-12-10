from flask import Flask  # This class "Flask" let's us create an instance of Flask
from .db import init_app  # This is the function that closes our db connection automatically 
from .routes import main  # blueprint with routes

def create_app():
    """
    Called from run.py to create the app and run it on a development server.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # load config from config.py
    app.config.from_object("config.Config")

    # set up DB teardown
    init_app(app)

    # register blueprint routes
    app.register_blueprint(main)

    return app
