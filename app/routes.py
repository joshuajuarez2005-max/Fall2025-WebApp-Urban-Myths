"""
This routes.py script will contain the routes/path for our application
"""

from flask import Blueprint, render_template, request, session, url_for
from app.db import query_test
from app.login import handle_login



main = Blueprint("main", __name__)
## initializies a blueprint#

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pass
    return render_template("login.html")

@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pass
    return render_template("registration.html")

@main.route("/about")
def about():
    return render_template("about.html")
