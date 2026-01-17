# Imports the Flask class (the web framework) and helper functions.
# render_template: renders HTML files.
# request: handles incoming data (forms, files).
# redirect/url_for: moves users to different pages.
# flash: stores temporary messages (like success/error notifications) to show on the next page load.
from flask import Flask, render_template, request, redirect, url_for, flash

# Imports for handling dates and time calculations (used for week logic).
from datetime import datetime, timedelta, date

# Imports for handling file uploads (on add page) and CSV parsing.
import csv
import io

# Import the custom calculation logic from utils.py.
from utils import calculate_stats

# Import for database interation.
import sqlite3
# Import for handling file system paths (finding the database file).
from pathlib import Path

#-----------------------------------------------------------------------

# Creates the Flask application instance.
# Passing __name__ tells Flask where to look for templates and static files.
app = Flask(__name__)
# Secret key is required for session data (like Flash messages).
# In a real production app, this should be a long random string hidden in an enviroment variable.
app.secret_key = "dev_key_for_mileage_tracker"

# Defines the full path to the database file.
# Path(__file__) gets the location of this script (app.py).
# .with_name("milage.db") makes sure we look for the database in the same folder as app.py.
DB_PATH = Path(__file__).with_name("mileage.db")

# Helper function to connect to the database.
def get_db_connection():
    # Opens a connection to the SQLite database file defined in DB_PATH.
    conn = sqlite3.connect(DB_PATH)
    # Sets the row_factory to sqlite3.Row so we can access columns by name.
    # (e.g., row['date']) instead of (row[0]).
    conn.row_factory = sqlite3.Row
    return conn


# Initializes the database by creating the 'entries' table if it doesn't exist.
# This ensures the app has a place to store data when it first runs.
#
# Table Schema:
#   - id: Unique identifier for each row (Primary Key).
#   - date: The Monday date of the week (stored as TEXT 'YYYY-MM-DD').
#   - miles: Total miles driven (stored as REAL/Float).
#   - earnings: Total money made (stored as REAL/Float).
#   - notes: Optional additional notes (stored as TEXT).
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
    # Commits the changes to the database (saves whatever was done to it).
    conn.commit()
    # Closes the connection to the database. Good for saving computer memory and
    #  good to prevent errors such as 'Database is locked'.
    conn.close()

#-----------------------------------------------------------------------

#
# App route for the home/main page
#
# @app.route decorator: Tells Flask what URL should trigger the function below it.
# The string inside ("/") is the 'rule'. "/" represents the root or homepage.
@app.route("/")
def home():
    # 1. Connect to the database
    conn = get_db_connection()
    # 2. Fetch all entries
    # "SELECT * FROM entries" gets every column.
    # "ORDER BY date ASC" list the entries starting from week #1 and going forward.
    rows = conn.execute("SELECT * FROM entries ORDER BY date ASC").fetchall()

    # 3. Close the connection immediately after fetching data.
    conn.close()

    # Convert rows to dictionaries so utils.py can modify the data (add week_num, etc.)
    # SQLite rows are read-only. We convert them to dicts so we can add new keys.
    # (like 'week_num', 'set_aside', etc.) inside the calculate_stats function.
    entries = [dict(row) for row in rows]

    # This function (from utils.py) loops through entries to calculate totals
    # and formats the dates/money for display.
    totals = calculate_stats(entries)

    # 4. Render the HTML template.
    # We pass 'entries' (the list of rows) and '**totals' (unpacked dictionary of totals)
    # so they can be used inside {{ }} tags in home.html.
    return render_template("home.html", entries=entries, **totals)

#---------------------------------------------------------

#
# App Route for the Add page
#
# @app.route("/add", ...):
#   - The Rule "/add": When the user visits '.../add', this function runs
#   - methods=("GET", "POST"): Defines allowed HTTP methods.
#       * GET: Used when the user just wants to see the page.
#       * POST: Used when the user submits the form to save data.
@app.route("/add", methods=("GET", "POST"))
def add():
    # Check if the form was submitted (POST request)
    if request.method == "POST":
        # 1. Get the date selected by the user from the form
        date_str = request.form["date"]

        # 2. Snap the date to the Monday of that week.
        # This ensures that regardless of which day the user picks (e.g., Wednesday),
        # the entry is saved under the Monday of that week for consistent weekly tracking.
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        monday_of_week = dt - timedelta(days=dt.weekday())
        sunday_of_week = monday_of_week + timedelta(days=6)
        date_to_save = monday_of_week.strftime('%Y-%m-%d')

        # ------------------------------------------------
        # Miles Logic: Check file first, then manual input
        # ------------------------------------------------
        miles = 0.0
        file_processed = False

        # 3. Check if a file was uploaded in the form.
        if 'file' in request.files:
            file = request.files['file']
            # Ensure the user actually selected a file (filename is not empty)
            if file.filename != '':
                file_processed = True

                # Read the CSV file from memory (without saving to disk).
                # .decode("UTF8") converts raw bytes to string.
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)

                # Loop through every row in the CSV file.
                for row in csv_input:
                    # Get values using Stride's specific column headers.
                    row_date_str = row.get("Date")
                    dist_str = row.get("Distance")

                    # Skip empty rows
                    if not row_date_str or not dist_str:
                        continue

                    # Parse the date from the CSV row.
                    # Stride usually uses MM/DD/YYYY, but we check ISO format too just in case.
                    row_dt = None
                    for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
                        try:
                            row_dt = datetime.strptime(row_date_str, fmt)
                            break
                        except ValueError:
                            continue

                    if not row_dt: continue

                    # Filter: Only add miles if the trip happened during the selected week.
                    if monday_of_week.date() <= row_dt.date() <= sunday_of_week.date():
                        try:
                            # Clean the distance string (remove " mi") and convert to float.
                            trip_miles = float(dist_str.replace(" mi", "").strip())
                            miles += trip_miles
                        except ValueError:
                            continue
        # If statement detects if there were any miles add for the week selected, and flashes a message accordingly
        if miles > 0:
            flash(f"Success! Imported {miles: .2f} miles from Stride CSV.", "success")
        else:
            flash("CSV processed, but no trips were found for this specific week.", "warning")

        # 4. Fallback: If no file was uploaded, use the manual input box.
        if not file_processed:
            manual_miles = request.form.get("miles")
            if manual_miles:
                miles = float(manual_miles)
                flash("Entry added successfully!", "success")

        # 5. Get the remaining form data.
        # Convert earnings to float, defaulting to 0.0 if empty.
        earnings_str = request.form.get("earnings", "")
        earnings = float(earnings_str) if earnings_str else 0.0

        notes = request.form["notes"]

        # Save to the database.
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO entries (date, miles, earnings, notes) VALUES (?, ?, ?, ?)",
            (date_to_save, miles, earnings, notes),
        )
        conn.commit()
        conn.close()

        # Redirect back to the home page to see the new entry.
        return redirect(url_for("home"))

    # This runs on GET (when the user first visits the page).
    # We pass today's date so the date picker defaults to the current week.
    return render_template("add.html", today=date.today())

#---------------------------------------------------------

#
# App route for the Edit page
#
# The Rule "/edit/<int:id>":
#   - <int:id> is a dynamic variable. If you go to '/edit/5', Flask passes 5
#     as the 'id' argument to the edit(id) function below.
@app.route("/edit/<int:id>", methods=("GET", "POST"))
def edit(id):
    # 1. Connect to the database.
    conn = get_db_connection()

    # 2. Fetch the existing entry.
    # We need the current data to pre-fill the form so the user sees what they are editing.
    # 'WHERE id =?' ensures we only get the one specific row matching the URL ID.
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (id,)).fetchone()

    # 3. Handle the form submission (POST).
    # If the user made changes and clicked "Save Changes".
    if request.method == "POST":
        # Get the date from the form
        date_str = request.form["date"]

        # Logic: Snap the selected date to the Monday of that week.
        # Just like in 'add', we ensure consistency by storing the Monday date.
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        monday_of_week = dt - timedelta(days=dt.weekday())
        date_to_save = monday_of_week.strftime('%Y-%m-%d')

        # Get other fields from the form.
        # Convert to floats to ensure we don't save empty strings to the database
        miles_Str = request.form.get("miles", "")
        miles = float(miles_Str) if miles_Str else 0.0

        earnings_str = request.form.get("earnings", "")
        earnings = float(earnings_str) if earnings_str else 0.0

        notes = request.form["notes"]

        # 4. Update the Database
        # "UPDATE entries SET ..." modifies the existing row.
        # We use the 'id' to make sure we don't overwrite the wrong entry.
        conn.execute(
            "UPDATE entries SET date = ?, miles = ?, earnings = ?, notes = ? WHERE id = ?",
            (date_to_save, miles, earnings, notes, id),
        )

        # Save the changes and close connection.
        conn.commit()
        conn.close()

        # Redirect back to home page.
        flash("Entry updated successfully!", "success")
        return redirect(url_for("home"))

    # 5. Handle Page Load (GET).
    # If we are just viewing the page, close the connection (we already fetched 'entry' at the top).
    conn.close()

    # 6. Format Data for Display.
    # Convert the database row to a dictionary so we can modify values.
    # We format miles and earnings to 2 decimal places (e.g., 10.5 -> 10.50)
    # so they look correct inside the input boxes.
    if entry:
        entry = dict(entry)
        # Safely format numbers, handling cases where database might have bad data
        try:
            entry['miles'] = "{:.2f}".format(float(entry['miles']))
        except (ValueError, TypeError):
            entry['miles'] = "0.00"

        try:
            entry['earnings'] = "{:.2f}".format(float(entry['earnings']))
        except (ValueError, TypeError):
            entry['earnings'] = "0.00"

    # Render the edit template with the pre-filled data.
    return render_template("edit.html", entry=entry)

#---------------------------------------------------------

#
# App route for delete (not a page)
#
# The Rule "/delete/<int:id>":
#   - This route is triggered when a form submits to '/delete/X' (where X is the ID).
#   - methods=("POST",): We ONLY allow POST requests here.
#     This prevents accidental deletions via simple link clicks (GET requests).
@app.route("/delete/<int:id>", methods=("POST",))
def delete(id):
    # 1. Connect to the database.
    conn = get_db_connection()

    # 2. Execute the Delete Command.
    # 'DELETE FROM entries WHERE id = ?' removes the row with the matching ID.
    # The (id,) tuple provides the value for the '?' placeholder.
    conn.execute('DELETE FROM entries WHERE id = ?', (id,))

    # 3. Save changes and close the connection
    conn.commit()
    conn.close()

    #4. Redirect back to the home page.
    flash("Entry deleted.", "error")
    return redirect(url_for("home"))

#---------------------------------------------------------

#
# App route for the About page
#
@app.route("/about")
def about():
    return render_template("about.html")


# Checks if this script is being run directly (e.g., 'python app.py').
# If this file were imported into another script, this block would NOT run.
if __name__ == "__main__":
    # Initialize the database (create tables) before starting the server.
    init_db()

    # Start the Flask development server.
    # debug=True: Automatically restarts the server when you save code changes
    #             and shows detailed error messages in the browser.
    # host="127.0.0.1": Runs the app on your local machine (localhost).
    # port=5050: The address will be http://127.0.0.1:5050
    app.run(debug=True, host="127.0.0.1", port=5050)