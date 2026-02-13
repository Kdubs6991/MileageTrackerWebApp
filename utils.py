# Imports from the standard Python library
# datetime: used to parse string dates (e.g., "2026-01-12") into objects we can manipulate.
# timedelta: used for date math, like subtracting days to find the Monday of a week.
from datetime import datetime, timedelta
# This file will handle all the backend data calculations

# -- Calculations notes --
# - Week #'s
# - Weeks go from Monday through Sunday
# - Amount made will be a manual entry from the user
# - Amount set aside will take the amount made for that week, and multiply
#   it by 0.25, and that answer will be the 'set aside amount'
# - Miles Driven will be calculated by a file upload or by scanning my Gmail
#   account to read the CSV file from Stride
# - Est. deductions will take the miles driven, multiply it by the constant
#   deduction rate, and that answer will go there
# - The additional notes is just extra in case I need to add a note, it can
#   be left blank.

# -- Total Notes --
# - The total made takes everything in the Amount made column and adds it
# - The total set aside takes everything from the set aside column and adds it
# - The total miles driven takes everything from the miles column and adds it
# - The total deductions takes everything from the deductions column and adds it

# -----------------------------------------------------------------------

def calculate_stats(entries):
    """
    INPUT:  'entries' is a list of dictionaries passed from app.py.
            Each dictionary represents one row from the database (Date, Miles, Earnings, Notes).
    OUTPUT: Returns a dictionary containing the Grand Totals for the top of the home page.
            Also modifies the 'entries' list in-place to add formatted fields for the table.
    """

    # -- Constants --
    # We use uppercase variables to show that these are fixed values that should not change.
    TAX_SET_ASIDE_RATE = 0.25 # We save 25% of earnings for taxes
    STANDARD_MILEAGE_RATE = 0.70 # The 2025 IRS deduction rate is 70 cents per mile.

    # -- Initialize Totals --
    # These variables are initialized at 0, and as we loop through every entry in the
    # database, we add that entry's numbers into these variables.
    total_made = 0.0
    total_set_aside = 0.0
    total_miles = 0.0
    total_deductions = 0.0

    # Loop through every single entry (row) from the database.
    for entry in entries:
        # 1. Calculate Week # (Monday through Sunday)
        # We need to turn the text date "YYY-MM-DD" into a Python Date Object so
        # we can do math on it (like finding the week number).
        dt = None
        if isinstance(entry['date'], str):
            try:
                # strptime parses a string into a datetime object.
                dt = datetime.strptime(entry['date'], '%Y-%m-%d')
            except ValueError:
                # If the date format is wrong (e.g. empty or typo), skip date logic
                # so the app doesn't crash.
                pass
        else:
            # If it's already a date object (rare, but possible depending on DB driver)
            dt = entry['date']

        if dt:
            # Week Number Logic: Use ISO Calendar to determine week number.
            # This ensures Week 1 is the first week of the year, and resets every year,
            # preventing negative numbers for past years, and large numbers for future years.
            entry['week_num'] = dt.isocalendar()[1]

            # Calculate the start (Monday) and end (Sunday) of the week
            # dt.weekday() returns 0 for Monday, 1 for Tuesday... 6 for Sunday.
            # Subtracting that number of days snaps us back to Monday.
            start_of_week = dt - timedelta(days=dt.weekday())
            # Adding 6 days to Monday gives us Sunday.
            end_of_week = start_of_week + timedelta(days=6)

            # Format the dates nicely for the table (e.g., "Jan 12, 2026 - Jan 18, 2026")
            entry['date'] = f"{start_of_week.strftime('%b %d, %Y')} - {end_of_week.strftime('%b %d, %Y')}"
        else:
            # Fallback if date was invalid.
            entry['week_num'] = "-"

        # 2. Get values from the database
        # Data comes from the DB as strings or generic numbers. We force them into
        # Python 'floats' (decimal numbers) so we can do math on them.
        try:
            earnings = float(entry['earnings'])
        except (ValueError, TypeError):
            earnings = 0.0

        try:
            miles = float(entry['miles'])
        except (ValueError, TypeError):
            miles = 0.0

        # Format the original values to force 2 decimal places
        # This updates the dictionary so the Table shows "150.00" instead of "150.0".
        entry['earnings'] = "{:.2f}".format(earnings)
        entry['miles'] = "{:.2f}".format(miles)

        # 3. Calculate set aside (amount made * 0.25)
        calculated_set_aside = earnings * TAX_SET_ASIDE_RATE

        # Store the formatted string back into the entry for the Table in home.html
        # "{:.2f}" formats the float to a string with exactly 2 decimal places.
        entry['set_aside'] = "{:.2f}".format(calculated_set_aside)

        # 4. Calculate estimated deductions (miles driven * constant rate)
        calculated_deduction = miles * STANDARD_MILEAGE_RATE
        # Store the formatted string back into the entry for the Table in home.html
        entry['deduction'] = "{:.2f}".format(calculated_deduction)

        # 5. Update totals
        # Add this specific entry's numbers to the running grand totals.
        # These totals will be sent to the top 4 boxes on the home page.
        total_made += earnings
        total_set_aside += calculated_set_aside
        total_miles += miles
        total_deductions += calculated_deduction

    # OUTPUT: Return a dictionary of the Grand Total.
    # These keys (e.g., "total_made") become variables available in home.html.
    # We format them here so the HTML template stays clean and simple.
    return {
        "total_made": "{:.2f}".format(total_made),
        "total_set_aside": "{:.2f}".format(total_set_aside),
        "total_miles": "{:.2f}".format(total_miles),
        "total_deductions": "{:.2f}".format(total_deductions)
    }