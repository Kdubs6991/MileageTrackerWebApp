#Imports the Flask class (the web framework)
from flask import Flask, render_template, request

import sqlite3
from pathlib import Path

#Creates the web app instance. __name__ helps Flask locate
# files like template
app = Flask(__name__)
DB_PATH = Path(__file__).with_name("mileage.db")

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 'CREATE TABLE IF NOT EXISTS' basically means 'make it if it's not already there'
# 'id ... AUTOINCREMENT' unique ID for each entry
# 'TEXT' strings and we store the date as "YYY-MM-DD"
# 'REAL' decimal numbers
def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        miles REAL NOT NULL,
        earnings REAL NOT NULL,
        notes TEXT
        );
    """)
    conn.commit()
    conn.close()

#-----------------------------------------------------------------------

#A route: When someone visits / (the home URL), run the function below
@app.route("/")
#This is the function that handles that page. When the render_template()
# runs, it looks for a folder named "templates/" and finds home.html
# inside of it. Then it reads that file and sends its contents as the HTTP
# response.
def home():
        return render_template("home.html")


@app.route("/add", methods=("GET", "POST"))
def add():
    # the 'request.method' tells how the page was accessed
    # the 'request.form' Dictionary-like object form inputs
    # the keys come from the name in "..." in HTML
    # the print statement outputs to the console
    if request.method == "POST":
        date = request.form["date"]
        miles = request.form["miles"]
        earnings = request.form["earnings"]
        notes = request.form["notes"]

        print(f'{date} {miles} {earnings} "{notes}"')
    return render_template("add.html")


#This means only run the server if you ran this file directly
if __name__ == "__main__":
    init_db()
    #debug=true auto-restarts when you save changes
    app.run(debug=True, host="127.0.0.1", port=5050)