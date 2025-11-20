"""
This routes.py script will contain the routes/path for our application
"""

from flask import Blueprint, render_template, request, session, url_for
from .db import query_test
from .login import handle_login
from .register import handle_registration


main = Blueprint("main", __name__)
## initializies a blueprint

@main.route("/")
def index():
    ## we will change this to render html home page later on 
    return render_template("index.html")
    
## Add the route for the login 
@main.route("/login", methods =("GET", "POST")) ##localhost/
def login():
    if request.method == "POST":
        ## Login.py script logic here

        return render_template("login.html")

## adding the register route 
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ## Call the register.py script logic here
         
        return render_template("register.html")

## Adding the about page route
@main.route("/about")
def about():
    return render_template("about.html")
