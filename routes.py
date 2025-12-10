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

from app.db import get_db
from app.login import handle_login

from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

main = Blueprint("main", __name__)

# -----------------------------
# Helpers
# -----------------------------

def get_serializer():
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"],
        salt=current_app.config.get("SECURITY_PASSWORD_SALT", "email-confirm"),
    )

def send_verification_email(to_email: str, token: str):
    verify_url = url_for("main.verify_email", token=token, _external=True)

    html_body = render_template("verify_email.html", verify_url=verify_url)
    text_body = f"Please verify your account by visiting: {verify_url}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Urban Myths account"
    msg["From"] = current_app.config["MAIL_USERNAME"]
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]) as server:
            if current_app.config.get("MAIL_USE_TLS", False):
                server.starttls()
            server.login(
                current_app.config["MAIL_USERNAME"],
                current_app.config["MAIL_PASSWORD"],
            )
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    except Exception as e:
        print("Error sending email:", e)

# -----------------------------
# Routes
# -----------------------------

@main.route("/")
def index():
    return render_template("index.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if len(username) < 5:
            flash("Username must be at least 5 characters.", "danger")
            return render_template("register.html")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("register.html")

        conn = get_db()
        # ✅ handle DB connection failure gracefully
        if conn is None:
            flash("Database connection error. Could not connect to MySQL.", "danger")
            return render_template("register.html")

        cur = conn.cursor(dictionary=True)

        # check if email exists
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            flash("Email is already registered.", "danger")
            cur.close()
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        # insert user, is_verified = 0
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, is_verified)
            VALUES (%s, %s, %s, %s)
            """,
            (username, email, password_hash, 0),
        )
        conn.commit()
        cur.close()

        # 🔐 generate token
        s = get_serializer()
        token = s.dumps(email)

        # ✅ print verification link to terminal (for testing)
        verify_url = url_for("main.verify_email", token=token, _external=True)
        print("\n✅ VERIFICATION LINK (FOR TESTING):")
        print(verify_url)
        print()

        # ✉️ send verification email
        send_verification_email(email, token)

        flash("Account created! Check your email to verify your account.", "success")
        return redirect(url_for("main.login"))

    # GET
    return render_template("register.html")



@main.route("/verify/<token>")
def verify_email(token):
    s = get_serializer()
    try:
        email = s.loads(token, max_age=3600)  # 1 hour
    except SignatureExpired:
        flash("The verification link has expired.", "danger")
        return redirect(url_for("main.login"))
    except BadSignature:
        flash("Invalid verification link.", "danger")
        return redirect(url_for("main.login"))

    conn = get_db()
    # ✅ handle DB connection failure here too
    if conn is None:
        flash("Database connection error. Could not connect to MySQL.", "danger")
        return redirect(url_for("main.login"))

    cur = conn.cursor()
    cur.execute("UPDATE users SET is_verified = 1 WHERE email = %s", (email,))
    conn.commit()
    cur.close()

    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("main.login"))


@main.route("/login", methods=["GET", "POST"])
def login():
    # ALWAYS returns something on every path
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        success, message = handle_login(email, password)

        if success:
            flash(message, "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(message, "danger")
            return render_template("login.html")

    # GET request
    return render_template("login.html")


@main.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("main.login"))

    return render_template("dashboard.html", username=session.get("username"))


@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))
