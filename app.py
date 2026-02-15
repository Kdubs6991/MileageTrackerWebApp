# Imports the Flask class (the web framework) and helper functions.
# render_template: renders HTML files.
# request: handles incoming data (forms, files).
# redirect/url_for: moves users to different pages.
# flash: stores temporary messages (like success/error notifications) to show on the next page load.
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_wtf.csrf import CSRFProtect

# os: Used to access operating system functionality, specifically environment variables.
import os
# dotenv: Loads environment variables from a .env file into os.environ.
from dotenv import load_dotenv

# Load environment variables from .env (local dev only; on a host you'll set real env vars)
load_dotenv()

# Flask-Login: Manages user sessions and authentication.
# LoginManager: The main class that handles the login process.
# login_user/logout_user: Functions to log a user in or out.
# login_required: Decorator to protect routes (ensure user is logged in).
# current_user: Proxy for the currently logged-in user.
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# Werkzeug Security: Handles password hashing.
# generate_password_hash: Encrypts a password before saving to the database.
# check_password_hash: Checks a login password against the stored hash.
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for handling dates and time calculations (used for week logic).
from datetime import datetime, timedelta, date

# Imports for handling file uploads (on add page) and CSV parsing.
import csv
import io

# Import the custom calculation logic from utils.py.
from utils import calculate_stats

# Import the User model from our new models.py file
from models import User

# Import for database interation.
import sqlite3
# Import for handling file system paths (finding the database file).
from pathlib import Path

#-----------------------------------------------------------------------

# Load environment variables form the .env file (if it exists)

# Creates the Flask application instance.
# Passing __name__ tells Flask where to look for templates and static files.
app = Flask(__name__)
# --- Configuration (dev vs prod) ---
# In production, you MUST set SECRET_KEY in the environment.
secret = os.environ.get("SECRET_KEY")
if not secret:
    # Safe default for local development only.
    # IMPORTANT: set SECRET_KEY in your hosting provider before deploying.
    secret = "dev_key_for_mileage_tracker"
app.secret_key = secret

# Cookie / session hardening
# NOTE: SESSION_COOKIE_SECURE should be True when served over HTTPS (typical in production).
is_prod = os.environ.get("FLASK_ENV") == "production" or os.environ.get("ENV") == "production"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=is_prod,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=is_prod,
)

# Upload safety: limit request size (prevents large file uploads / DOS)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB default

# CSRF protection for all POST/PUT/PATCH/DELETE requests
# Templates must include a hidden input named 'csrf_token'.
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
csrf = CSRFProtect(app)

# In production, require a real SECRET_KEY
if is_prod and secret == "dev_key_for_mileage_tracker":
    raise RuntimeError("SECRET_KEY must be set in production")
# -------------------------------

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' #Redirects users here if they try to access a protected page

# -------------------------------

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

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['password_hash'], user['theme'])
    return None


# Initializes the database by creating the 'entries' table if it doesn't exist.
# This ensures the app has a place to store data when it first runs.
#
# Table Schema:
#   Users Table:
#   - id: Unique User ID
#   - username: The login name
#   - password_hash: The encrypted password
#
#   Entries Table:
#   - id: Unique identifier for each row (Primary Key).
#   - user_id: Links the entry to a specific user.
#   - date: The Monday date of the week (stored as TEXT 'YYYY-MM-DD').
#   - miles: Total miles driven (stored as REAL/Float).
#   - earnings: Total money made (stored as REAL/Float).
#   - notes: Optional additional notes (stored as TEXT).
def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            theme TEXT DEFAULT 'light'
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        miles REAL NOT NULL,
        earnings REAL NOT NULL,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
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
@login_required
def home():
    # -- 1. Pagination & Filtering Setup --
    PER_PAGE = 15 # Entries per page
    page = request.args.get('page', 1, type=int)
    selected_year = request.args.get('year', type=int)

    # Connect to the database
    conn = get_db_connection()

    # -- 2. Get available years for the filter dropdown --
    years_result = conn.execute(
        "SELECT DISTINCT strftime('%Y', date) as year FROM entries WHERE user_id = ? ORDER BY year DESC",
        (current_user.id,)
    ).fetchall()
    available_years = [row['year'] for row in years_result]

    # -- 3. Determine which year to display --
    if not selected_year and available_years:
        # Defaults to the most recent year if none is chosen.
        selected_year = int(available_years[0])
    elif selected_year and str(selected_year) not in available_years:
        # Handle case where user types a year with no entries, default to most recent.
        flash(f"No entries found for the year {selected_year}.", "warning")
        selected_year = int(available_years[0]) if available_years else None

    # -- 4. Get paginated entries for the selected year --
    if selected_year:
        # Get total count for pagination
        total_entries_count = conn.execute(
            "SELECT COUNT(id) FROM entries WHERE user_id = ? AND strftime('%Y', date) = ?",
            (current_user.id, str(selected_year))
        ).fetchone()[0]

        total_pages = (total_entries_count + PER_PAGE - 1) // PER_PAGE

        # Get the actual entries for the current page
        offset = (page - 1) * PER_PAGE
        rows = conn.execute(
            "SELECT * FROM entries WHERE user_id = ? AND strftime('%Y', date) = ? ORDER BY date ASC LIMIT ? OFFSET ?",
            (current_user.id, str(selected_year), PER_PAGE, offset)
        ).fetchall()
    else:
        # No entries exist for this user at all
        rows = []
        total_pages = 0


    # Close the connection immediately after fetching data.
    conn.close()

    # -- 5. Process rows for display --
    # Convert rows to dictionaries so utils.py can modify the data (add week_num, etc.)
    # SQLite rows are read-only. We convert them to dicts so we can add new keys.
    # (like 'week_num', 'set_aside', etc.) inside the calculate_stats function.
    entries = [dict(row) for row in rows]

    # This function (from utils.py) loops through entries to calculate totals
    # and formats the dates/money for display.
    totals = calculate_stats(entries)

    # -- Pagination Logic for UI --
    page_iter = []
    if total_pages > 1:
        if total_pages <= 7:
            page_iter = list(range(1, total_pages + 1))
        else:
            page_iter.append(1)
            # Window of +/- 1 around current page
            window_start = max(2, page - 1)
            window_end = min(total_pages - 1, page + 1)

            if window_start > 2:
                page_iter.append(None) # Represents '...'

            for p in range(window_start, window_end + 1):
                page_iter.append(p)

            if window_end < total_pages - 1:
                page_iter.append(None) # Represents '...'

            page_iter.append(total_pages)

    # -- 6. Render the HTML template. --
    # We pass 'entries' (the list of rows) and '**totals' (unpacked dictionary of totals)
    # so they can be used inside {{ }} tags in home.html.
    return render_template("home.html", entries=entries, **totals, available_years=available_years,
                           selected_year=selected_year, current_page=page, total_pages=total_pages, page_iter=page_iter)

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
@login_required
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
                # Basic validation: only allow CSV uploads
                filename_lower = file.filename.lower()
                if not filename_lower.endswith('.csv'):
                    flash("Error: Please upload a .csv file.", "error")
                    return redirect(url_for("add"))

                # Some browsers send useful mimetypes, some don't; accept common CSV types
                if file.mimetype and ('csv' not in file.mimetype and file.mimetype not in ('application/vnd.ms-excel',)):
                    flash("Error: Uploaded file does not look like a CSV.", "error")
                    return redirect(url_for("add"))

                file_processed = True

                # Safety: Reset file pointer to the beginning
                file.stream.seek(0)
                # Read the CSV file from memory (without saving to disk).
                # .decode("utf-8-sig") converts raw bytes to string and handles BOM (Byte Order Mark).
                try:
                    raw = file.stream.read()
                    text = raw.decode("utf-8-sig")
                except Exception:
                    flash("Error: Could not read the uploaded file. Please upload a valid UTF-8 CSV.", "error")
                    return redirect(url_for("add"))

                stream = io.StringIO(text, newline=None)

                csv_input = csv.DictReader(stream)

                # Store parsed rows to avoid re-reading/re-parsing
                parsed_rows = []
                max_csv_date = None

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

                    if row_dt:
                        parsed_rows.append({'dt': row_dt, 'dist': dist_str})
                        # Track the latest date found in the file
                        if max_csv_date is None or row_dt > max_csv_date:
                            max_csv_date = row_dt

                # Logic: Only process if the selected week matches the week of the most recent CSV entry
                if max_csv_date:
                    # Calculate the Monday of the most recent entry in the CSV
                    max_csv_monday = max_csv_date - timedelta(days=max_csv_date.weekday())

                    # Check if the form's selected week matches the CSV's latest week
                    if monday_of_week.date() != max_csv_monday.date():
                        flash(
                            f"Error: The CSV file's most recent week ({max_csv_monday.strftime('%b %d')}) does not match the selected week ({monday_of_week.strftime('%b %d')}).",
                            "error")
                        return redirect(url_for("add"))

                    for row in parsed_rows:
                        # Filter: Only add miles if the trip happened during the selected week.
                        if monday_of_week.date() <= row['dt'].date() <= sunday_of_week.date():
                            try:
                                # Clean the distance string (remove " mi") and convert to float.
                                trip_miles = float(row['dist'].replace(' mi', '').strip())
                                miles += trip_miles
                            except ValueError:
                                continue
                else:
                    flash("Error: Could not find any valid dates in the uploaded CSV. Please check the file format.",
                          "error")
                    return redirect(url_for("add"))

                # If statement detects if there were any miles add for the week selected, and flashes a message accordingly
                if miles > 0:
                    flash(f"Success! Imported {miles: .2f} miles from Stride CSV.", "success")
                else:
                    flash("CSV processed, but no trips were found for this specific week. Entry not saved.", "warning")
                    return redirect(url_for("add"))

        # 4. Fallback: If no file was uploaded, use the manual input box.
        if not file_processed:
            manual_miles = request.form.get("miles")
            if manual_miles:
                try:
                    miles = float(manual_miles)
                    if miles < 0:
                        flash("Miles cannot be negative.", "error")
                        return redirect(url_for("add"))
                except ValueError:
                    miles = 0.0
                flash("Entry added successfully!", "success")

        # 5. Get the remaining form data.
        # Convert earnings to float, defaulting to 0.0 if empty.
        earnings_str = request.form.get("earnings", "")
        try:
            earnings = float(earnings_str) if earnings_str else 0.0
            if earnings < 0:
                flash("Earnings cannot be negative.", "error")
                return redirect(url_for("add"))
        except ValueError:
            earnings = 0.0

        notes = request.form["notes"]

        # Save to the database.
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO entries (date, miles, earnings, notes, user_id) VALUES (?, ?, ?, ?, ?)",
            (date_to_save, miles, earnings, notes, current_user.id),
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
@login_required
def edit(id):
    # 1. Connect to the database.
    conn = get_db_connection()

    # 2. Fetch the existing entry.
    # We need the current data to pre-fill the form so the user sees what they are editing.
    # We also check 'AND user_id = ?' to ensure users can't edit someone else's data.
    entry = conn.execute('SELECT * FROM entries WHERE id = ? AND user_id = ?', (id, current_user.id)).fetchone()

    if entry is None:
        flash("Entry not found or access denied.", "error")
        return redirect(url_for("home"))

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
        try:
            miles = float(miles_Str) if miles_Str else 0.0
            if miles < 0:
                flash("Miles cannot be negative.", "error")
                return redirect(url_for("edit", id=id))
        except ValueError:
            miles = 0.0

        earnings_str = request.form.get("earnings", "")
        try:
            earnings = float(earnings_str) if earnings_str else 0.0
            if earnings < 0:
                flash("Earnings cannot be negative.", "error")
                return redirect(url_for("edit", id=id))
        except ValueError:
            earnings = 0.0

        notes = request.form["notes"]

        # 4. Update the Database
        # "UPDATE entries SET ..." modifies the existing row.
        # We use the 'id' to make sure we don't overwrite the wrong entry.
        conn.execute(
            "UPDATE entries SET date = ?, miles = ?, earnings = ?, notes = ? WHERE id = ? AND user_id = ?",
            (date_to_save, miles, earnings, notes, id, current_user.id),
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
@login_required
def delete(id):
    # 1. Connect to the database.
    conn = get_db_connection()

    # 2. Execute the Delete Command.
    # 'DELETE FROM entries WHERE id = ?' removes the row with the matching ID and User ID.
    # The (id,) tuple provides the value for the '?' placeholder.
    conn.execute('DELETE FROM entries WHERE id = ? AND user_id = ?', (id, current_user.id))

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

#-----------------------------------------------------------------------

#
# App route for the user's account information
#
@app.route("/account")
@login_required
def account():
    return render_template("auth/account.html")

#---------------------------------------------------------

#
# App route for Deleting the User Account
#
@app.route("/delete_account", methods=("POST",))
@login_required
def delete_account():
    conn = get_db_connection()
    # Delete all entries belonging to the user first
    conn.execute("DELETE FROM entries WHERE user_id = ?", (current_user.id,))
    # Then delete the user itself
    conn.execute("DELETE FROM users WHERE id = ?", (current_user.id,))
    conn.commit()
    conn.close()

    logout_user()
    flash('Your account and all data have been deleted', 'success')
    return redirect(url_for('login'))


#---------------------------------------------------------
#
# Authentication Routes
#
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If the user submitted the registration form
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        # Check if user already exists
        user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()

        if user:
            flash('Username or email already exists', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Security: Hash the password so we never store plain text passwords.
        # If the database is hacked, the attacker only sees hashes, not real passwords.
        hashed_pw = generate_password_hash(password)

        # Save the new user
        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)', (username, email, hashed_pw))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

#---------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If the user submitted the login form
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        conn = get_db_connection()
        # Fetch the user record by username OR email
        # We pass 'username' twice because we are checking it against two different columns.
        user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username)).fetchone()
        conn.close()

        # Verify user exists AND the password matches the stored hash.
        # check_password_hash handles the decryption/comparison securely.
        if user and check_password_hash(user['password_hash'], password):
            # Create a User object and log them in using Flask-Login
            user_obj = User(user['id'], user['username'], user['email'], user['password_hash'], user['theme'])
            login_user(user_obj, remember=remember)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')

#---------------------------------------------------------

@app.route('/logout')
@login_required
def logout():
    # Clears the user session and logs them out
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

#---------------------------------------------------------

#
# App route for Exporting Data (CSV)
#
@app.route("/export")
@login_required
def export():
    # 1. Fetch all data for the current user
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM entries WHERE user_id = ? ORDER BY date ASC", (current_user.id,)).fetchall()
    conn.close()

    # 2. Create CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    # Write Headers
    cw.writerow(["Date", "Miles", "Earnings", "Notes"])
    # Write Data
    for row in rows:
        cw.writerow([row["date"], row["miles"], row["earnings"], row["notes"]])

    # 3. Create a response object that acts as a file download
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=mileage_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

#-----------------------------------------------------------------------

#
# App route for Updating the theme (light/dark mode)
#
@app.route("/update_theme", methods=["POST"])
@login_required
def update_theme():
    data = request.get_json()
    theme = data.get('theme')
    if theme not in ("light", "dark"):
        return "Invalid theme", 400

    conn = get_db_connection()
    conn.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, current_user.id))
    conn.commit()
    conn.close()
    return '', 204


# Checks if this script is being run directly (e.g., 'python app.py').
# If this file were imported into another script, this block would NOT run.
if __name__ == "__main__":
    # Initialize the database (create tables) before starting the server.
    init_db()

    # Dev server only. In production, run with a WSGI server like gunicorn.
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug, host="127.0.0.1", port=5050)