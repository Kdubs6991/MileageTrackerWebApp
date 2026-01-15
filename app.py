# Imports the Flask class (the web framework)
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta, date
import csv
import io
from utils import calculate_stats

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

# 'redirect()' sends the browser to another page after saving
# 'url_for("home")' generates the correct URL for your home() route

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

#
# App route for the home/main page
#
@app.route("/")
#This is the function that handles that page. When the render_template()
# runs, it looks for a folder named "templates/" and finds home.html
# inside of it. Then it reads that file and sends its contents as the HTTP
# response.
def home():
    conn = get_db_connection()
    # Gets all the rows from the database
    rows = conn.execute("SELECT * FROM entries ORDER BY date DESC").fetchall()
    conn.close()

    # Convert rows to dictionaries so utils.py can modify the data (add week_num, etc.)
    entries = [dict(row) for row in rows]

    # Calculate totals and add calculated fields to entries
    totals = calculate_stats(entries) #function in utils.py file

    return render_template("home.html", entries=entries, **totals)

#
# App Route for the Add page
#
@app.route("/add", methods=("GET", "POST"))
def add():
    # the 'request.method' tells how the page was accessed
    # the 'request.form' Dictionary-like object form inputs
    # the keys come from the name in "..." in HTML
    # the print statement outputs to the console
    if request.method == "POST":
        date_str = request.form["date"]

        # Logic: snap the selected date to the Monday of that week
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        monday_of_week = dt - timedelta(days=dt.weekday())
        sunday_of_week = monday_of_week + timedelta(days=6)
        date_to_save = monday_of_week.strftime('%Y-%m-%d')

        # ------------------------------------------------
        # Miles Logic: Check file first, then manual input
        # ------------------------------------------------
        miles = 0.0
        file_processed = False

        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # A file was uploaded. Read it and calculate the miles from it
                file_processed = True
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)

                for row in csv_input:
                    # Stride CSV headers: "Date", "Distance"
                    row_date_str = row.get("Date")
                    dist_str = row.get("Distance")

                    if not row_date_str or not dist_str:
                        continue
                    row_dt = None
                    for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
                        try:
                            row_dt = datetime.strptime(row_date_str, fmt)
                            break
                        except ValueError:
                            continue

                    if not row_dt: continue

                    # Check if this trip falls within the selected week
                    if monday_of_week.date() <= row_dt.date() <= sunday_of_week.date():
                        try:
                            trip_miles = float(dist_str.replace(" mi", "").strip())
                            miles += trip_miles
                        except ValueError:
                            continue

        if not file_processed:
            manual_miles = request.form.get("miles")
            if manual_miles:
                miles = float(manual_miles)

        earnings = request.form["earnings"]
        notes = request.form["notes"]

        # conn is the connection to the database. Inside the conn.execute:
        # the string is the SQL commands, then the values that are '?' are
        # placeholders, the tuple (date, miles, earnings, notes) fills those
        # placeholders. Commit makes the changes permanent and redirect
        # prevents re-submitting the form if you refresh
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO entries (date, miles, earnings, notes) VALUES (?, ?, ?, ?)",
            (date_to_save, miles, earnings, notes),
        )
        conn.commit()
        conn.close()

        # This must be inside the post block
        return redirect(url_for("home"))

        # Old print statement for initial debugging
        #print(f'{date} {miles} {earnings} "{notes}"')
    # This runs on GET
    return render_template("add.html", today=date.today())

#
# App route for the Edit page
#
@app.route("/edit/<int:id>", methods=("GET", "POST"))
def edit(id):
    conn = get_db_connection()
    # Fetch the specific entry by ID so we can pre-fill the form
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()

    # if the request is a POST request, it will update the database with the
    # new values from the form, commit the changes to the database, and then
    # redirect to the home page
    if request.method == "POST":
        date_str = request.form["date"]

        # Logic: Snap the selected date to the Monday of that week
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        monday_of_week = dt - timedelta(days=dt.weekday())
        date_to_save = monday_of_week.strftime('%Y-%m-%d')

        miles = request.form["miles"]
        earnings = request.form["earnings"]
        notes = request.form["notes"]

        conn.execute(
            "UPDATE entries SET date = ?, miles = ?, earnings = ?, notes = ? WHERE id = ?",
            (date_to_save, miles, earnings, notes, id),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    # if the request is a GET request, it will render the edit.html template
    conn.close()

    # Convert row to dictionary and format numbers to 2 decimal places
    if entry:
        entry = dict(entry)
        entry['miles'] = "{:.2f}".format(entry['miles'])
        entry['earnings'] = "{:.2f}".format(entry['earnings'])

    return render_template("edit.html", entry=entry)

#
# App route for delete (not a page)
# This App route only has a POST method because there is no delete page
#
@app.route("/delete/<int:id>", methods=("POST",))
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM entries WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


#
# App route for the About page
#
@app.route("/about")
def about():
    return render_template("about.html")


#This means only run the server if you ran this file directly
if __name__ == "__main__":
    init_db()
    #debug=true auto-restarts when you save changes
    app.run(debug=True, host="127.0.0.1", port=5050)