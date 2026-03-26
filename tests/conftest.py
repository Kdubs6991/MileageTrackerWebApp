import sqlite3

from flask import Flask, g, current_app
app = Flask(__name__)

DB_PATH = "mileage.db"

def get_db_connection():
    # Use the test database path if one was provided in app config.
    # Otherwise fall back to the normal app database file.
    db_path = app.config.get("DATABASE", DB_PATH)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with app.open_resource('schema.sql') as f:
        conn.executescript(f.read().decode('utf8'))
    conn.commit()
    conn.close()