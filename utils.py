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


# INPUT: 'entries' is a list of dictionaries passed from the file app.py
# Each dictionary represents one row from the database (Date, Miles, Earnings, Notes)
def calculate_stats(entries):
    TAX_SET_ASIDE_RATE = 0.25 #25%
    STANDARD_MILEAGE_RATE = 0.70 #rate set by the IRS for 2025

    # -- Initialize Totals --
    # These variables start at 0, but then will be added to as
    # every entry is looped through
    total_made = 0.0
    total_set_aside = 0.0
    total_miles = 0.0
    total_deductions = 0.0

    # for loop runs through every entry in the database
    for entry in entries:
        # 1. Calculate Week # (Monday through Sunday)
        dt = None
        if isinstance(entry['date'], str):
            try:
                dt = datetime.strptime(entry['date'], '%Y-%m-%d')
            except ValueError:
                # If the date format is wrong, skip  date logic for this entry
                pass
        else:
            dt = entry['date']

        if dt:
            # Week Number Logic: Week 1 starts on December 29th, 2025
            # Calculate the week number relative to that start date
            TRACKING_START_DATE = datetime(2025, 12, 29)
            entry['week_num'] = ((dt - TRACKING_START_DATE).days // 7) + 1

            # Calculate the start (Monday) and end (Sunday) of the week
            start_of_week = dt - timedelta(days=dt.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            entry['date'] = f"{start_of_week.strftime('%b %d, %Y')} - {end_of_week.strftime('%b %d, %Y')}"
        else:
            entry['week_num'] = "-"
        # 2. Get values from the database
        # Converted to floats so we can perform math on the numbers
        earnings = float(entry['earnings'])
        miles = float(entry['miles'])

        # Format the original values to force 2 decimal places
        entry['earnings'] = "{:.2f}".format(earnings)
        entry['miles'] = "{:.2f}".format(miles)

        # 3. Calculate set aside (amount made * 0.25)
        calculated_set_aside = earnings * TAX_SET_ASIDE_RATE
        # Store the formatted string back into the entry for the Table in home.html
        # ------------------- this formats the float to 2 decimal places
        entry['set_aside'] = "{:.2f}".format(calculated_set_aside)

        # 4. Calculate estimated deductions (miles driven * constant rate)
        calculated_deduction = miles * STANDARD_MILEAGE_RATE
        # Store the formatted string back into the entry for the Table in home.html
        entry['deduction'] = "{:.2f}".format(calculated_deduction)

        # 5. Update totals
        # Add this specific entry's numbers to the running grand total
        total_made += earnings
        total_set_aside += calculated_set_aside
        total_miles += miles
        total_deductions += calculated_deduction

    # OUTPUT: Return a dictionary of the Grand Total.
    # These keys (e.g., "total_made") become variables available in home.html
    return {
        "total_made": "{:.2f}".format(total_made),
        "total_set_aside": "{:.2f}".format(total_set_aside),
        "total_miles": "{:.2f}".format(total_miles),
        "total_deductions": "{:.2f}".format(total_deductions)
    }