import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "dev-salt-change-me")

    # MySQL - hardcode for now so it DEFINITELY matches MySQL
    DB_HOST = "127.0.0.1"          # use TCP, not socket
    DB_PORT = 3306
    DB_USER = "flaskuser"
    DB_PASSWORD = "password123"
    DB_NAME = "urban_myths_db"

    # Email (Gmail)

    # ... your Flask + DB config above ...

    # Email (Gmail)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True

    # For local dev / school project, you can hardcode these:
    MAIL_USERNAME = "gustavito1107@gmail.com"
    MAIL_PASSWORD = "mxcnjkyxjuhogowd"  # <-- remove all spaces
 # no spaces
