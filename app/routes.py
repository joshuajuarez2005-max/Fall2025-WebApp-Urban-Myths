"""
This routes.py script will contain the routes/path for our application
"""

from markupsafe import Markup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import (
    Blueprint,
    render_template,
    request,
    session,
    url_for,
    redirect,
    flash,
    current_app,
)
from app.db import query_test           # still here if you need it elsewhere
from app.login import handle_login      # still here if you need it elsewhere

from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from config import Config   # uses the DB_* values from your config.py

# for email verification
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


main = Blueprint("main", __name__)
## initializes a blueprint #


def get_connection():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )


# ------------------ EMAIL VERIFICATION HELPERS ------------------

def get_serializer():
    return URLSafeTimedSerializer(
        secret_key=Config.SECRET_KEY,
        salt="email-confirm",
    )


def generate_confirmation_token(email: str) -> str:
    s = get_serializer()
    return s.dumps(email)


def confirm_token(token: str, max_age: int = 3600):
    """
    max_age is in seconds. 3600 = 1 hour.
    """
    s = get_serializer()
    return s.loads(token, max_age=max_age)


def send_verification_email(to_email: str, token: str):
    """
    Send a verification email via Gmail using settings from Config.
    Includes both plain-text and HTML with a 'Verify' button.
    """
    from flask import url_for

    verify_url = url_for("main.verify_email", token=token, _external=True)

    subject = "Confirm your Urban Myths account"

    # Plain-text version (fallback)
    text_body = f"""
Hi,

Thanks for registering for Urban Myths!

Please confirm your email by clicking the link below:

{verify_url}

If you did not create this account, you can ignore this email.
"""

    # HTML version with a button
    html_body = f"""
<html>
  <body>
    <p>Hi,</p>
    <p>Thanks for registering for <strong>Urban Myths</strong>!</p>
    <p>Please confirm your email by clicking the button below:</p>
    <p>
      <a href="{verify_url}"
         style="display:inline-block;padding:10px 18px;
                background-color:#007bff;color:#ffffff;
                text-decoration:none;border-radius:4px;">
        Verify my email
      </a>
    </p>
    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>If you did not create this account, you can ignore this email.</p>
  </body>
</html>
"""

    print("🔗 EMAIL VERIFICATION LINK:", verify_url)  # still useful while testing

    # Build the email with both text and HTML
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME
    msg["To"] = to_email

    part_text = MIMEText(text_body, "plain")
    part_html = MIMEText(html_body, "html")

    msg.attach(part_text)
    msg.attach(part_html)

    try:
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            if Config.MAIL_USE_TLS:
                server.starttls()
            if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Verification email sent to {to_email}")
    except Exception as e:
        print("❌ Failed to send verification email:", e)



# ------------------ ROUTES ------------------


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get form fields from login.html
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            # Look up user by email
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        except Error as e:
            # If MySQL connection fails, you'll see this in the browser and terminal
            print("MySQL login error:", e)
            flash("Database error during login. Please try again.", "error")
            return render_template("login.html")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

        # First: invalid email or wrong password
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        # Now we know email + password are correct.
        # Check if the user has verified their email.
        if not user.get("is_verified"):
            flash("Please verify your email before logging in. Check your email inbox.", "error")
            return render_template("login.html")

        # All good → log them in
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Logged in successfully!", "success")
        return redirect(url_for("main.index"))

    # GET or failed POST → show login page
    return render_template("login.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    # Debug info – optional
    print("DEBUG SECRET_KEY:", current_app.secret_key)
    print("DEBUG DB_USER:", Config.DB_USER, "DB_HOST:", Config.DB_HOST)

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Basic validation
        if not username or len(username) < 5:
            flash("Username must be at least 5 characters.", "error")
            return render_template("registration.html")

        if not email or not password:
            flash("Please fill out all fields.", "error")
            return render_template("registration.html")

        password_hash = generate_password_hash(password)

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            # 1. Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing = cursor.fetchone()
            if existing:
                flash("Email already registered. Please log in.", "error")
                return redirect(url_for("main.login"))

            # 2. Insert new user as UNVERIFIED
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, is_verified)
                VALUES (%s, %s, %s, %s)
                """,
                (username, email, password_hash, 0),
            )
            conn.commit()

            print("✅ Registered user in MySQL:", username, email)

                       # 3. Generate verification token
            token = generate_confirmation_token(email)

            # Build the full verification URL
            verify_url = url_for("main.verify_email", token=token, _external=True)

            # Print it to the terminal (debug)
            print("🔗 EMAIL VERIFICATION LINK:", verify_url)

            # Send real email via Gmail
            send_verification_email(email, token)

            # 4. Inform the user to check their email
            
            
            flash("Registration successful! Check your email to verify your account.", "success")
            return redirect(url_for("main.login"))



          

        except Error as e:
            print("MySQL register error:", e)
            flash("Database error during registration. Please try again.", "error")
            return render_template("registration.html")

        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

        # 4. Final message to user
        flash("Registration successful! Please check your email to verify your account.", "success")
        return redirect(url_for("main.login"))

    # GET request → show registration page
    return render_template("registration.html")


@main.route("/verify/<token>")
def verify_email(token):
    try:
        email = confirm_token(token)
    except SignatureExpired:
        flash("Verification link expired. Please register again.", "error")
        return redirect(url_for("main.register"))
    except BadSignature:
        flash("Invalid verification link.", "error")
        return redirect(url_for("main.register"))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, is_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            flash("Account not found.", "error")
            return redirect(url_for("main.register"))

        if user["is_verified"]:
            flash("Account already verified. Please log in.", "info")
            return redirect(url_for("main.login"))

        cursor.execute(
            "UPDATE users SET is_verified = 1 WHERE id = %s",
            (user["id"],),
        )
        conn.commit()

    except Error as e:
        print("MySQL verify error:", e)
        flash("Database error during verification.", "error")
        return redirect(url_for("main.register"))

    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    flash("Your email has been verified! You can now log in.", "success")
    return redirect(url_for("main.login"))


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/db-test")
def db_test():
    """
    Simple route to test if MySQL connection works.
    Visit /db-test in the browser.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return "MySQL connection: OK ✅"
    except Error as e:
        print("MySQL test error:", e)
        return f"MySQL connection FAILED ❌<br>{e}", 500
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
