import mysql.connector  # MySQL driver
from mysql.connector import Error
from flask import current_app, g  # current_app: config; g: per-request storage


def get_db():
    """
    Open a MySQL connection and store it in g.db for this request.
    If the connection fails, return None instead of crashing.
    """
    if "db" not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config["DB_HOST"],
                port=current_app.config["DB_PORT"],
                user=current_app.config["DB_USER"],
                password=current_app.config["DB_PASSWORD"],
                database=current_app.config["DB_NAME"],
            )
        except Error as e:
            print("MySQL connection error:", e)
            g.db = None
    return g.db


def close_db(e=None):
    """
    Closes the database connection at the end of a request.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """
    Called from __init__.py after Flask app is created.
    Registers close_db() so every request closes DB afterwards.
    """
    app.teardown_appcontext(close_db)


def query_test(sql, params=()):
    """
    Simple test/query helper. Returns True if a row is found, False otherwise.
    If DB connection fails, returns False.
    """
    conn = get_db()
    if conn is None:
        return False

    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return True if row else False
